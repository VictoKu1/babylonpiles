"""Public-only HTTP transport: validate actual DNS answers and every redirect."""
from contextlib import asynccontextmanager
import ipaddress
import json
import re
import socket

import aiohttp
from aiohttp.abc import AbstractResolver
from yarl import URL

from app.core.config import settings
from app.core.transfers import TransferTooLarge


def public_address(value: str) -> str:
    address = ipaddress.ip_address(value)
    mapped = getattr(address, "ipv4_mapped", None)
    transition = getattr(address, "sixtofour", None) or getattr(address, "teredo", None)
    if not address.is_global or transition or (mapped is not None and not mapped.is_global):
        raise ValueError("Content sources must use public network addresses")
    return str(address)


def validate_url(value: str) -> URL:
    try:
        url = URL(value)
        if url.scheme not in {"http", "https"} or not url.host or url.user is not None or url.password is not None:
            raise ValueError("Use an HTTP(S) source URL without credentials")
        if any(ord(c) < 32 for c in str(value)) or "%" in url.host or "\\" in str(value):
            raise ValueError("Invalid source URL")
        # Force validation of malformed/out-of-range ports before any request.
        if not url.port or not 1 <= url.port <= 65535:
            raise ValueError("Invalid source port")
        try:
            ipaddress.ip_address(url.host)
        except ValueError:
            if url.host.rstrip(".").lower() in {"localhost", "localhost.localdomain"}:
                raise ValueError("Local content sources are not allowed")
        else:
            public_address(url.host)
        return url.with_fragment(None)
    except (TypeError, UnicodeError) as exc:
        raise ValueError("Invalid source URL") from exc


class PublicResolver(AbstractResolver):
    def __init__(self):
        self.delegate = aiohttp.resolver.DefaultResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        answers = await self.delegate.resolve(host, port, family)
        if not answers:
            raise ValueError("Source hostname has no addresses")
        for answer in answers:
            public_address(answer["host"])
        # aiohttp connects directly to these validated answers, without a second
        # hostname lookup. Mixed public/private answers fail closed above.
        return answers

    async def close(self):
        await self.delegate.close()


class BoundedContent:
    def __init__(self, content, limit):
        self.content, self.limit, self.count = content, limit, 0

    async def read(self, n=-1):
        if n < 0:
            parts = []
            async for part in self.iter_chunked(65536):
                parts.append(part)
            return b"".join(parts)
        data = await self.content.read(min(n, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise TransferTooLarge("Source response exceeds the configured size limit")
        return data

    async def iter_chunked(self, n):
        while True:
            part = await self.read(n)
            if not part:
                break
            yield part


class PublicResponse:
    def __init__(self, response, limit):
        self.response = response
        self.content = BoundedContent(response.content, limit)
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > limit:
            raise TransferTooLarge("Source response exceeds the configured size limit")

    def __getattr__(self, name):
        return getattr(self.response, name)

    async def text(self, encoding=None, errors="strict"):
        return (await self.content.read()).decode(encoding or self.response.charset or "utf-8", errors)

    async def json(self, **kwargs):
        return json.loads(await self.text())


class PublicSession:
    def __init__(self, *, timeout=None, max_bytes=None):
        self.limit = max_bytes or settings.max_file_size
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=PublicResolver(), limit=8),
            timeout=timeout or aiohttp.ClientTimeout(total=3600, connect=15, sock_read=60),
            trust_env=False,
        )

    @property
    def closed(self):
        return self.session.closed

    async def close(self):
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    @asynccontextmanager
    async def get(self, url, *, timeout=None, allow_redirects=True, max_bytes=None, headers=None):
        current = validate_url(str(url))
        for hop in range(6):
            # Validate the exact serialized value passed to the transport. This
            # syntax check supplements the public IP/DNS policy above; it does
            # not replace address checks or per-redirect validation.
            request_url = str(current)
            if not re.fullmatch(
                r"https?://(?:[A-Za-z0-9._~!$&'()*+,;=-]+|\[[A-Fa-f0-9:.]+\])"
                r"(?::[0-9]{1,5})?(?:[/?][^\s#]*)?",
                request_url,
            ):
                raise ValueError("Invalid source URL syntax")
            options = {"allow_redirects": False}
            if timeout is not None:
                options["timeout"] = timeout
            if headers is not None:
                options["headers"] = headers
            async with self.session.get(request_url, **options) as response:
                if allow_redirects and response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location or hop == 5:
                        raise ValueError("Invalid or excessive source redirects")
                    current = validate_url(str(current.join(URL(location))))
                    continue
                yield PublicResponse(response, max_bytes or self.limit)
                return
