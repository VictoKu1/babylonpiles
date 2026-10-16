"""System metadata must use supported standard-library APIs."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

STATE = tempfile.TemporaryDirectory()
os.environ["STATE_DIR"] = STATE.name
os.environ["DATABASE_URL"] = f"sqlite:///{STATE.name}/system.db"
os.environ["SECRET_KEY"] = "system-info-test-key-" * 4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core import system


class SystemInfoTests(unittest.IsolatedAsyncioTestCase):
    async def test_system_info_returns_hostname_and_platform_metadata(self):
        with (
            patch("socket.gethostname", return_value="test-server"),
            patch.object(system.psutil, "cpu_count", return_value=4),
            patch.object(system.psutil, "cpu_freq", return_value=None),
            patch.object(system.psutil, "virtual_memory", return_value=SimpleNamespace(total=4096)),
            patch.object(system.psutil, "boot_time", return_value=1000),
            patch.object(system.os, "getpid", return_value=42),
        ):
            info = await system.SystemManager()._get_system_info()

        self.assertNotIn("error", info)
        self.assertEqual(info["hostname"], "test-server")
        self.assertEqual(info["platform"], sys.platform)
        self.assertEqual(info["python_version"], sys.version)
        self.assertEqual(info["cpu_count"], 4)
        self.assertIsNone(info["cpu_freq"])
        self.assertEqual(info["memory_total"], 4096)
        self.assertEqual(info["pid"], 42)


if __name__ == "__main__":
    unittest.main()
