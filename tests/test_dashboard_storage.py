"""Dashboard storage contract checks using a private database and real files."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

STATE = tempfile.TemporaryDirectory()
os.environ["STATE_DIR"] = STATE.name
os.environ["DATABASE_URL"] = f"sqlite:///{STATE.name}/dashboard.db"
os.environ["SECRET_KEY"] = "dashboard-test-key-" * 4
os.environ["SERVICE_API_KEY"] = "dashboard-service-key-" * 4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from fastapi import FastAPI
from app.api.v1.api import api_router
from app.api.v1.endpoints import auth, system
from app.core.config import settings
from app.core.database import Base, engine, AsyncSessionLocal
from app.core.system import SystemManager
from app.models.user import User


class DashboardStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        self.root = Path(self.files.name)
        self.data_dir = self.root / "data"
        self.piles_dir = self.root / "piles"
        self.data_dir.mkdir()
        self.piles_dir.mkdir()
        self.enterContext(patch.object(settings, "data_dir", str(self.data_dir)))
        self.enterContext(patch.object(settings, "piles_dir", str(self.piles_dir)))
        self.enterContext(patch.object(system, "system_manager", SystemManager()))
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as db:
            db.add(User(username="admin", hashed_password=auth.hash_password("dashboard-test-password"),
                        role="admin", is_active=True))
            await db.commit()
        app = FastAPI()
        app.include_router(api_router, prefix="/api/v1")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        response = await self.client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "dashboard-test-password",
        })
        self.assertEqual(response.status_code, 200, response.text)

    async def storage(self):
        response = await self.client.get("/api/v1/system/storage")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["success"], body)
        data = body["data"]
        for field in ("content_size_bytes", "total_bytes", "available_bytes", "piles_size_bytes"):
            self.assertIn(field, data)
            self.assertIsInstance(data[field], int)
            self.assertGreaterEqual(data[field], 0)
        return data

    async def test_empty_storage_has_numeric_dashboard_fields_after_login(self):
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 0)
        self.assertEqual(data["piles_size_bytes"], 0)

    async def test_counts_files_and_piles_recursively(self):
        (self.data_dir / "nested").mkdir()
        (self.data_dir / "nested" / "notes.txt").write_bytes(b"notes")
        (self.piles_dir / "book.zim").write_bytes(b"reference")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 14)
        self.assertEqual(data["piles_size_bytes"], 9)

    async def test_nested_piles_root_does_not_double_count_content(self):
        nested = self.data_dir / "piles"
        nested.mkdir()
        settings.piles_dir = str(nested)
        (self.data_dir / "notes.txt").write_bytes(b"notes")
        (nested / "book.zim").write_bytes(b"reference")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 14)
        self.assertEqual(data["piles_size_bytes"], 9)

    async def test_identical_roots_count_each_file_once(self):
        settings.piles_dir = str(self.data_dir)
        (self.data_dir / "notes.txt").write_bytes(b"notes")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 5)
        self.assertEqual(data["piles_size_bytes"], 5)

    async def test_hard_link_in_second_root_counts_once(self):
        original = self.data_dir / "notes.txt"
        original.write_bytes(b"notes")
        os.link(original, self.piles_dir / "notes.txt")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 5)

    async def test_symbolic_links_do_not_count_outside_content(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "private.txt").write_bytes(b"outside content")
        (self.data_dir / "notes.txt").write_bytes(b"notes")
        (self.data_dir / "linked-dir").symlink_to(outside, target_is_directory=True)
        (self.piles_dir / "linked-file").symlink_to(outside / "private.txt")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 5)
        self.assertEqual(data["piles_size_bytes"], 0)

    async def test_missing_piles_directory_has_zero_pile_bytes(self):
        self.piles_dir.rmdir()
        (self.data_dir / "notes.txt").write_bytes(b"notes")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 5)
        self.assertEqual(data["piles_size_bytes"], 0)

    async def test_missing_data_directory_still_counts_piles(self):
        self.data_dir.rmdir()
        (self.piles_dir / "book.zim").write_bytes(b"reference")
        data = await self.storage()
        self.assertEqual(data["content_size_bytes"], 9)

    async def test_storage_still_requires_login(self):
        self.client.cookies.clear()
        response = await self.client.get("/api/v1/system/storage")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
