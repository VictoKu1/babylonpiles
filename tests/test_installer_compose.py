"""Optional offline Compose parser integration; never creates a container."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI is not installed")
class ComposeParserTests(unittest.TestCase):
    def test_generated_configuration_preserves_interpolation_and_command(self):
        version = subprocess.run(["docker", "compose", "version"], capture_output=True)
        if version.returncode:
            self.skipTest("Docker Compose v2 is not installed")
        path = Path(__file__).resolve().parents[1] / "scripts" / "manage_storage.py"
        spec = importlib.util.spec_from_file_location("manage_storage", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "compose.json"
            source.write_text(json.dumps({
                "name": "installer-parser-fixture",
                "services": {
                    "storage": {
                        "image": "fixture-not-started",
                        "environment": {"LITERAL": "keep-$$value-$${value}", "MAX_DRIVES": "0"},
                        "command": ["/bin/sh", "-ec", 'printf "%s" "$$value"'],
                    }
                },
            }))
            base = json.loads(subprocess.check_output([
                "docker", "compose", "-f", str(source), "config", "--format", "json",
            ], text=True))
            compose = module.Compose(root)
            actual = json.loads(compose.execute(base, ["config", "--format", "json"], capture=True))
            self.assertEqual(actual["services"], base["services"])
            self.assertEqual(actual["networks"], base["networks"])
            self.assertEqual(list(root.glob(".babylonpiles-compose-*.json")), [])


if __name__ == "__main__":
    unittest.main()
