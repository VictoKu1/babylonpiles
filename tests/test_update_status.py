"""Update routing regressions with an isolated database dependency."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

STATE = tempfile.TemporaryDirectory()
os.environ["STATE_DIR"] = STATE.name
os.environ["DATABASE_URL"] = f"sqlite:///{STATE.name}/updates.db"
os.environ["SECRET_KEY"] = "updates-test-key-" * 4
os.environ["SERVICE_API_KEY"] = "updates-service-key-" * 4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.api.v1.endpoints import updates
from app.core.database import Base, get_db
from app.models.pile import Pile
from app.models.update_log import UpdateLog


class UpdateStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMock()
        app = FastAPI()
        app.include_router(updates.router, prefix="/api/v1/updates")

        async def test_db():
            yield self.db

        app.dependency_overrides[get_db] = test_db
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_status_url_returns_summary_instead_of_log_id_validation(self):
        recent = Mock()
        recent.scalars.return_value.all.return_value = []
        counts = Mock()
        counts.all.return_value = [("completed", 1), ("completed", 2), ("running", 3)]
        downloading = Mock()
        downloading.scalars.return_value.all.return_value = []
        self.db.execute.side_effect = [recent, counts, downloading]

        response = await self.client.get("/api/v1/updates/status")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "success": True,
            "data": {
                "recent_logs": [], "status_counts": {"completed": 2, "running": 1},
                "downloading_piles": [], "total_downloading": 0,
            },
        })

    async def test_numeric_log_id_still_returns_specific_log(self):
        log = Mock()
        log.to_dict.return_value = {"id": 7, "status": "completed"}
        result = Mock()
        result.scalar_one_or_none.return_value = log
        self.db.execute.return_value = result

        response = await self.client.get("/api/v1/updates/7")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "success": True, "data": {"id": 7, "status": "completed"},
        })

    async def test_missing_log_id_still_returns_not_found(self):
        result = Mock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        response = await self.client.get("/api/v1/updates/7")

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"], "Update log not found")


class RollbackLogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            pile = Pile(
                name="test-pile", display_name="Test pile", category="test",
                source_type="http", version="current", checksum="a" * 64,
                file_path="current.zim", file_size=100,
            )
            db.add(pile)
            await db.commit()
            self.pile_id = pile.id

        async def test_db():
            async with self.sessions() as db:
                yield db

        app = FastAPI()
        app.include_router(updates.router, prefix="/api/v1/updates")
        app.dependency_overrides[get_db] = test_db
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_success_log_records_restored_backup_metadata(self):
        async def restore(pile, version):
            pile.version = "20260101_120000"
            pile.checksum = "b" * 64
            pile.file_path = "restored.zim"
            pile.file_size = 75
            return True

        with patch.object(updates, "content_updater", SimpleNamespace(rollback_pile=restore)):
            response = await self.client.post(f"/api/v1/updates/pile/{self.pile_id}/rollback")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["version"], "20260101_120000")
        async with self.sessions() as db:
            log = await db.get(UpdateLog, body["data"]["id"])
            self.assertEqual(log.status, "completed")
            self.assertEqual(log.version, "20260101_120000")
            self.assertEqual(log.checksum, "b" * 64)
            self.assertEqual(log.file_path, "restored.zim")
            self.assertEqual(log.file_size, 75)
            self.assertIsNotNone(log.completed_at)
            self.assertGreaterEqual(log.duration_seconds, 0)

    async def test_failed_restore_does_not_log_success_metadata(self):
        updater = SimpleNamespace(rollback_pile=AsyncMock(return_value=False))
        with patch.object(updates, "content_updater", updater):
            response = await self.client.post(f"/api/v1/updates/pile/{self.pile_id}/rollback")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["success"])
        async with self.sessions() as db:
            log = await db.get(UpdateLog, body["data"]["id"])
            self.assertEqual(log.status, "failed")
            self.assertIsNone(log.checksum)
            self.assertIsNone(log.file_path)
            self.assertIsNone(log.file_size)
            self.assertIsNone(log.completed_at)
            pile = await db.get(Pile, self.pile_id)
            self.assertEqual(pile.version, "current")


if __name__ == "__main__":
    unittest.main()
