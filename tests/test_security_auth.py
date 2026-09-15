"""Isolated authentication regressions; never uses the deployed database."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

STATE = tempfile.TemporaryDirectory()
os.environ["STATE_DIR"] = STATE.name
os.environ["DATABASE_URL"] = f"sqlite:///{STATE.name}/auth.db"
os.environ["SECRET_KEY"] = "security-test-key-" * 4
os.environ["SERVICE_API_KEY"] = "service-test-key-" * 4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import select
from app.api.v1.api import api_router
from app.api.v1.endpoints import auth
from app.core.database import Base, engine, AsyncSessionLocal, init_db
from app.models.user import User


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.app = FastAPI()
        self.app.include_router(api_router, prefix="/api/v1")
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        )
        hasher = getattr(auth, "hash_password", lambda password: password)
        hashes = await asyncio.gather(*(asyncio.to_thread(hasher, password) for password in
                                      ("test-admin-password", "test-reader-password", "test-disabled-password")))
        async with AsyncSessionLocal() as db:
            db.add_all([
                User(username="admin", hashed_password=hashes[0], role="admin", is_active=True),
                User(username="reader", hashed_password=hashes[1], role="user", is_active=True),
                User(username="disabled", hashed_password=hashes[2], role="admin", is_active=False),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.client.aclose()

    async def login(self, username="admin", password="test-admin-password"):
        return await self.client.post("/api/v1/auth/login", json={"username": username, "password": password})

    async def test_anonymous_clients_cannot_read_private_management_data(self):
        response = await self.client.get("/api/v1/piles/")
        self.assertEqual(response.status_code, 401, response.text)

    async def test_json_login_sets_private_session_and_allows_admin_reads(self):
        response = await self.login()
        self.assertEqual(response.status_code, 200, response.text)
        cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertEqual((await self.client.get("/api/v1/piles/")).status_code, 200)
        self.assertTrue((await self.client.get("/api/v1/auth/me")).json()["data"]["is_admin"])

    async def test_query_only_credentials_are_rejected(self):
        response = await self.client.post("/api/v1/auth/login", params={"username": "admin", "password": "test-admin-password"})
        self.assertEqual(response.status_code, 422)

    async def test_reader_cannot_perform_admin_operations(self):
        response = await self.login("reader", "test-reader-password")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.client.get("/api/v1/piles/")).status_code, 403)

    async def test_inactive_accounts_cannot_log_in(self):
        response = await self.login("disabled", "test-disabled-password")
        self.assertEqual(response.status_code, 401)

    async def test_registration_requires_admin_and_hashes_password(self):
        body = {"username": "new-user", "password": "new-user-password"}
        response = await self.client.post("/api/v1/auth/register", json=body)
        self.assertEqual(response.status_code, 401)
        self.assertEqual((await self.login()).status_code, 200)
        response = await self.client.post("/api/v1/auth/register", json=body, headers={"Origin": "http://testserver"})
        self.assertEqual(response.status_code, 200, response.text)
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.username == "new-user"))).scalar_one()
            self.assertNotEqual(user.hashed_password, body["password"])
            self.assertTrue(auth.verify_password(body["password"], user.hashed_password))

    async def test_cookie_mutations_reject_foreign_or_missing_origin(self):
        self.assertEqual((await self.login()).status_code, 200)
        body = {"username": "new-user", "password": "new-user-password"}
        for origin in [None, "http://attacker.invalid", "http://testserver.attacker.invalid"]:
            response = await self.client.post("/api/v1/auth/register", json=body, headers={"Origin": origin} if origin else {})
            self.assertEqual(response.status_code, 403, (origin, response.text))

    async def test_known_default_jwt_key_is_not_accepted(self):
        token = jwt.encode({"sub": "1", "exp": 4102444800}, "your-secret-key-change-in-production", algorithm="HS256")
        response = await self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    async def test_logout_clears_session(self):
        self.assertEqual((await self.login()).status_code, 200)
        response = await self.client.post("/api/v1/auth/logout", headers={"Origin": "http://testserver"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await self.client.get("/api/v1/auth/me")).status_code, 401)

    async def test_wrong_password_and_foreign_login_origin_are_rejected(self):
        self.assertEqual((await self.login(password="incorrect-password")).status_code, 401)
        response = await self.client.post("/api/v1/auth/login", json={"username": "admin", "password": "test-admin-password"},
                                          headers={"Origin": "https://attacker.invalid"})
        self.assertEqual(response.status_code, 403)

    async def test_account_disabled_after_login_invalidates_existing_token(self):
        response = await self.login()
        token = response.json()["data"]["access_token"]
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.username == "admin"))).scalar_one()
            user.is_active = False
            await db.commit()
        self.assertEqual((await self.client.get("/api/v1/piles/", headers={"Authorization": f"Bearer {token}"})).status_code, 401)

    async def test_legacy_password_migration_is_persistent_and_preserves_login(self):
        async with AsyncSessionLocal() as db:
            db.add(User(username="legacy", hashed_password="legacy-password", role="admin", is_active=True))
            await db.commit()
        await init_db()
        async with AsyncSessionLocal() as db:
            stored = (await db.execute(select(User).where(User.username == "legacy"))).scalar_one().hashed_password
        self.assertNotEqual(stored, "legacy-password")
        await init_db()
        async with AsyncSessionLocal() as db:
            self.assertEqual((await db.execute(select(User).where(User.username == "legacy"))).scalar_one().hashed_password, stored)
        self.assertEqual((await self.login("legacy", "legacy-password")).status_code, 200)


if __name__ == "__main__":
    unittest.main()
