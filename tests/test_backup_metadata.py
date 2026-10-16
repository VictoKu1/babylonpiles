"""Offline regressions for backup content and metadata consistency."""

import hashlib
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.models.pile import Pile
from app.models.update_log import UpdateLog
from app.modules.updater import ContentUpdater


class BackupMetadataTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        self.piles = self.base / "piles"
        self.piles.mkdir()
        self.backups = self.data / "backups" / "example"
        self.backups.mkdir(parents=True)
        for name, value in (("data_dir", self.data), ("piles_dir", self.piles)):
            setting = patch.object(settings, name, str(value))
            setting.start()
            self.addCleanup(setting.stop)
        self.target = self.piles / "example.txt"
        self.current_bytes = b"current synthetic content"
        self.target.write_bytes(self.current_bytes)
        self.pile = Pile(
            name="example",
            source_type="http",
            file_path=str(self.target),
            file_format="txt",
            file_size=len(self.current_bytes),
            version="20261016_120000",
            checksum=hashlib.sha256(self.current_bytes).hexdigest(),
            last_updated=datetime(2026, 10, 16, 12),
        )
        self.updater = ContentUpdater.__new__(ContentUpdater)

    def make_backup(self, version="20260914_010000", content=b"older synthetic content"):
        backup = self.backups / f"{version}.backup"
        backup.write_bytes(content)
        return backup

    def metadata(self):
        return {
            name: getattr(self.pile, name)
            for name in ("file_path", "file_size", "file_format", "version", "checksum", "last_updated")
        }

    async def test_legacy_backup_restores_checksum_and_selected_version(self):
        backup = self.make_backup()

        self.assertTrue(await self.updater.rollback_pile(self.pile, backup.stem))

        self.assertEqual(self.target.read_bytes(), b"older synthetic content")
        self.assertEqual(self.pile.file_path, str(self.target))
        self.assertEqual(self.pile.file_size, len(b"older synthetic content"))
        self.assertEqual(self.pile.file_format, "txt")
        self.assertEqual(self.pile.checksum, hashlib.sha256(b"older synthetic content").hexdigest())
        self.assertEqual(self.pile.version, "20260914_010000")
        self.assertNotEqual(self.pile.last_updated, datetime(2026, 10, 16, 12))

    async def test_latest_rollback_metadata_describes_the_selected_backup(self):
        older = self.make_backup("20260913_010000", b"first backup")
        latest = self.make_backup("20260914_010000", b"second backup")
        os.utime(older, (1, 1))
        os.utime(latest, (2, 2))

        self.assertTrue(await self.updater.rollback_pile(self.pile))

        self.assertEqual(self.target.read_bytes(), b"second backup")
        self.assertEqual(self.pile.version, "20260914_010000")
        self.assertEqual(self.pile.checksum, hashlib.sha256(b"second backup").hexdigest())

    async def test_created_backup_round_trip_recalculates_metadata(self):
        backup = await self.updater._create_backup(self.pile)
        self.assertIsNotNone(backup)
        self.target.write_bytes(b"updated synthetic content")
        self.pile.checksum = hashlib.sha256(b"updated synthetic content").hexdigest()
        self.pile.version = "newer-version"

        self.assertTrue(await self.updater._restore_backup(self.pile, backup))

        self.assertEqual(self.target.read_bytes(), self.current_bytes)
        self.assertEqual(self.pile.checksum, hashlib.sha256(self.current_bytes).hexdigest())
        self.assertEqual(self.pile.version, Path(backup).stem)
        self.assertEqual(list(self.piles.iterdir()), [self.target])

    async def test_partial_copy_failure_preserves_current_content_and_metadata(self):
        backup = self.make_backup()
        metadata = self.metadata()

        def fail_copy(source, destination):
            Path(destination).write_bytes(b"partial")
            raise OSError("simulated copy failure")

        with patch("app.modules.updater.shutil.copy2", side_effect=fail_copy):
            self.assertFalse(await self.updater._restore_backup(self.pile, str(backup)))

        self.assertEqual(self.target.read_bytes(), self.current_bytes)
        self.assertEqual(self.metadata(), metadata)
        self.assertEqual(list(self.piles.iterdir()), [self.target])

    async def test_checksum_failure_preserves_current_content_and_metadata(self):
        backup = self.make_backup()
        metadata = self.metadata()

        with patch.object(self.updater, "_calculate_checksum", new=AsyncMock(return_value="")):
            self.assertFalse(await self.updater._restore_backup(self.pile, str(backup)))

        self.assertEqual(self.target.read_bytes(), self.current_bytes)
        self.assertEqual(self.metadata(), metadata)
        self.assertEqual(list(self.piles.iterdir()), [self.target])

    async def test_replace_failure_preserves_current_content_and_metadata(self):
        backup = self.make_backup()
        metadata = self.metadata()

        with patch("app.modules.updater.os.replace", side_effect=OSError("simulated replace failure")):
            self.assertFalse(await self.updater._restore_backup(self.pile, str(backup)))

        self.assertEqual(self.target.read_bytes(), self.current_bytes)
        self.assertEqual(self.metadata(), metadata)
        self.assertEqual(list(self.piles.iterdir()), [self.target])

    async def test_failed_update_restores_content_with_matching_metadata(self):
        async def failed_download(pile, update_log, progress_callback):
            self.target.write_bytes(b"failed synthetic download")
            pile.checksum = hashlib.sha256(b"failed synthetic download").hexdigest()
            pile.version = "failed-update"
            return False

        self.updater.sources = {"http": SimpleNamespace(download=failed_download)}

        self.assertFalse(await self.updater.update_pile(self.pile, UpdateLog()))

        self.assertEqual(self.target.read_bytes(), self.current_bytes)
        self.assertEqual(self.pile.checksum, hashlib.sha256(self.current_bytes).hexdigest())
        backup = next(self.backups.glob("*.backup"))
        self.assertEqual(self.pile.version, backup.stem)


if __name__ == "__main__":
    unittest.main()
