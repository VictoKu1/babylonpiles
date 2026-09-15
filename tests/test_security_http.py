"""Outbound tests stub transport only; no external network is contacted."""
import asyncio
import io
import os
from pathlib import Path
import sys
import socket
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SECRET_KEY", "http-security-test-" * 4)
os.environ.setdefault("SERVICE_API_KEY", "service-security-test-" * 4)
os.environ.setdefault("STATE_DIR", "/tmp/babylonpiles-http-tests")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.api.v1.endpoints import piles
from app.core import public_http as http
from app.core.transfers import TransferTooLarge
from fastapi import HTTPException


class Content:
    def __init__(self, data): self.buffer = io.BytesIO(data)
    async def read(self, size): return self.buffer.read(size)


class FakeResponse:
    def __init__(self, data=b"<html><pre></pre></html>", status=200, headers=None):
        self.status, self.headers, self.charset = status, headers or {}, "utf-8"
        self.content = Content(data)
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return None
    def raise_for_status(self): pass


class FakeSession:
    responses = []
    calls = []
    def __init__(self, *args, **kwargs):
        self.connector = kwargs.get("connector")
        self.closed = False
    async def close(self):
        self.closed = True
        if self.connector: await self.connector.close()
    def get(self, url, **kwargs):
        self.calls.append((str(url), kwargs))
        return self.responses.pop(0) if self.responses else FakeResponse()


class HTTPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeSession.calls, FakeSession.responses = [], []

    async def test_source_browser_rejects_loopback_before_fetch(self):
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            with self.assertRaises((ValueError, HTTPException)):
                await piles.browse_source("http://127.0.0.1/private")
        self.assertEqual(FakeSession.calls, [])

    async def test_file_info_returns_structured_data_not_html(self):
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            result = await piles.file_info('<img src=x onerror=alert(1)>', "https://example.org/catalog")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["found"])

    async def test_metadata_is_selected_text_and_never_source_markup(self):
        FakeSession.responses = [FakeResponse(b'<book name="safe" title="&lt;script&gt;alert(1)&lt;/script&gt;" onclick="alert(1)"/>')]
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            result = await piles.file_info("safe", "https://example.org/catalog")
        self.assertTrue(result["found"])
        self.assertEqual(result["title"], "<script>alert(1)</script>")
        self.assertNotIn("onclick", result)

    async def test_rejects_private_literal_and_parser_variants(self):
        for url in ["http://localhost/", "http://127.0.0.1/", "http://10.2.3.4/", "http://169.254.169.254/", "http://[::1]/", "http://[::ffff:127.0.0.1]/", "http://[fc00::1]/", "http://[2002:7f00:1::]/", "http://user:password@example.org/", "file:///etc/passwd", "https://example.org:99999/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                http.validate_url(url)

    async def test_malformed_authority_is_rejected_before_transport(self):
        for url in ["http://exa mple.org/", "http://example.org|other.test/"]:
            with self.subTest(url=url), patch.object(http.aiohttp, "ClientSession", FakeSession):
                async with http.PublicSession() as session:
                    with self.assertRaises(ValueError):
                        async with session.get(url):
                            pass
        self.assertEqual(FakeSession.calls, [])

    async def test_canonical_public_urls_preserve_authority_path_and_query(self):
        cases = [
            ("https://example.org/a b?x=a%2Fb#part", "https://example.org/a%20b?x=a/b"),
            ("http://8.8.8.8:8080/a%2Fb?q=one%20two", "http://8.8.8.8:8080/a%2Fb?q=one%20two"),
            ("https://[2606:4700:4700::1111]:8443/catalog", "https://[2606:4700:4700::1111]:8443/catalog"),
            ("https://b\u00fccher.example/catalog", "https://xn--bcher-kva.example/catalog"),
            ("https://example.org?empty=", "https://example.org/?empty="),
        ]
        for value, expected in cases:
            with self.subTest(url=value), patch.object(http.aiohttp, "ClientSession", FakeSession):
                async with http.PublicSession() as session:
                    async with session.get(value) as response:
                        self.assertEqual(response.status, 200)
                self.assertEqual(FakeSession.calls[-1][0], expected)

    async def test_dns_answers_are_all_validated_and_returned_without_reresolution(self):
        resolver = http.PublicResolver()
        try:
            for answers in [[{"host": "127.0.0.1"}], [{"host": "8.8.8.8"}, {"host": "10.0.0.1"}], [{"host": "::ffff:192.168.1.1"}]]:
                resolver.delegate.resolve = AsyncMock(return_value=answers)
                with self.assertRaises(ValueError): await resolver.resolve("source.example", 443)
            answers = [{"host": "8.8.8.8"}, {"host": "2606:4700:4700::1111"}]
            resolver.delegate.resolve = AsyncMock(return_value=answers)
            self.assertIs(await resolver.resolve("source.example", 443), answers)
            resolver.delegate.resolve.assert_awaited_once()
        finally:
            await resolver.close()

    async def test_private_redirect_stops_before_second_request(self):
        FakeSession.responses = [FakeResponse(status=302, headers={"Location": "http://169.254.169.254/latest"})]
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            async with http.PublicSession() as session:
                with self.assertRaises(ValueError):
                    async with session.get("https://example.org/start"): pass
        self.assertEqual(len(FakeSession.calls), 1)
        self.assertFalse(FakeSession.calls[0][1]["allow_redirects"])

    async def test_public_relative_redirect_and_exact_size_control(self):
        FakeSession.responses = [FakeResponse(status=302, headers={"Location": "/file"}), FakeResponse(b"safe")]
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            async with http.PublicSession(max_bytes=4) as session:
                async with session.get("https://example.org/start") as response:
                    self.assertEqual(await response.text(), "safe")
        self.assertEqual(FakeSession.calls[1][0], "https://example.org/file")

    async def test_size_limits_check_actual_bytes_and_declared_length(self):
        for headers in [{}, {"Content-Length": "1"}, {"Content-Length": "99"}]:
            FakeSession.responses = [FakeResponse(b"oversized", headers=headers)]
            with patch.object(http.aiohttp, "ClientSession", FakeSession):
                async with http.PublicSession(max_bytes=4) as session:
                    with self.assertRaises(TransferTooLarge):
                        async with session.get("https://example.org/file") as response:
                            await response.text()

    async def test_redirect_hops_are_bounded(self):
        FakeSession.responses = [FakeResponse(status=302, headers={"Location": "/again"}) for _ in range(6)]
        with patch.object(http.aiohttp, "ClientSession", FakeSession):
            async with http.PublicSession() as session:
                with self.assertRaises(ValueError):
                    async with session.get("https://example.org/start"): pass
        self.assertEqual(len(FakeSession.calls), 6)

    async def test_tls_and_environment_proxy_verification_remain_enabled(self):
        async with http.PublicSession() as session:
            self.assertIs(session.session.connector._ssl, True)
            self.assertFalse(session.session.trust_env)


class ConnectorBoundaryTests(unittest.IsolatedAsyncioTestCase):
    """Use the actual aiohttp connector; all sockets stay on loopback."""

    async def asyncSetUp(self):
        self.requests = []
        self.redirect = None

        async def serve(reader, writer):
            try:
                self.requests.append(await reader.readuntil(b"\r\n\r\n"))
                if self.redirect:
                    reply = ("HTTP/1.1 302 Found\r\nLocation: " + self.redirect +
                             "\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").encode()
                else:
                    reply = b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\nConnection: close\r\n\r\nsafe"
                writer.write(reply)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        self.server = await asyncio.start_server(serve, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    def answers(self, *addresses):
        return [{"hostname": "source.example", "host": address, "port": self.port,
                 "family": socket.AF_INET, "proto": socket.IPPROTO_TCP, "flags": 0}
                for address in addresses]

    async def connect_public_to_fixture(self, *, addr_infos, **kwargs):
        # Replace only external socket creation, after real connector validation.
        self.assertTrue(addr_infos)
        self.assertEqual({entry[4][0] for entry in addr_infos}, {"8.8.8.8"})
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        try:
            await asyncio.get_running_loop().sock_connect(sock, ("127.0.0.1", self.port))
        except BaseException:
            sock.close()
            raise
        return sock

    async def test_private_and_mixed_dns_never_reach_the_http_server(self):
        for addresses in [("127.0.0.1",), ("8.8.8.8", "127.0.0.1")]:
            with self.subTest(addresses=addresses), patch.object(
                http.aiohttp.resolver.DefaultResolver, "resolve",
                AsyncMock(return_value=self.answers(*addresses)),
            ):
                async with http.PublicSession() as session:
                    with self.assertRaises((ValueError, http.aiohttp.ClientError)):
                        async with session.get(f"http://source.example:{self.port}/private"):
                            pass
            self.assertEqual(self.requests, [])

    async def test_numeric_loopback_aliases_never_reach_the_http_server(self):
        for host in ["127.0.0.1", "2130706433", "127.1", "0177.0.0.1", "0x7f000001"]:
            with self.subTest(host=host), patch.object(
                http.aiohttp.resolver.DefaultResolver, "resolve",
                AsyncMock(return_value=self.answers("127.0.0.1")),
            ):
                async with http.PublicSession() as session:
                    with self.assertRaises((ValueError, http.aiohttp.ClientError)):
                        async with session.get(f"http://{host}:{self.port}/private"):
                            pass
            self.assertEqual(self.requests, [])

    async def test_public_dns_uses_checked_addresses_and_retains_host_header(self):
        with patch.object(http.aiohttp.resolver.DefaultResolver, "resolve",
                          AsyncMock(return_value=self.answers("8.8.8.8"))), patch(
            "aiohttp.connector.aiohappyeyeballs.start_connection", self.connect_public_to_fixture,
        ):
            async with http.PublicSession() as session:
                async with session.get(f"http://source.example:{self.port}/catalog?q=one") as response:
                    self.assertEqual(await response.text(), "safe")
        self.assertEqual(len(self.requests), 1)
        self.assertIn(b"GET /catalog?q=one HTTP/1.1\r\n", self.requests[0])
        self.assertIn(f"Host: source.example:{self.port}\r\n".encode(), self.requests[0])

    async def test_public_redirect_to_private_address_stops_before_another_connection(self):
        self.redirect = f"http://127.0.0.1:{self.port}/private"
        with patch.object(http.aiohttp.resolver.DefaultResolver, "resolve",
                          AsyncMock(return_value=self.answers("8.8.8.8"))), patch(
            "aiohttp.connector.aiohappyeyeballs.start_connection", self.connect_public_to_fixture,
        ):
            async with http.PublicSession() as session:
                with self.assertRaises(ValueError):
                    async with session.get(f"http://source.example:{self.port}/redirect"):
                        pass
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__":
    unittest.main()
