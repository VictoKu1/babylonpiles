"""Isolated service security checks; no running services or network required."""

import asyncio
import importlib.util
import logging
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
TEST_KEY = "isolated-test-service-credential-0123456789abcdef"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


secret_path = ROOT / "backend/app/core/secrets.py"
secret_module = load_module("service_secrets", secret_path) if secret_path.exists() else None
# Existing module import creates logs/metadata and starts a scanner. Suppress those
# external startup effects while testing real manager methods under temporary roots.
with patch.dict(os.environ, {"SERVICE_API_KEY": TEST_KEY}), \
        patch("logging.FileHandler", return_value=logging.NullHandler()), \
        patch("pathlib.Path.mkdir"), patch("threading.Thread.start"):
    storage = load_module("security_test_storage", ROOT / "storage/storage_service.py")
    mirrorer = load_module("security_test_mirrorer", ROOT / "mirrorer/app.py")


def fixture_manager(root):
    manager = storage.StorageManager.__new__(storage.StorageManager)
    manager.drives = {}
    for drive_id in ("hdd1", "hdd2"):
        drive_path = root / drive_id
        drive_path.mkdir()
        manager.drives[drive_id] = storage.DriveInfo(
            id=drive_id, path=str(drive_path), total_space=1024,
            free_space=1024, used_space=0, status="active", health="healthy",
            mount_point=str(drive_path), file_system="test",
        )
    manager.chunks = {}
    manager.migrations = {}
    manager.file_allocations = {}
    manager.chunk_size = 100
    manager.max_file_size = 1000
    manager.save_metadata = lambda: None
    return manager


