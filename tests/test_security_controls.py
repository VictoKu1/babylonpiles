"""Request throttling and credential-free security audit regressions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

STATE = tempfile.TemporaryDirectory()
os.environ.update(STATE_DIR=STATE.name, DATABASE_URL=f"sqlite:///{STATE.name}/controls.db",
                  SECRET_KEY="controls-test-secret-" * 4, SERVICE_API_KEY="controls-test-service-" * 4)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from fastapi import FastAPI
from app.api.v1.endpoints import auth
from app.core.config import settings
from app.core.database import Base, engine, AsyncSessionLocal
from app.core.security_controls import RateLimiter, SecurityControlsMiddleware
from app.models.user import User


class WindowTests(unittest.TestCase):
    def test_expiry_recovers_and_retry_is_positive(self):
        now = [0.0]
        limiter = RateLimiter(window_seconds=60, max_keys=2, clock=lambda: now[0])
        self.assertEqual(limiter.check("one", 1), 0)
        self.assertEqual(limiter.check("one", 1), 60)
        now[0] = 59.5
        self.assertEqual(limiter.check("one", 1), 1)
        now[0] = 60
        self.assertEqual(limiter.check("one", 1), 0)

    def test_new_keys_cannot_evict_throttled_clients(self):
        now = [0.0]
        limiter = RateLimiter(window_seconds=60, max_keys=2, clock=lambda: now[0])
        self.assertEqual(limiter.check("hot", 1), 0)
        self.assertEqual(limiter.check("other", 1), 0)
        for index in range(10):
            self.assertGreater(limiter.check(f"new-{index}", 1), 0)
        self.assertGreater(limiter.check("hot", 1), 0)
        now[0] = 61
        self.assertEqual(limiter.check("new", 1), 0)


class ControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.object(settings, "login_client_limit", 3))
        self.enterContext(patch.object(settings, "login_account_limit", 2))
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as db:
            db.add(User(username="admin", hashed_password=auth.hash_password("controls-password"),
                        role="admin", is_active=True))
            await db.commit()
        self.app = FastAPI()
        self.app.include_router(auth.router, prefix="/api/v1/auth")
        self.app.add_middleware(SecurityControlsMiddleware, api_limit=50, window_seconds=60)
        self.client = self.make_client("192.0.2.1")

    def make_client(self, host):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=(host, 1)),
                                   base_url="http://testserver", trust_env=False)
        self.addAsyncCleanup(client.aclose)
        return client

    async def login(self, client=None, username="admin", password="wrong-password"):
        return await (client or self.client).post("/api/v1/auth/login",
            json={"username": username, "password": password})

    async def test_account_limit_applies_across_clients_before_hashing(self):
        for index in range(2):
            self.assertEqual((await self.login(self.make_client(f"192.0.2.{index + 2}"))).status_code, 401)
        with patch.object(auth, "verify_password", wraps=auth.verify_password) as verify:
            response = await self.login()
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)
        verify.assert_not_called()

    async def test_client_limit_applies_when_account_names_change(self):
        for index in range(3):
            self.assertEqual((await self.login(username=f"missing-{index}")).status_code, 401)
        self.assertEqual((await self.login(username="new-missing")).status_code, 429)

    async def test_one_proxied_client_cannot_block_another_login(self):
        self.app = FastAPI()
        self.app.include_router(auth.router, prefix="/api/v1/auth")
        self.app.add_middleware(SecurityControlsMiddleware, trusted_proxies="192.0.2.100")
        client = self.make_client("192.0.2.100")
        for index in range(3):
            response = await client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.1"},
                                        json={"username": f"missing-{index}", "password": "wrong"})
            self.assertEqual(response.status_code, 401)
        response = await client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.1"},
                                    json={"username": "admin", "password": "controls-password"})
        self.assertEqual(response.status_code, 429)
        response = await client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "198.51.100.2"},
                                    json={"username": "admin", "password": "controls-password"})
        self.assertEqual(response.status_code, 200)

    async def test_login_limits_apply_to_trailing_slash_alias(self):
        for _ in range(2):
            self.assertEqual((await self.login()).status_code, 401)
        response = await self.client.post("/api/v1/auth/login/", follow_redirects=True,
            json={"username": "admin", "password": "controls-password"})
        self.assertEqual(response.status_code, 429)

    async def test_audit_events_exclude_sensitive_inputs(self):
        with self.assertLogs("app.security.audit", level="INFO") as capture:
            self.assertEqual((await self.login(password="controls-password")).status_code, 200)
            response = await self.login(username="private-user-marker", password="private-password-marker")
            self.assertEqual(response.status_code, 401)
        events = [json.loads(record.getMessage()) for record in capture.records]
        self.assertIn("login.succeeded", [event["event"] for event in events])
        self.assertIn("login.failed", [event["event"] for event in events])
        serialized = json.dumps(events)
        for sensitive in ("private-user-marker", "private-password-marker", "controls-password", "192.0.2.1"):
            self.assertNotIn(sensitive, serialized)
        self.assertNotIn("hashed_password", serialized)
        self.assertNotIn("access_token", serialized)

    async def test_reset_during_login_cannot_issue_new_version_session(self):
        original_refresh = AsyncSessionLocal.class_.refresh
        async def reset_before_refresh(session, user, *args, **kwargs):
            async with AsyncSessionLocal() as other:
                account = await other.get(User, user.id)
                account.hashed_password = auth.hash_password("reset-during-login-password")
                await other.commit()
            await original_refresh(session, user, *args, **kwargs)
        with patch.object(AsyncSessionLocal.class_, "refresh", reset_before_refresh):
            response = await self.login(password="controls-password")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)


class MiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_configured_proxy_hostname_refreshes_and_failed_dns_drops_trust(self):
        seen = []
        async def downstream(scope, receive, send):
            seen.append(scope["state"]["rate_limit_client"])
        middleware = SecurityControlsMiddleware(downstream, trusted_proxies="frontend")
        scope = {"type": "http", "path": "/api/v1/test", "method": "GET",
                 "client": ("192.0.2.100", 1), "headers": [(b"x-forwarded-for", b"198.51.100.2")]}
        with patch("app.core.security_controls.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("192.0.2.100", 0))]) as resolver:
            await middleware(dict(scope), None, None)
            await middleware(dict(scope), None, None)
        self.assertEqual(seen, ["198.51.100.2", "198.51.100.2"])
        self.assertEqual(resolver.call_count, 1)
        middleware.proxy_refresh_at = 0
        with patch("app.core.security_controls.socket.getaddrinfo", side_effect=OSError("unavailable")):
            await middleware(dict(scope), None, None)
        self.assertEqual(seen[-1], "192.0.2.100")

    async def test_trusted_proxy_clients_have_independent_api_limits(self):
        app = FastAPI()
        app.include_router(auth.router, prefix="/api/v1/auth")
        app.add_middleware(SecurityControlsMiddleware, api_limit=3, window_seconds=60,
                           trusted_proxies="192.0.2.100")
        with patch.object(settings, "login_client_limit", 1), patch.object(settings, "login_account_limit", 10):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.0.2.100", 1)),
                                         base_url="http://testserver", trust_env=False) as client:
                # Missing/invalid input still reaches validation and consumes the
                # API window without a database dependency in this test.
                for _ in range(3):
                    response = await client.post("/api/v1/auth/login", json={}, headers={"X-Forwarded-For": "198.51.100.1"})
                    self.assertEqual(response.status_code, 422)
                response = await client.post("/api/v1/auth/login", json={}, headers={"X-Forwarded-For": "198.51.100.1"})
                self.assertEqual(response.status_code, 429)
                response = await client.post("/api/v1/auth/login", json={}, headers={"X-Forwarded-For": "198.51.100.2"})
                self.assertEqual(response.status_code, 422)

    async def test_forwarded_identity_only_accepts_one_valid_ip_from_trusted_peer(self):
        seen = []
        async def downstream(scope, receive, send):
            seen.append(scope["state"]["rate_limit_client"])
        middleware = SecurityControlsMiddleware(downstream, trusted_proxies="192.0.2.100")
        for peer, forwarded, expected in (
            ("192.0.2.100", b"198.51.100.2", "198.51.100.2"),
            ("192.0.2.100", b"::ffff:198.51.100.2", "198.51.100.2"),
            ("192.0.2.100", b"198.51.100.2, 198.51.100.3", "192.0.2.100"),
            ("192.0.2.100", b"not-an-address", "192.0.2.100"),
            ("192.0.2.200", b"198.51.100.2", "192.0.2.200"),
        ):
            scope = {"type": "http", "path": "/api/v1/test", "method": "GET",
                     "client": (peer, 1), "headers": [(b"x-forwarded-for", forwarded)]}
            await middleware(scope, None, None)
            self.assertEqual(seen[-1], expected)

    async def test_rate_limit_does_not_read_body_or_trust_forwarded_headers(self):
        calls = []
        async def downstream(scope, receive, send):
            calls.append(scope["path"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        middleware = SecurityControlsMiddleware(downstream, api_limit=1, window_seconds=60)
        async def call(path, host="192.0.2.1", forwarded=b"192.0.2.5"):
            output = []
            async def receive():
                self.fail("Rate-limit check must run before reading the body")
            async def send(message):
                output.append(message)
            scope = {"type": "http", "http_version": "1.1", "method": "POST", "path": path,
                     "client": (host, 1), "headers": [(b"x-forwarded-for", forwarded)]}
            await middleware(scope, receive, send)
            return output[0]
        self.assertEqual((await call("/api/v1/anything"))["status"], 200)
        blocked = await call("/api/v1/anything", forwarded=b"198.51.100.2")
        self.assertEqual(blocked["status"], 429)
        self.assertIn((b"connection", b"close"), blocked["headers"])
        self.assertIn((b"retry-after", b"60"), blocked["headers"])
        self.assertEqual((await call("/health"))["status"], 200)
        self.assertEqual((await call("/apiculture"))["status"], 200)
        self.assertEqual((await call("/api/v1/anything", host="192.0.2.2"))["status"], 200)
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
