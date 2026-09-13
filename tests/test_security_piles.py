"""Real pile API regressions with independent SQLite and disposable storage."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

TEST_STATE = tempfile.TemporaryDirectory()
os.environ.setdefault("STATE_DIR", TEST_STATE.name)
os.environ.setdefault("SECRET_KEY", "isolated-pile-tests-" * 4)

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from yarl import URL
from app.api.v1.api import api_router
from app.api.v1.endpoints.auth import create_access_token
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.pile import Pile
from app.models.user import User


class RawResponse:
    def __init__(self, body=b"", status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self.content = self
        self.stream = io.BytesIO(body)
        self.charset = "utf-8"
        self.url = URL("https://example.org/book.txt")
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    def raise_for_status(self):
        if self.status >= 400:
            raise ValueError(f"HTTP {self.status}")
    async def read(self, size=-1):
        return self.stream.read(size)
    async def iter_chunked(self, size):
        while chunk := await self.read(size):
            yield chunk


class PileBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        self.piles = self.base / "piles"
        self.outside = self.base / "data-private"
        for path in (self.data, self.piles, self.outside):
            path.mkdir()
        self.secret = self.outside / "secret.txt"
        self.secret.write_bytes(b"private")
        self.patches = [patch.object(settings, "data_dir", str(self.data)),
                        patch.object(settings, "piles_dir", str(self.piles)),
                        patch.object(settings, "max_upload_size", 8),
                        patch.object(settings, "max_file_size", 8)]
        for item in self.patches:
            item.start()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.base}/test.db")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            user = User(username="pile-admin", hashed_password="unused-fixture", role="admin", is_active=True)
            db.add(user)
            await db.commit()
            token = create_access_token({"sub": str(user.id)})
        async def isolated_db():
            async with self.sessions() as db:
                yield db
        app = FastAPI()
        app.dependency_overrides[get_db] = isolated_db
        app.include_router(api_router, prefix="/api/v1")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                                        headers={"Authorization": f"Bearer {token}"})

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    async def create_legacy_pile(self, name="safe", file_path=None, source_url=None, source_type="http"):
        async with self.sessions() as db:
            pile = Pile(name=name, display_name="Fixture", category="test", source_type=source_type,
                        source_url=source_url, file_path=file_path)
            db.add(pile)
            await db.commit()
            return pile.id

    async def get_pile_row(self, pile_id):
        async with self.sessions() as db:
            return (await db.execute(select(Pile).where(Pile.id == pile_id))).scalar_one_or_none()

    async def test_malicious_legacy_name_cannot_write_outside_piles(self):
        pile_id = await self.create_legacy_pile("../data-private/escaped")
        response = await self.client.post(f"/api/v1/piles/{pile_id}/upload", files={"file": ("book.txt", b"attack")})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertFalse((self.outside / "escaped.txt").exists())
        self.assertIsNone((await self.get_pile_row(pile_id)).file_path)

    async def test_malicious_upload_filenames_are_rejected(self):
        pile_id = await self.create_legacy_pile()
        for filename in ("../outside.txt", "C:/outside.txt", ".permissions.json", "%252e%252e.txt"):
            response = await self.client.post(f"/api/v1/piles/{pile_id}/upload", files={"file": (filename, b"attack")})
            self.assertEqual(response.status_code, 400, (filename, response.text))
        self.assertEqual(list(self.piles.iterdir()), [])

    async def test_safe_upload_returns_fresh_metadata_and_downloads(self):
        pile_id = await self.create_legacy_pile("safe name")
        response = await self.client.post(f"/api/v1/piles/{pile_id}/upload", files={"file": ("my book.txt", b"12345678")})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["data"]
        self.assertEqual(result["file_size"], 8)
        self.assertTrue(result["updated_at"])
        self.assertEqual(Path(result["file_path"]), self.piles / "safe name.txt")
        download = await self.client.get(f"/api/v1/piles/{pile_id}/download")
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, b"12345678")

    async def test_oversized_upload_preserves_existing_file_and_database(self):
        target = self.piles / "safe.txt"
        target.write_bytes(b"original")
        pile_id = await self.create_legacy_pile(file_path=str(target))
        response = await self.client.post(f"/api/v1/piles/{pile_id}/upload", files={"file": ("book.txt", b"123456789")})
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual([p.name for p in self.piles.iterdir()], ["safe.txt"])
        self.assertEqual((await self.get_pile_row(pile_id)).file_path, str(target))

    async def test_tainted_stored_paths_cannot_be_downloaded_or_deleted(self):
        pile_id = await self.create_legacy_pile(file_path=str(self.secret))
        for method in (self.client.get, self.client.delete):
            suffix = "/download" if method == self.client.get else ""
            response = await method(f"/api/v1/piles/{pile_id}{suffix}")
            self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.secret.read_bytes(), b"private")
        self.assertIsNotNone(await self.get_pile_row(pile_id))

    async def test_stored_symlink_paths_cannot_be_downloaded_or_deleted(self):
        link = self.piles / "linked.txt"
        link.symlink_to(self.secret)
        pile_id = await self.create_legacy_pile(file_path=str(link))
        self.assertEqual((await self.client.get(f"/api/v1/piles/{pile_id}/download")).status_code, 400)
        self.assertEqual((await self.client.delete(f"/api/v1/piles/{pile_id}")).status_code, 400)
        self.assertEqual(self.secret.read_bytes(), b"private")

    async def test_direct_source_download_blocks_private_destination_before_transport(self):
        pile_id = await self.create_legacy_pile(source_url="http://127.0.0.1/private.txt")
        with patch("aiohttp.ClientSession.get", return_value=RawResponse(b"secret")) as transport:
            response = await self.client.post(f"/api/v1/piles/{pile_id}/download-source")
        self.assertEqual(response.status_code, 400, response.text)
        transport.assert_not_called()
        self.assertFalse((await self.get_pile_row(pile_id)).is_downloading)
        self.assertEqual(list(self.data.iterdir()), [])

    async def test_direct_source_download_revalidates_private_redirect(self):
        pile_id = await self.create_legacy_pile(source_url="https://example.org/book.txt")
        redirected = RawResponse(status=302, headers={"Location": "http://127.0.0.1/private.txt"})
        with patch("aiohttp.ClientSession.get", return_value=redirected) as transport:
            response = await self.client.post(f"/api/v1/piles/{pile_id}/download-source")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(transport.call_count, 1)
        self.assertFalse((await self.get_pile_row(pile_id)).is_downloading)
        self.assertEqual(list(self.data.iterdir()), [])

    async def test_direct_source_oversize_preserves_target_and_resets_status(self):
        target = self.data / "book.txt"
        target.write_bytes(b"original")
        pile_id = await self.create_legacy_pile(source_url="https://example.org/book.txt", file_path=str(target))
        with patch("aiohttp.ClientSession.get", return_value=RawResponse(b"123456789")):
            response = await self.client.post(f"/api/v1/piles/{pile_id}/download-source")
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual([p.name for p in self.data.iterdir()], ["book.txt"])
        row = await self.get_pile_row(pile_id)
        self.assertFalse(row.is_downloading)
        self.assertEqual(row.file_path, str(target))

    async def test_direct_source_success_returns_fresh_database_metadata(self):
        pile_id = await self.create_legacy_pile(source_url="https://example.org/book.txt")
        # A known length invokes the async progress callback, which commits while
        # the download is running and expires SQL-generated timestamp columns.
        with patch("aiohttp.ClientSession.get", return_value=RawResponse(b"12345678", headers={"content-length": "8"})):
            response = await self.client.post(f"/api/v1/piles/{pile_id}/download-source")
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["data"]
        self.assertTrue(result["updated_at"])
        self.assertEqual(result["file_size"], 8)
        self.assertFalse(result["is_downloading"])
        self.assertEqual(Path(result["file_path"]).read_bytes(), b"12345678")

    async def test_direct_source_validates_legacy_name_even_with_safe_url_filename(self):
        pile_id = await self.create_legacy_pile("../unsafe", source_url="https://example.org/book.txt")
        with patch("aiohttp.ClientSession.get", return_value=RawResponse(b"content")) as transport:
            response = await self.client.post(f"/api/v1/piles/{pile_id}/download-source")
        self.assertEqual(response.status_code, 400, response.text)
        transport.assert_not_called()
        self.assertEqual(list(self.data.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