class SecretTests(unittest.TestCase):
    def load(self, path):
        self.assertIsNotNone(secret_module, "shared secret persistence is not implemented")
        return secret_module.load_secret("ISOLATED_SERVICE_TEST_KEY", path)

    def test_generated_secret_survives_reload_and_concurrent_first_start(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            os.environ.pop("ISOLATED_SERVICE_TEST_KEY", None)
            path = Path(directory) / "private" / "service.key"
            with ThreadPoolExecutor(max_workers=12) as executor:
                values = list(executor.map(lambda _: self.load(path), range(36)))
            self.assertEqual(len(set(values)), 1)
            self.assertGreaterEqual(len(values[0]), 32)
            self.assertEqual(self.load(path), values[0])
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_explicit_weak_or_placeholder_secret_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for key in ("", "short", "your-secret-key-change-in-production", "x" * 32 + "\n"):
                with self.subTest(key=repr(key)), patch.dict(os.environ, {"ISOLATED_SERVICE_TEST_KEY": key}):
                    with self.assertRaises(ValueError):
                        self.load(Path(directory) / "key")

    def test_explicit_secret_does_not_write_a_file(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ISOLATED_SERVICE_TEST_KEY": TEST_KEY}):
            path = Path(directory) / "key"
            self.assertEqual(self.load(path), TEST_KEY)
            self.assertFalse(path.exists())

    def test_existing_symlink_or_nonregular_secret_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            os.environ.pop("ISOLATED_SERVICE_TEST_KEY", None)
            root = Path(directory)
            with self.assertRaises(ValueError):
                self.load(root)
            target = root / "target"
            target.write_text(TEST_KEY)
            link = root / "link"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                self.load(link)

    @unittest.skipIf(os.name == "nt", "POSIX secret modes")
    def test_existing_publicly_readable_secret_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            os.environ.pop("ISOLATED_SERVICE_TEST_KEY", None)
            path = Path(directory) / "key"
            path.write_text(TEST_KEY)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                self.load(path)


class StorageBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = fixture_manager(self.root)

    def test_unsafe_file_ids_cannot_create_directories(self):
        for file_id in ("../escape/nested", "/absolute", "C:\\escape", "a/b", "a\\b", ".", "", "a" * 129):
            with self.subTest(file_id=file_id):
                with self.assertRaises(HTTPException) as caught:
                    self.manager.allocate_file(10, file_id)
                self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(list(self.root.glob("*/chunks")), [])
        self.assertFalse(self.manager.chunks)

    def test_allocation_size_is_bounded_and_duplicates_do_not_overwrite(self):
        for size in (0, -1, True, 1001):
            with self.subTest(size=size), self.assertRaises(HTTPException):
                self.manager.allocate_file(size, "safe_id")
        allocation = self.manager.allocate_file(125, "safe_id")
        self.assertEqual(sum(chunk["size"] for chunk in allocation.chunks), 125)
        with self.assertRaises(HTTPException) as caught:
            self.manager.allocate_file(25, "safe_id")
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.manager.file_allocations["safe_id"].file_size, 125)

    def test_allocation_rejects_traversal_in_configured_root_before_creating_directories(self):
        self.manager.drives["hdd1"].path = str(self.root / "hdd2" / ".." / "hdd1")
        with self.assertRaises(HTTPException) as caught:
            self.manager.allocate_file(10, "safe")
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(list(self.root.glob("*/chunks")), [])
        self.assertFalse(self.manager.file_allocations)

    def test_valid_allocation_can_be_deleted_without_touching_a_sibling_drive(self):
        allocation = self.manager.allocate_file(10, "safe")
        chunk = self.manager.chunks[allocation.chunks[0]["id"]]
        target = Path(chunk.path)
        self.assertEqual(target, self.root / chunk.drive_id / "chunks" / "safe_chunk_0")
        target.write_bytes(b"content")
        sibling = self.root / (chunk.drive_id + "0") / "chunks"
        sibling.mkdir(parents=True)
        unrelated = sibling / "safe_chunk_0"
        unrelated.write_bytes(b"keep")
        with patch.object(storage, "storage_manager", self.manager):
            storage.delete_file("safe")
        self.assertFalse(target.exists())
        self.assertEqual(unrelated.read_bytes(), b"keep")
        self.assertNotIn("safe", self.manager.file_allocations)

    def test_restored_chunk_metadata_prevents_reusing_an_existing_file_id(self):
        self.manager.allocate_file(10, "safe_id")
        # Existing storage versions restore chunks but not file_allocations.
        self.manager.file_allocations.clear()
        with self.assertRaises(HTTPException) as caught:
            self.manager.allocate_file(25, "safe_id")
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.manager.chunks["safe_id_chunk_0"].size, 10)

    def test_symlink_chunk_directory_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.root / "hdd1/chunks").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(HTTPException):
            self.manager.allocate_file(10, "safe")
        self.assertEqual(list(outside.iterdir()), [])

    def test_deletion_rejects_legacy_external_chunk_path(self):
        allocation = self.manager.allocate_file(10, "safe")
        outside = self.root / "unrelated.txt"
        outside.write_text("keep")
        chunk = self.manager.chunks[allocation.chunks[0]["id"]]
        chunk.path = str(outside)
        with patch.object(storage, "storage_manager", self.manager):
            with self.assertRaises(HTTPException):
                storage.delete_file("safe")
        self.assertEqual(outside.read_text(), "keep")
        self.assertIn("safe", self.manager.file_allocations)

    def test_migration_keeps_destination_and_deletes_original(self):
        allocation = self.manager.allocate_file(10, "safe")
        chunk = self.manager.chunks[allocation.chunks[0]["id"]]
        original = Path(chunk.path)
        original.write_bytes(b"content")
        target_drive = "hdd2" if chunk.drive_id == "hdd1" else "hdd1"
        with patch("threading.Thread.start"):
            migration = self.manager.migrate_chunk(chunk.id, target_drive)

        def local_copy(command, **kwargs):
            shutil.copyfile(command[-2], command[-1])
            return SimpleNamespace(returncode=0, stderr="")

        with patch.object(storage.subprocess, "run", side_effect=local_copy):
            self.manager._perform_migration(migration.id)
        self.assertEqual(migration.status, "completed")
        self.assertTrue(Path(chunk.path).exists(), "migration deleted the destination")
        self.assertEqual(Path(chunk.path).read_bytes(), b"content")
        self.assertFalse(original.exists())

    def test_migration_rejects_legacy_external_chunk_path_before_queueing(self):
        allocation = self.manager.allocate_file(10, "safe")
        chunk = self.manager.chunks[allocation.chunks[0]["id"]]
        outside = self.root / "unrelated.txt"
        outside.write_text("keep")
        chunk.path = str(outside)
        with patch("threading.Thread.start"), self.assertRaises(HTTPException):
            self.manager.migrate_chunk(chunk.id, "hdd2")
        self.assertFalse(self.manager.migrations)
        self.assertEqual(outside.read_text(), "keep")


class ServiceHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_storage_operation_requires_authentication(self):
        routes = (
            ("GET", "/drives"), ("POST", "/drives/scan"), ("GET", "/drives/hdd1"),
            ("POST", "/allocate"), ("GET", "/chunks"), ("GET", "/chunks/missing"),
            ("POST", "/migrate"), ("GET", "/migrations"), ("GET", "/migrations/missing"),
            ("GET", "/status"), ("GET", "/files/missing"), ("DELETE", "/files/missing"),
        )
        with tempfile.TemporaryDirectory() as directory:
            manager = fixture_manager(Path(directory))
            manager.scan_drives = lambda: []
            with patch.object(storage, "storage_manager", manager):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=storage.app), base_url="http://storage") as client:
                    for method, path in routes:
                        with self.subTest(method=method, path=path):
                            self.assertEqual((await client.request(method, path)).status_code, 401)

    async def test_storage_migration_accepts_client_json(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = fixture_manager(Path(directory))
            allocation = manager.allocate_file(10, "safe")
            chunk_id = allocation.chunks[0]["id"]
            no_background_threads = SimpleNamespace(Thread=lambda **kwargs: SimpleNamespace(start=lambda: None))
            with patch.object(storage, "storage_manager", manager), patch.object(storage, "threading", no_background_threads):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=storage.app), base_url="http://storage") as client:
                    response = await client.post("/migrate", json={"chunk_id": chunk_id, "target_drive": "hdd2"}, headers={"X-Service-Key": TEST_KEY})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["status"], "queued")

    async def test_storage_requires_service_key_and_accepts_client_json(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SERVICE_API_KEY": TEST_KEY}):
            manager = fixture_manager(Path(directory))
            with patch.object(storage, "storage_manager", manager):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=storage.app), base_url="http://storage") as client:
                    self.assertEqual((await client.get("/health")).status_code, 200)
                    self.assertEqual((await client.get("/drives")).status_code, 401)
                    self.assertEqual((await client.get("/drives", headers={"X-Service-Key": "wrong"})).status_code, 401)
                    headers = {"X-Service-Key": TEST_KEY}
                    response = await client.post("/allocate", json={"file_size": 15, "file_id": "safe"}, headers=headers)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["file_size"], 15)
                    response = await client.post("/allocate", json={"file_size": -1, "file_id": "safe2"}, headers=headers)
                    self.assertEqual(response.status_code, 422)
                    response = await client.post("/allocate", json={"file_size": 1, "file_id": "../escape"}, headers=headers)
                    self.assertEqual(response.status_code, 422)

    async def test_mirrorer_execution_and_logs_require_service_key(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SERVICE_API_KEY": TEST_KEY}), \
                patch.object(mirrorer, "MIRROR_ROOT", Path(directory) / "piles"), \
                patch.object(mirrorer, "MIRROR_LOG_DIR", Path(directory) / "logs"):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mirrorer.app), base_url="http://mirrorer") as client:
                self.assertEqual((await client.get("/health")).status_code, 200)
                self.assertEqual((await client.get("/api/v1/runs/1/logs")).status_code, 401)
                self.assertEqual((await client.post("/api/v1/run", json={})).status_code, 401)
                response = await client.get("/api/v1/runs/1/logs", headers={"X-Service-Key": TEST_KEY})
                self.assertEqual(response.status_code, 404)

    async def test_backend_clients_authenticate_at_service_boundary(self):
        from app.core.storage_client import StorageClient
        from app.core.mirrorer_client import MirrorerClient

        with patch.dict(os.environ, {"SERVICE_API_KEY": TEST_KEY}):
            storage_client = StorageClient("http://storage")
            mirror_client = MirrorerClient("http://mirrorer")
        received = []

        async def respond(request):
            received.append((request.url.path, request.headers.get("X-Service-Key")))
            return httpx.Response(200, json=[] if request.url.path == "/drives" else {"content": "ok"})

        # Swap transport only, retaining headers created by the production clients.
        storage_client.client._transport = httpx.MockTransport(respond)
        mirror_client._client._transport = httpx.MockTransport(respond)
        try:
            await storage_client.get_drives()
            await mirror_client.get_logs(1)
        finally:
            await storage_client.close()
            await mirror_client.close()
        self.assertEqual(received, [("/drives", TEST_KEY), ("/api/v1/runs/1/logs", TEST_KEY)])


if __name__ == "__main__":
    unittest.main()
