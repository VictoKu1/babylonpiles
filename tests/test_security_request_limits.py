"""Request body limits run before parsing or mutation, including untrusted framing."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile


class RequestLimitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.actions = []
        self.buffers = []

    def middleware(self, app=None, **options):
        from app.core.request_limits import RequestBodyLimitMiddleware
        return RequestBodyLimitMiddleware(
            app or self.record_request, max_upload_size=2 * 1024 * 1024,
            temp_dir=self.temp.name, **options,
        )

    def track_buffers(self):
        original = tempfile.SpooledTemporaryFile

        def allocate(*args, **kwargs):
            buffer = original(*args, **kwargs)
            self.buffers.append(buffer)
            return buffer

        return patch("app.core.request_limits.SpooledTemporaryFile", side_effect=allocate)

    async def record_request(self, scope, receive, send):
        body = bytearray()
        while True:
            message = await receive()
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        self.actions.append(bytes(body))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def request(self, app, chunks, path="/api/v1/auth/login", headers=(), method="POST"):
        responses = []
        received = []
        pending = iter(chunks)

        async def receive():
            message = next(pending, {"type": "http.disconnect"})
            received.append(message)
            return message

        async def send(message):
            responses.append(message)

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": method, "path": path, "raw_path": path.encode(),
                 "query_string": b"", "headers": list(headers), "scheme": "http",
                 "server": ("testserver", 80), "client": ("127.0.0.1", 1234)}
        await app(scope, receive, send)
        return responses, received

    def chunk(self, body, more=False):
        return {"type": "http.request", "body": body, "more_body": more}

    def assert_status(self, responses, status):
        self.assertEqual([message["status"] for message in responses if message["type"] == "http.response.start"], [status])
        self.assertEqual(responses[-1]["type"], "http.response.body")
        self.assertFalse(responses[-1].get("more_body", False))

    def assert_clean(self):
        self.assertTrue(all(buffer.closed for buffer in self.buffers))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    async def test_small_login_json_reaches_the_real_fastapi_parser_unchanged(self):
        app = FastAPI()

        @app.post("/api/v1/auth/login")
        async def login(request: Request):
            data = await request.json()
            self.actions.append(data)
            return {"username": data["username"]}

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.middleware(app)), base_url="http://testserver") as client:
            response = await client.post("/api/v1/auth/login", json={"username": "operator", "password": "test password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"username": "operator"})
        self.assertEqual(self.actions, [{"username": "operator", "password": "test password"}])
        self.assert_clean()

    async def test_valid_multipart_upload_survives_disk_staging_and_replay(self):
        app = FastAPI()
        payload = b"archive contents\x00" * 8000

        @app.post("/api/v1/files/upload")
        async def upload(file: UploadFile = File(...), path: str = Form("")):
            self.actions.append((file.filename, path, await file.read()))
            return {"uploaded": True}

        middleware = self.middleware(app)
        with self.track_buffers():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=middleware), base_url="http://testserver") as client:
                response = await client.post("/api/v1/files/upload", files={"file": ("archive.zim", payload)}, data={"path": "nested folder"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.actions, [("archive.zim", "nested folder", payload)])
        self.assertTrue(self.buffers)
        self.assertTrue(self.buffers[0]._rolled, "accepted large bodies must spill to disk")
        self.assert_clean()

    async def test_oversized_content_length_is_rejected_without_reading_or_running_handlers(self):
        responses, received = await self.request(self.middleware(), [self.chunk(b"small")], headers=[(b"content-length", b"1048577")])
        self.assert_status(responses, 413)
        self.assertEqual(received, [])
        self.assertEqual(self.actions, [])
        self.assertEqual(json.loads(responses[-1]["body"])["detail"], "Request body too large")
        self.assert_clean()

    async def test_chunked_and_forged_length_overflow_stop_before_parsing_or_mutation(self):
        middleware = self.middleware()
        for headers in ([(b"transfer-encoding", b"chunked")], [(b"content-length", b"1")]):
            with self.subTest(headers=headers), self.track_buffers():
                responses, received = await self.request(middleware, [
                    self.chunk(b"a" * 524288, True), self.chunk(b"b" * 524288, True),
                    self.chunk(b"c", True), self.chunk(b"must not be consumed"),
                ], headers=headers)
            self.assert_status(responses, 413)
            self.assertEqual(len(received), 3)
            self.assertEqual(self.actions, [])
            self.assert_clean()

    async def test_upload_routes_allow_only_the_configured_size_plus_multipart_overhead(self):
        middleware = self.middleware()
        cap = 2 * 1024 * 1024 + 65536
        for path in ("/api/v1/files/upload", "/api/v1/piles/7/upload", "/api/v1/files/upload/"):
            with self.subTest(path=path):
                responses, _ = await self.request(middleware, [self.chunk(b"x" * cap)], path=path)
                self.assert_status(responses, 200)
                responses, received = await self.request(middleware, [self.chunk(b"x" * cap, True), self.chunk(b"x")], path=path)
                self.assert_status(responses, 413)
                self.assertEqual(len(received), 2)
        self.assertEqual(len(self.actions), 3)
        self.assert_clean()

    async def test_oversized_multipart_never_enters_the_multipart_parser(self):
        app = FastAPI()

        @app.post("/api/v1/files/upload")
        async def upload(file: UploadFile = File(...)):
            self.actions.append(await file.read())
            return {"uploaded": True}

        middleware = self.middleware(app)
        with patch("starlette.formparsers.SpooledTemporaryFile", wraps=tempfile.SpooledTemporaryFile) as parser_files:
            responses, _ = await self.request(middleware, [self.chunk(b"x" * (2 * 1024 * 1024 + 65537))],
                path="/api/v1/files/upload", headers=[(b"content-type", b"multipart/form-data; boundary=TEST")])
        self.assert_status(responses, 413)
        self.assertFalse(parser_files.called)
        self.assertEqual(self.actions, [])
        self.assert_clean()

    async def test_other_endpoints_cannot_claim_the_larger_upload_budget(self):
        middleware = self.middleware()
        for path in ("/api/v1/system/hotspot/request-upload", "/api/v1/files/upload/extra", "/api/v1/piles/not-an-id/upload"):
            responses, _ = await self.request(middleware, [self.chunk(b"x" * 1048577)], path=path,
                                             headers=[(b"content-type", b"multipart/form-data; boundary=TEST")])
            self.assert_status(responses, 413)
        self.assertEqual(self.actions, [])

    async def test_exact_general_limit_and_empty_bodies_are_forwarded(self):
        middleware = self.middleware()
        for body in (b"", b"x" * 1048576):
            responses, _ = await self.request(middleware, [self.chunk(body)])
            self.assert_status(responses, 200)
        self.assertEqual(self.actions, [b"", b"x" * 1048576])
        self.assert_clean()

    async def test_disconnect_discards_staging_without_running_handlers(self):
        middleware = self.middleware()
        with self.track_buffers():
            responses, _ = await self.request(middleware, [self.chunk(b"x" * 131072, True), {"type": "http.disconnect"}])
        self.assertEqual(responses, [])
        self.assertEqual(self.actions, [])
        self.assert_clean()

    async def test_invalid_or_conflicting_lengths_are_rejected(self):
        for headers in ([(b"content-length", b"-1")], [(b"content-length", b"abc")], [(b"content-length", b"1"), (b"content-length", b"2")]):
            responses, received = await self.request(self.middleware(), [self.chunk(b"x")], headers=headers)
            self.assert_status(responses, 400)
            self.assertEqual(received, [])
        self.assertEqual(self.actions, [])

    async def test_cancelled_stream_cleans_staging_and_releases_capacity(self):
        middleware = self.middleware(max_concurrent_bodies=1)
        waiting = asyncio.Event()
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return self.chunk(b"x" * 131072, True)
            waiting.set()
            await asyncio.Future()

        async def send(message):
            self.fail("Cancelled request must not emit a response")

        scope = {"type": "http", "path": "/api/v1/auth/login", "headers": []}
        with self.track_buffers():
            task = asyncio.create_task(middleware(scope, receive, send))
            await asyncio.wait_for(waiting.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assert_clean()
        responses, _ = await self.request(middleware, [self.chunk(b"next")])
        self.assert_status(responses, 200)
        self.assertEqual(self.actions, [b"next"])

    async def test_concurrent_stream_cap_rejects_excess_without_reading_it(self):
        middleware = self.middleware(max_concurrent_bodies=1)
        waiting = asyncio.Event()
        resume = asyncio.Event()

        async def slow_receive():
            waiting.set()
            await resume.wait()
            return self.chunk(b"first")

        async def send(message):
            pass

        first = asyncio.create_task(middleware({"type": "http", "path": "/api/v1/auth/login", "headers": []}, slow_receive, send))
        try:
            await asyncio.wait_for(waiting.wait(), 2)
            responses, received = await self.request(middleware, [self.chunk(b"excess")])
            self.assert_status(responses, 503)
            self.assertEqual(received, [])
        finally:
            resume.set()
            await first
        responses, _ = await self.request(middleware, [self.chunk(b"next")])
        self.assert_status(responses, 200)
        self.assertEqual(self.actions, [b"first", b"next"])

    async def test_stalled_stream_times_out_and_cleans_temporary_files(self):
        middleware = self.middleware(receive_timeout=0.02)
        responses = []
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return self.chunk(b"x" * 131072, True)
            await asyncio.Future()

        async def send(message):
            responses.append(message)

        with self.track_buffers():
            await middleware({"type": "http", "path": "/api/v1/auth/login", "headers": []}, receive, send)
        self.assert_status(responses, 408)
        self.assertEqual(self.actions, [])
        self.assert_clean()

    async def test_bodyless_media_responses_do_not_hold_incoming_body_capacity(self):
        responding = asyncio.Event()
        finish = asyncio.Event()

        async def app(scope, receive, send):
            if scope["path"] == "/media":
                await send({"type": "http.response.start", "status": 200, "headers": []})
                responding.set()
                await finish.wait()
                await send({"type": "http.response.body", "body": b"media"})
            else:
                await self.record_request(scope, receive, send)

        middleware = self.middleware(app, max_concurrent_bodies=1)
        media = asyncio.create_task(self.request(middleware, [self.chunk(b"")], path="/media", method="GET"))
        try:
            await asyncio.wait_for(responding.wait(), 2)
            responses, _ = await self.request(middleware, [self.chunk(b"login")])
            self.assert_status(responses, 200)
        finally:
            finish.set()
            await media

    async def test_handler_errors_close_staging_and_release_capacity(self):
        fail = True

        async def app(scope, receive, send):
            nonlocal fail
            if fail:
                fail = False
                raise RuntimeError("handler failed")
            await self.record_request(scope, receive, send)

        middleware = self.middleware(app, max_concurrent_bodies=1)
        with self.track_buffers(), self.assertRaisesRegex(RuntimeError, "handler failed"):
            await self.request(middleware, [self.chunk(b"x" * 131072)])
        self.assert_clean()
        responses, _ = await self.request(middleware, [self.chunk(b"next")])
        self.assert_status(responses, 200)
        self.assertEqual(self.actions, [b"next"])

    async def test_main_application_rejects_oversized_bodies_before_routing(self):
        from main import app
        responses, received = await self.request(app, [self.chunk(b"small")], path="/health",
                                                 method="GET", headers=[(b"content-length", b"1048577")])
        self.assert_status(responses, 413)
        self.assertEqual(received, [])


if __name__ == "__main__":
    unittest.main()
