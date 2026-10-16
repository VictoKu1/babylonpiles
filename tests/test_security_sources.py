"""Offline regressions for source import boundaries and bounded downloads."""
import tempfile
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.modules.sources.http import HTTPSource
from app.modules.sources.kiwix import KiwixSource
from app.modules.sources.torrent import TorrentSource


class FakeResponse:
    def __init__(self, chunks=(), data=None, status=200):
        self.chunks = chunks
        self.data = data
        self.status = status
        self.headers = {}
        self.content = self
        self.charset = "utf-8"
        self.stream = io.BytesIO(b"".join(chunks))
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk
    async def json(self):
        return self.data
    async def read(self, size=-1):
        return self.stream.read(size)


class FakeSession:
    closed = False
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.responses.pop(0)
    async def close(self):
        self.closed = True
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        await self.close()


class SourceSecurityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "piles"
        self.root.mkdir()
        self.patches = [patch.object(settings, "piles_dir", str(self.root)),
                        patch.object(settings, "temp_dir", str(self.base / "temp")),
                        patch.object(settings, "max_file_size", 8)]
        for item in self.patches:
            item.start()
    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()
    def pile(self, name="safe", url="https://example.org/book.txt"):
        return SimpleNamespace(name=name, source_url=url, file_path=None,
                               description="", tags=[])

    async def public_transport(self, responses):
        from app.core.public_http import PublicSession
        transport = PublicSession()
        await transport.session.close()
        transport.session = FakeSession(responses)
        return transport

    async def test_http_and_kiwix_validate_legacy_name_before_network(self):
        for cls in (HTTPSource, KiwixSource):
            source = cls()
            source.session = FakeSession([FakeResponse([b"content"])])
            log = SimpleNamespace(error_message=None)
            self.assertFalse(await source.download(self.pile("../unsafe"), log))
            self.assertEqual(source.session.requests, [])
            self.assertIsNotNone(log.error_message)

    async def test_oversized_source_downloads_preserve_target_and_cleanup(self):
        for cls in (HTTPSource, KiwixSource):
            with self.subTest(source=cls.__name__):
                source = cls()
                source.session = FakeSession([FakeResponse([b"12345", b"67890"])])
                target = self.root / "existing.txt"
                target.write_bytes(b"original")
                self.assertFalse(await source._download_file("https://example.org/file", target))
                self.assertEqual(target.read_bytes(), b"original")
                self.assertEqual([p.name for p in self.root.iterdir()], ["existing.txt"])

    async def test_http_url_filename_cannot_be_reserved_or_encoded_alias(self):
        for name in (".permissions.json", "%252e%252e.txt", "C:drive.txt"):
            source = HTTPSource()
            source.session = FakeSession([FakeResponse([b"content"])])
            log = SimpleNamespace(error_message=None)
            self.assertFalse(await source.download(self.pile(url=f"https://example.org/{name}"), log))
            self.assertEqual(source.session.requests, [])

    async def test_source_cannot_follow_a_target_symlink(self):
        outside = self.base / "outside.txt"
        outside.write_bytes(b"original")
        target = self.root / "linked.txt"
        target.symlink_to(outside)
        source = HTTPSource()
        source.session = FakeSession([FakeResponse([b"changed"])])
        self.assertFalse(await source._download_file("https://example.org/file", target))
        self.assertEqual(outside.read_bytes(), b"original")

    async def test_torrent_imports_fail_closed_without_running_downloaders(self):
        source = TorrentSource()
        target = self.root / "existing.txt"
        target.write_bytes(b"original")
        log = SimpleNamespace(error_message=None)
        with patch.object(source, "_download_torrent_file", AsyncMock(return_value=target), create=True) as metadata, \
             patch.object(source, "_download_via_torrent", AsyncMock(return_value=True), create=True) as downloader, \
             patch.object(source, "_find_downloaded_file", return_value=target, create=True):
            self.assertFalse(await source.download(self.pile(), log))
            metadata.assert_not_called()
            downloader.assert_not_called()
        self.assertIn("Torrent imports are disabled", log.error_message)

    async def test_gutenberg_validates_legacy_name_before_metadata_lookup(self):
        from app.modules.sources import gutenberg
        session = FakeSession([FakeResponse(data={"formats": {"text/plain": "https://example.org/book.txt"}}),
                               FakeResponse([b"content"])])
        session_target = "PublicSession" if hasattr(gutenberg, "PublicSession") else "aiohttp.ClientSession"
        with patch(f"app.modules.sources.gutenberg.{session_target}", return_value=session):
            source = gutenberg.GutenbergSource()
            self.assertFalse(await source.download(self.pile("../unsafe", "1342"), SimpleNamespace(error_message=None)))
        self.assertEqual(session.requests, [])

    async def test_gutenberg_rejects_nonnumeric_book_identifiers(self):
        from app.modules.sources import gutenberg
        for value in ("../private", "1342?redirect=http://127.0.0.1", "https://gutenberg.org/ebooks/not-an-id"):
            session = FakeSession([FakeResponse(data={"formats": {"text/plain": "https://example.org/book.txt"}}),
                                   FakeResponse([b"content"])])
            session_target = "PublicSession" if hasattr(gutenberg, "PublicSession") else "aiohttp.ClientSession"
            with patch(f"app.modules.sources.gutenberg.{session_target}", return_value=session):
                source = gutenberg.GutenbergSource()
                self.assertFalse(await source.download(self.pile(url=value), SimpleNamespace(error_message=None)))
            self.assertEqual(session.requests, [])

    async def test_successful_http_downloads_preserve_spaces_and_support_callbacks(self):
        for callback in (lambda *_: None, AsyncMock()):
            source = HTTPSource()
            response = FakeResponse([b"1234", b"5678"])
            response.headers["content-length"] = "8"
            source.session = FakeSession([response])
            pile = self.pile(url="https://example.org/my%20book.txt")
            self.assertTrue(await source.download(pile, SimpleNamespace(error_message=None), callback))
            self.assertEqual(Path(pile.file_path).name, "my book.txt")
            self.assertEqual(Path(pile.file_path).read_bytes(), b"12345678")
            if isinstance(callback, AsyncMock):
                self.assertEqual(callback.await_count, 2)

    async def test_http_and_kiwix_use_real_public_transport_to_block_private_targets(self):
        for cls in (HTTPSource, KiwixSource):
            source = cls()
            source.session = await self.public_transport([])
            log = SimpleNamespace(error_message=None)
            try:
                self.assertFalse(await source.download(self.pile(url="http://127.0.0.1/private.txt"), log))
                self.assertEqual(source.session.session.requests, [])
                self.assertEqual(list(self.root.iterdir()), [])
            finally:
                await source.cleanup()

    async def test_gutenberg_metadata_cannot_redirect_imports_to_private_urls(self):
        from app.modules.sources.gutenberg import GutenbergSource
        metadata = {"formats": {"text/plain": "http://127.0.0.1/private.txt"}}
        transport = await self.public_transport([FakeResponse([json.dumps(metadata).encode()])])
        log = SimpleNamespace(error_message=None)
        with patch("app.modules.sources.gutenberg.PublicSession", return_value=transport):
            self.assertFalse(await GutenbergSource().download(self.pile(url="1342"), log))
        self.assertEqual(len(transport.session.requests), 1)
        self.assertIn("public network addresses", log.error_message)
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_catalog_responses_use_the_smaller_limit(self):
        source = KiwixSource()
        source.session = await self.public_transport([FakeResponse([b'{"data": []}'])])
        try:
            with patch.object(settings, "max_catalog_size", 4):
                self.assertEqual(await source._get_content_list(), [])
        finally:
            await source.cleanup()

    async def test_gutenberg_numeric_and_full_url_ids_work_with_bounded_files(self):
        from app.modules.sources.gutenberg import GutenbergSource
        for identifier in ("1342", "https://www.gutenberg.org/ebooks/1342"):
            metadata = {"formats": {"text/plain": "https://example.org/book.txt"}}
            session = FakeSession([FakeResponse(data=metadata), FakeResponse([b"12345678"])])
            pile = self.pile(url=identifier)
            with patch("app.modules.sources.gutenberg.PublicSession", return_value=session):
                self.assertTrue(await GutenbergSource().download(pile, SimpleNamespace(error_message=None)))
            self.assertEqual(session.requests[0][0], "https://gutendex.com/books/1342")
            self.assertEqual(session.requests[0][1]["max_bytes"], settings.max_catalog_size)
            self.assertEqual(session.requests[1][1]["max_bytes"], 8)
            self.assertEqual(Path(pile.file_path).read_bytes(), b"12345678")

    async def test_gutenberg_oversized_files_preserve_existing_target(self):
        from app.modules.sources.gutenberg import GutenbergSource
        target = self.root / "safe.txt"
        target.write_bytes(b"original")
        session = FakeSession([FakeResponse(data={"formats": {"text/plain": "https://example.org/book.txt"}}),
                               FakeResponse([b"12345", b"67890"])])
        with patch("app.modules.sources.gutenberg.PublicSession", return_value=session):
            self.assertFalse(await GutenbergSource().download(self.pile(url="1342"), SimpleNamespace(error_message=None)))
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual([p.name for p in self.root.iterdir()], ["safe.txt"])

    async def test_gutenberg_search_encodes_query_as_a_single_parameter(self):
        from app.modules.sources.gutenberg import GutenbergSource
        session = FakeSession([FakeResponse(data={"count": 0, "results": []})])
        with patch("app.modules.sources.gutenberg.PublicSession", return_value=session):
            await GutenbergSource().get_available_content("history&languages=secret")
        self.assertEqual(session.requests[0][0], "https://gutendex.com/books?search=history%26languages%3Dsecret")


if __name__ == "__main__":
    unittest.main()
