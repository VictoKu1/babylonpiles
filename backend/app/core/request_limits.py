"""Bound incoming bodies before multipart parsing or endpoint side effects."""
import asyncio
import re
from tempfile import SpooledTemporaryFile
from typing import Optional

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    """Stage a bounded body, then replay it to the application in small chunks.

    Content-Length is only an early rejection hint: actual ASGI bytes always count.
    Staging prevents parsers and handlers from observing a truncated oversized body.
    At most four requests per worker can hold staging files, each with at most 64 KiB
    in memory; the remaining accepted bytes spill to temporary disk and are removed
    on every exit path. Receiving the body has a five-minute total deadline.
    """

    GENERAL_LIMIT = 1024 * 1024
    MULTIPART_OVERHEAD = 64 * 1024
    CHUNK_SIZE = 64 * 1024
    PILE_UPLOAD = re.compile(r"/api/v1/piles/[0-9]+/upload")

    def __init__(
        self,
        app: ASGIApp,
        max_upload_size: int,
        temp_dir: Optional[str] = None,
        max_concurrent_bodies: int = 4,
        receive_timeout: float = 300,
    ):
        if max_upload_size <= 0 or max_concurrent_bodies <= 0 or receive_timeout <= 0:
            raise ValueError("Request limits must be positive")
        self.app = app
        self.upload_limit = max_upload_size + self.MULTIPART_OVERHEAD
        self.temp_dir = temp_dir
        self.max_concurrent_bodies = max_concurrent_bodies
        self.receive_timeout = receive_timeout
        self.active_bodies = 0

    async def reject(self, scope: Scope, receive: Receive, send: Send, status: int, detail: str):
        # Do not drain rejected bodies. Close HTTP/1 connections so unread bytes
        # cannot be mistaken for another request on a persistent connection.
        headers = {"Connection": "close"} if scope.get("http_version", "1.1") in ("1.0", "1.1") else {}
        response = JSONResponse({"detail": detail}, status_code=status, headers=headers)
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "").rstrip("/")
        limit = self.upload_limit if path == "/api/v1/files/upload" or self.PILE_UPLOAD.fullmatch(path) else self.GENERAL_LIMIT
        lengths = []
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            value = value.strip()
            if not value.isdigit():
                await self.reject(scope, receive, send, 400, "Invalid Content-Length")
                return
            # Compare decimal lengths before conversion, including absurdly long
            # numeric headers that Python intentionally refuses to parse as int.
            value = value.lstrip(b"0") or b"0"
            maximum = str(limit).encode("ascii")
            if len(value) > len(maximum) or (len(value) == len(maximum) and value > maximum):
                await self.reject(scope, receive, send, 413, "Request body too large")
                return
            lengths.append(int(value))
        if len(set(lengths)) > 1:
            await self.reject(scope, receive, send, 400, "Conflicting Content-Length headers")
            return

        # There is no await between checking and taking a slot; ASGI tasks on this
        # worker's event loop cannot race the counter. Reject instead of queueing
        # an unbounded number of additional incoming bodies.
        if self.active_bodies >= self.max_concurrent_bodies:
            await self.reject(scope, receive, send, 503, "Too many incoming requests; please retry")
            return
        self.active_bodies += 1
        slot_held = True
        try:
            with SpooledTemporaryFile(max_size=self.CHUNK_SIZE, mode="w+b", dir=self.temp_dir) as body:
                size = 0
                failure = None
                try:
                    async with asyncio.timeout(self.receive_timeout):
                        while True:
                            message = await receive()
                            if message["type"] == "http.disconnect":
                                return
                            if message["type"] != "http.request":
                                failure = (400, "Invalid request body")
                                break
                            chunk = message.get("body", b"")
                            size += len(chunk)
                            if size > limit:
                                failure = (413, "Request body too large")
                                break
                            if chunk:
                                # Roll over before a large ASGI chunk is written,
                                # so the spool never temporarily grows past 64 KiB.
                                if size > self.CHUNK_SIZE:
                                    await run_in_threadpool(body.rollover)
                                await run_in_threadpool(body.write, chunk)
                            more_body = message.get("more_body", False)
                            # Do not retain an ASGI server's final input chunk
                            # while the application parses the staged body.
                            del chunk, message
                            if not more_body:
                                break
                except TimeoutError:
                    failure = (408, "Request body timed out")
                if failure:
                    # Sending the response is outside the receive deadline, so a
                    # timeout cannot interrupt one status and emit a second one.
                    await self.reject(scope, receive, send, *failure)
                    return

                if size:
                    await run_in_threadpool(body.seek, 0)
                else:
                    # Bodyless GETs, including long-lived media responses, do not
                    # consume staging capacity while their responses are sent.
                    body.close()
                    self.active_bodies -= 1
                    slot_held = False
                remaining = size
                complete = False

                async def replay():
                    nonlocal remaining, complete
                    if complete:
                        return await receive()
                    chunk = await run_in_threadpool(body.read, min(remaining, self.CHUNK_SIZE)) if remaining else b""
                    remaining -= len(chunk)
                    complete = remaining == 0
                    return {"type": "http.request", "body": chunk, "more_body": not complete}

                await self.app(scope, replay, send)
        finally:
            if slot_held:
                self.active_bodies -= 1
