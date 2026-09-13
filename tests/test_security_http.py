"""Outbound tests stub transport only; no external network is contacted."""
import io
import os
from pathlib import Path
import sys
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


if __name__ == "__main__":
    unittest.main()
