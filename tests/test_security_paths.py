"""Offline regressions for file containment, publication and bounded transfers."""
import asyncio
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from fastapi import HTTPException, UploadFile
from app.api.v1.endpoints import files
from app.core.config import settings
from app.schemas.pile import PileCreate


class FileBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "data"
        self.root.mkdir()
        self.outside = self.base / "data-private"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("private")
        self.patches = [
            patch.object(files, "DATA_ROOT", str(self.root)),
            patch.object(files, "PERMISSIONS_FILE", str(self.root / ".permissions.json")),
            patch.object(files, "METADATA_FILE", str(self.root / ".metadata.json")),
            patch.object(settings, "data_dir", str(self.root)),
            patch.object(settings, "piles_dir", str(self.base / "piles")),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    async def assert_rejected(self, result):
        with self.assertRaises(HTTPException) as error:
            await result
        self.assertEqual(error.exception.status_code, 400)

    async def consume_response(self, response):
        messages = []
        async def receive():
            await asyncio.Event().wait()
        async def send(message):
            messages.append(message)
        await response({"type": "http", "method": "GET", "headers": []}, receive, send)
        return b"".join(message.get("body", b"") for message in messages)

    async def test_every_read_route_rejects_prefix_sibling_and_absolute(self):
        for value in ("../data-private/secret.txt", str(self.outside / "secret.txt")):
            with self.subTest(value=value):
                with self.assertRaises(HTTPException) as error:
                    files.download_file(value)
                self.assertEqual(error.exception.status_code, 400)
                await self.assert_rejected(files.view_file(value))
                await self.assert_rejected(files.preview_file(value))
                await self.assert_rejected(files.get_file_metadata_info(value))

    async def test_upload_validates_combined_filename(self):
        upload = UploadFile(filename="../data-private/new.txt", file=io.BytesIO(b"changed"))
        await self.assert_rejected(files.upload_file(upload, ""))
        self.assertFalse((self.outside / "new.txt").exists())

    async def test_mkdir_validates_folder_name(self):
        await self.assert_rejected(files.create_folder("../data-private/newdir", ""))
        self.assertFalse((self.outside / "newdir").exists())

    async def test_reserved_metadata_files_are_not_addressable(self):
        for value in (".permissions.json", ".metadata.json"):
            (self.root / value).write_text("{}")
            await self.assert_rejected(files.delete_item(value))
            self.assertTrue((self.root / value).exists())

    async def test_root_cannot_be_deleted_or_moved(self):
        await self.assert_rejected(files.delete_item(""))
        await self.assert_rejected(files.move_item("", "moved"))
        self.assertTrue(self.root.is_dir())

    async def test_symlinks_are_not_read_or_listed(self):
        (self.root / "link").symlink_to(self.outside, target_is_directory=True)
        await self.assert_rejected(files.preview_file("link/secret.txt"))
        self.assertEqual(files.list_files("")["items"], [])

    async def test_all_path_endpoints_reject_aliases_windows_forms_and_symlinks(self):
        (self.root / "link").symlink_to(self.outside, target_is_directory=True)
        for value in ("link/secret.txt", "../data-private/secret.txt", "%2e%2e/secret.txt", "%252e%252e/secret.txt", "C:/secret.txt", "C:\\secret.txt", "\\\\server\\share", ".permissions.json", "nested/./file.txt"):
            with self.subTest(value=value):
                for endpoint in (files.view_file, files.preview_file, files.zim_viewer, files.get_file_permission_status, files.toggle_file_permission, files.get_file_metadata_info):
                    await self.assert_rejected(endpoint(value))
                await self.assert_rejected(files.set_file_permission_status(value, True))
                await self.assert_rejected(files.delete_item(value))
                await self.assert_rejected(files.move_item(value, "moved"))

    async def test_upload_cannot_overwrite_a_symlink_target(self):
        (self.root / "link.txt").symlink_to(self.outside / "secret.txt")
        upload = UploadFile(filename="link.txt", file=io.BytesIO(b"changed"))
        await self.assert_rejected(files.upload_file(upload, ""))
        self.assertEqual((self.outside / "secret.txt").read_text(), "private")

    async def test_move_destination_must_be_contained_and_not_reserved(self):
        (self.root / "safe.txt").write_bytes(b"safe")
        for value in ("../data-private/stolen.txt", ".permissions.json", ""):
            await self.assert_rejected(files.move_item("safe.txt", value))
        self.assertTrue((self.root / "safe.txt").exists())

    async def test_nested_uploads_and_spaces_work(self):
        upload = UploadFile(filename="my file.txt", file=io.BytesIO(b"hello"))
        result = await files.upload_file(upload, "nested folder/child")
        self.assertEqual(result["file_path"], "nested folder/child/my file.txt")
        self.assertEqual((self.root / result["file_path"]).read_bytes(), b"hello")

    async def test_oversized_upload_preserves_target_and_cleans_staging(self):
        (self.root / "existing.txt").write_bytes(b"old")
        with patch.object(settings, "max_upload_size", 4):
            upload = UploadFile(filename="existing.txt", file=io.BytesIO(b"too large"))
            with self.assertRaises(HTTPException) as error:
                await files.upload_file(upload, "")
        self.assertEqual(error.exception.status_code, 413)
        self.assertEqual((self.root / "existing.txt").read_bytes(), b"old")
        self.assertEqual([p.name for p in self.root.iterdir()], ["existing.txt"])

    async def test_upload_reads_bounded_chunks_and_accepts_exact_limit(self):
        from app.core.transfers import save_upload
        class BoundedUpload:
            def __init__(self):
                self.content = io.BytesIO(b"abcdefgh")
            async def read(self, size=-1):
                if not 0 < size <= 64 * 1024:
                    raise AssertionError("Upload must use bounded reads")
                return self.content.read(size)
        target = self.root / "eight.txt"
        self.assertEqual(await save_upload(BoundedUpload(), target, 8), 8)
        self.assertEqual(target.read_bytes(), b"abcdefgh")

    async def test_stream_failure_cleans_staging_and_preserves_existing_file(self):
        from app.core.transfers import save_chunks, TransferTooLarge
        target = self.root / "eight.txt"
        target.write_bytes(b"original")
        async def oversized():
            yield b"1234"
            yield b"56789"
        with self.assertRaises(TransferTooLarge):
            await save_chunks(oversized(), target, 8)
        async def broken():
            yield b"1234"
            raise RuntimeError("connection interrupted")
        with self.assertRaises(RuntimeError):
            await save_chunks(broken(), target, 8)
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual([p.name for p in self.root.iterdir()], ["eight.txt"])

    async def test_pile_name_is_a_single_safe_component(self):
        for value in ("../bad", "/tmp/bad", "C:\\bad", ".", "%252e%252e", ".metadata.json"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PileCreate(name=value, display_name="Name", category="test", source_type="local")

    async def test_public_download_uses_exact_permission_and_canonical_path(self):
        from app.api.v1.endpoints import system
        (self.root / "nested folder").mkdir()
        (self.root / "nested folder/my file.txt").write_bytes(b"public")
        (self.root / "nested folder/private.txt").write_bytes(b"private")
        files.set_file_permission("nested folder", True)
        files.set_file_permission("nested folder/my file.txt", True)
        response = await system.download_public_file("nested folder/my file.txt")
        self.assertEqual(await self.consume_response(response), b"public")
        with self.assertRaises(HTTPException) as error:
            await system.download_public_file("nested folder/private.txt")
        self.assertEqual(error.exception.status_code, 403)
        for value in ("nested folder/../nested folder/my file.txt", "%252e%252e/data-private/secret.txt", "nested folder//my file.txt"):
            await self.assert_rejected(system.download_public_file(value))
        listing = await system.get_public_content()
        public_file = next(item for item in listing["data"]["files"] if not item["is_dir"])
        self.assertEqual(public_file["download_url"], "/api/v1/system/hotspot/download/nested%20folder/my%20file.txt")

    async def test_deleted_public_path_does_not_publish_moved_private_file(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public report")
        (self.root / "private.txt").write_bytes(b"private bytes")
        files.set_file_permission("report.txt", True)
        await files.delete_item("report.txt")
        await files.move_item("private.txt", "report.txt")
        self.assertFalse(files.get_file_permission("report.txt"))

    async def test_deleted_public_path_does_not_publish_new_upload(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public report")
        files.set_file_permission("report.txt", True)
        await files.delete_item("report.txt")
        await files.upload_file(UploadFile(filename="report.txt", file=io.BytesIO(b"private bytes")), "")
        self.assertFalse(files.get_file_permission("report.txt"))

    async def test_atomic_import_replacement_requires_explicit_resharing(self):
        from app.core.transfers import save_chunks
        report = self.root / "report.txt"
        report.write_bytes(b"public report")
        files.set_file_permission("report.txt", True)
        async def imported():
            yield b"private imported bytes"
        await save_chunks(imported(), report, 100)
        self.assertFalse(files.get_file_permission("report.txt"))
        files.set_file_permission("report.txt", True)
        self.assertTrue(files.get_file_permission("report.txt"))

    async def test_legacy_boolean_permissions_are_private_until_reshared(self):
        (self.root / "report.txt").write_bytes(b"unidentified bytes")
        (self.root / ".permissions.json").write_text(json.dumps({"report.txt": True}))
        self.assertFalse(files.get_file_permission("report.txt"))
        files.set_file_permission("report.txt", True)
        self.assertTrue(files.get_file_permission("report.txt"))

    async def test_modified_file_identity_invalidates_its_public_grant(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public bytes")
        files.set_file_permission("report.txt", True)
        report.write_bytes(b"private rewritten bytes")
        self.assertFalse(files.get_file_permission("report.txt"))
        with self.assertRaises(HTTPException) as error:
            files.public_file_response("report.txt")
        self.assertEqual(error.exception.status_code, 403)

    async def test_public_descriptor_keeps_authorized_bytes_after_path_replacement(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public bytes")
        files.set_file_permission("report.txt", True)
        response = files.public_file_response("report.txt")
        replacement = self.root / "private.txt"
        replacement.write_bytes(b"private replacement")
        os.replace(replacement, report)
        self.assertEqual(await self.consume_response(response), b"public bytes")
        self.assertTrue(response.source.closed)
        self.assertFalse(files.get_file_permission("report.txt"))

    async def test_replacement_during_open_is_not_authorized_and_descriptor_closes(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public bytes")
        files.set_file_permission("report.txt", True)
        replacement = self.root / "private.txt"
        replacement.write_bytes(b"private replacement")
        real_open = os.open
        descriptors = []
        def swap_then_open(path, flags, *args, **kwargs):
            os.replace(replacement, report)
            descriptor = real_open(path, flags, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(files.os, "open", side_effect=swap_then_open):
            with self.assertRaises(HTTPException) as error:
                files.public_file_response("report.txt")
        self.assertEqual(error.exception.status_code, 403)
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])

    async def test_public_descriptor_closes_on_disconnect(self):
        (self.root / "report.txt").write_bytes(b"public bytes")
        files.set_file_permission("report.txt", True)
        response = files.public_file_response("report.txt")
        async def receive():
            return {"type": "http.disconnect"}
        async def send(message):
            pass
        await response({"type": "http", "method": "GET", "headers": []}, receive, send)
        self.assertTrue(response.source.closed)

    async def test_public_descriptor_rejects_in_place_change_before_reading(self):
        report = self.root / "report.txt"
        report.write_bytes(b"public bytes")
        files.set_file_permission("report.txt", True)
        response = files.public_file_response("report.txt")
        report.write_bytes(b"private changed bytes")
        with self.assertRaises(RuntimeError):
            await response.body_iterator.__anext__()
        self.assertTrue(response.source.closed)

    async def test_zim_viewer_escapes_name_and_encodes_download_query(self):
        name = '<img src=x onerror=alert(1)> & "quoted".zim'
        (self.root / name).write_bytes(b"zim")
        response = await files.zim_viewer(name)
        page = response.body.decode()
        self.assertNotIn('<img src=x', page)
        self.assertIn('&lt;img src=x', page)
        self.assertIn('/api/v1/files/download?path=%3Cimg', page)
        self.assertIn('%26', page)
        self.assertIn('%22quoted%22.zim', page)

    async def test_backup_rejects_tainted_legacy_name_and_stored_path(self):
        from app.modules.updater import ContentUpdater
        updater = ContentUpdater.__new__(ContentUpdater)
        pile = SimpleNamespace(name="../outside", file_path=str(self.outside / "secret.txt"))
        self.assertIsNone(await updater._create_backup(pile))
        pile.name = "safe"
        self.assertIsNone(await updater._create_backup(pile))
        self.assertFalse((self.root / "backups/safe").exists())

    async def test_backup_version_cannot_escape_the_pile_backup_directory(self):
        from app.modules.updater import ContentUpdater
        updater = ContentUpdater.__new__(ContentUpdater)
        backups = self.root / "backups/safe"
        backups.mkdir(parents=True)
        (self.root / "secret.backup").write_bytes(b"secret")
        pile = SimpleNamespace(name="safe", file_path=None, file_format="txt")
        self.assertFalse(await updater.rollback_pile(pile, "../../secret"))
        self.assertFalse(await updater._restore_backup(pile, str(self.root / "secret.backup")))

    async def test_backup_symlink_cannot_be_read_or_overwritten(self):
        from app.modules.updater import ContentUpdater
        updater = ContentUpdater.__new__(ContentUpdater)
        backups = self.root / "backups/safe"
        backups.mkdir(parents=True)
        (backups / "20260913_010000.backup").symlink_to(self.outside / "secret.txt")
        pile = SimpleNamespace(name="safe", file_path=None, file_format="txt")
        self.assertFalse(await updater.rollback_pile(pile, "20260913_010000"))

    async def test_backup_round_trip_preserves_the_original_filename(self):
        from app.modules.updater import ContentUpdater
        updater = ContentUpdater.__new__(ContentUpdater)
        piles = Path(settings.piles_dir)
        piles.mkdir()
        target = piles / "safe.txt"
        target.write_bytes(b"original")
        pile = SimpleNamespace(name="safe", file_path=str(target), file_format="txt")
        backup = await updater._create_backup(pile)
        self.assertIsNotNone(backup)
        target.write_bytes(b"changed")
        self.assertTrue(await updater._restore_backup(pile, backup))
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(pile.file_path, str(target))


if __name__ == "__main__":
    unittest.main()
