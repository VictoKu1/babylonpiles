"""Installer regression tests: fixtures and stubbed host boundaries only."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        helper = ROOT / "scripts" / "manage_storage.py"
        self.assertTrue(helper.exists(), "Storage configuration needs a transactional helper")
        spec = importlib.util.spec_from_file_location("manage_storage", helper)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.base = {
            "name": "fixture",
            "services": {
                "backend": {"environment": {"DATA_DIR": "/data"}},
                "storage": {
                    "environment": {"MAX_DRIVES": "1", "CHUNK_SIZE": "100"},
                    "volumes": [
                        {"type": "bind", "source": str(self.root / "original"), "target": "/mnt/hdd1"},
                        {"type": "volume", "source": "storage_data", "target": "/app/data"},
                    ],
                },
            },
        }

    def test_add_uses_selected_filesystem_and_preserves_other_services(self):
        source = self.root / "external disk"
        source.mkdir()
        state, target = self.mod.add_mapping(self.base, self.mod.empty_state(), source)
        config = self.mod.effective_config(self.base, state)
        self.assertEqual(target, "/mnt/hdd2")
        self.assertEqual(config["services"]["storage"]["volumes"][-1]["source"], str(source / "babylonpiles"))
        self.assertEqual(config["services"]["storage"]["environment"]["MAX_DRIVES"], "2")
        self.assertEqual(config["services"]["backend"], self.base["services"]["backend"])
        self.assertEqual(self.base["services"]["storage"]["environment"]["MAX_DRIVES"], "1")

    def test_noncontiguous_drive_ids_use_highest_id_not_count(self):
        self.base["services"]["storage"]["volumes"].append({"type": "bind", "source": "/disk5", "target": "/mnt/hdd5"})
        state = self.mod.remove_mapping(self.base, self.mod.empty_state(), "hdd1")
        config = self.mod.effective_config(self.base, state)
        self.assertEqual(config["services"]["storage"]["environment"]["MAX_DRIVES"], "5")
        self.assertNotIn("/mnt/hdd1", [v["target"] for v in config["services"]["storage"]["volumes"]])
        self.assertIn("/app/data", [v["target"] for v in config["services"]["storage"]["volumes"]])

    def test_duplicate_directory_is_rejected(self):
        source = self.root / "disk"
        source.mkdir()
        state, _ = self.mod.add_mapping(self.base, self.mod.empty_state(), source)
        with self.assertRaises(ValueError):
            self.mod.add_mapping(self.base, state, source)

    def test_symlink_directory_is_rejected(self):
        source = self.root / "disk"
        source.mkdir()
        link = self.root / "alias"
        link.symlink_to(source, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.mod.add_mapping(self.base, self.mod.empty_state(), link)

    def test_new_base_configuration_remains_authoritative(self):
        source = self.root / "disk"
        source.mkdir()
        state, _ = self.mod.add_mapping(self.base, self.mod.empty_state(), source)
        newer = copy.deepcopy(self.base)
        newer["services"]["backend"]["environment"]["NEW_SETTING"] = "retained"
        self.assertEqual(self.mod.effective_config(newer, state)["services"]["backend"]["environment"]["NEW_SETTING"], "retained")

    def test_validation_failure_does_not_create_storage_or_save_state(self):
        target = self.root / "disk" / "babylonpiles"
        target.parent.mkdir()
        events = []
        def invalid(config):
            events.append("validate")
            raise RuntimeError("invalid compose")
        with self.assertRaisesRegex(RuntimeError, "invalid compose"):
            self.mod.apply_transaction(self.root / "state.json", {"version": 1}, {},
                                       invalid, lambda: target.mkdir(), lambda: events.append("start"),
                                       lambda: None, lambda: None)
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "state.json").exists())
        self.assertEqual(events, ["validate"])

    def test_failed_recreation_restores_exact_previous_state(self):
        state_file = self.root / "state.json"
        original = b'{"version": 1, "custom": "preserve"}\n'
        state_file.write_bytes(original)
        events = []
        def start():
            events.append("recreate")
            raise RuntimeError("service failed")
        with self.assertRaisesRegex(RuntimeError, "service failed"):
            self.mod.apply_transaction(state_file, {"version": 1, "added": []}, {},
                                       lambda config: events.append("validate"),
                                       lambda: events.append("prepare"), start,
                                       lambda: events.append("verify"), lambda: events.append("rollback"))
        self.assertEqual(state_file.read_bytes(), original)
        self.assertEqual(events, ["validate", "prepare", "recreate", "rollback"])

    def test_fstab_detected_type_and_unrelated_entries_are_preserved(self):
        original = "# system\nUUID=root / ext4 defaults 0 1\n"
        updated = self.mod.fstab_entry(original, "disk-uuid", "xfs", "/media/babylonpiles/disk-uuid")
        self.assertTrue(updated.startswith(original))
        self.assertIn("UUID=disk-uuid /media/babylonpiles/disk-uuid xfs defaults,nofail,x-systemd.device-timeout=10s 0 0", updated)
        self.assertEqual(updated, self.mod.fstab_entry(updated, "disk-uuid", "xfs", "/media/babylonpiles/disk-uuid"))

    def test_conflicting_existing_fstab_uuid_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            self.mod.fstab_entry("UUID=disk-uuid /other ext4 defaults 0 2\n", "disk-uuid", "xfs", "/media/babylonpiles/disk-uuid")

    def test_credentials_use_json_and_http_failure_propagates(self):
        from urllib.error import HTTPError
        requests = []
        def fail(request, timeout):
            requests.append(request)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)
        client = self.mod.ApiClient("http://127.0.0.1:8080/api/v1", "token")
        with patch.object(self.mod, "urlopen", fail):
            with self.assertRaisesRegex(RuntimeError, "401"):
                client.request("GET", "/storage/drives")
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer token")
        self.assertNotIn("token", requests[0].full_url)

    def test_remove_refuses_allocated_drive(self):
        with self.assertRaises(ValueError):
            self.mod.require_empty_drive("hdd1", {"chunks": [{"drive_id": "hdd1", "id": "a_chunk_0"}]})
        self.mod.require_empty_drive("hdd2", {"chunks": [{"drive_id": "hdd1", "id": "a_chunk_0"}]})

    def test_readonly_drive_is_not_reported_as_a_usable_addition(self):
        class Client:
            def request(self, *args):
                return {"drives": [{"path": "/mnt/hdd2", "status": "readonly"}]}
        with patch.object(self.mod.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "Storage did not confirm"):
                self.mod.verify_drive(Client(), "/mnt/hdd2", present=True)

    def test_normalized_compose_values_survive_a_second_interpolation_pass(self):
        compose = object.__new__(self.mod.Compose)
        compose.root, compose.command = self.root, ["docker", "compose"]
        config = copy.deepcopy(self.base)
        # This is the escaped representation returned by `compose config`.
        config["services"]["storage"]["environment"]["LITERAL"] = "keep-$$value-$${value}"
        rendered = []
        def capture(command, **kwargs):
            rendered.append(json.loads(Path(command[command.index("-f") + 1]).read_text()))
            return ""
        with patch.object(self.mod, "run", capture):
            compose.execute(config, ["config", "--quiet"])
        self.assertEqual(rendered[0]["services"]["storage"]["environment"]["LITERAL"], "keep-$$value-$${value}")
        self.assertEqual(list(self.root.glob(".babylonpiles-compose-*.json")), [])

    def test_fstab_validation_failure_rolls_back_a_new_mount(self):
        device = object.__new__(self.mod.DeviceMount)
        device.directory = self.root / "new-mount"
        device.device, device.filesystem = "/dev/fixture", "xfs"
        device.was_mounted = device.mounted = device.fstab_changed = False
        device.original_fstab = "# original\n"
        device.updated_fstab = "# proposed\n"
        commands = []
        def external(command, **kwargs):
            commands.append(command)
            if command[:2] == ["findmnt", "--verify"]:
                raise RuntimeError("invalid fstab")
            return ""
        with patch.object(self.mod, "run", external), patch.object(self.mod, "replace_fstab") as replacement:
            with self.assertRaisesRegex(RuntimeError, "invalid fstab"):
                device.prepare()
            device.rollback()
        replacement.assert_not_called()
        self.assertEqual(commands[-1], ["sudo", "umount", str(device.directory)])

    def test_verification_failure_restores_state_before_device_cleanup(self):
        state_file = self.root / "state.json"
        original = b'{"version": 1, "added": [], "removed": []}\n'
        state_file.write_bytes(original)
        def verify():
            raise RuntimeError("drive missing")
        restored = []
        with self.assertRaisesRegex(RuntimeError, "drive missing"):
            self.mod.apply_transaction(state_file, {"version": 1, "added": ["new"]}, {},
                                       lambda config: None, lambda: None, lambda: None,
                                       verify, lambda: restored.append(state_file.read_bytes()))
        self.assertEqual(restored, [original])


class ShellEntryTests(unittest.TestCase):
    def test_interactive_start_does_not_report_success_after_compose_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "babylonpiles.sh"
            script.write_text((ROOT / "babylonpiles.sh").read_text())
            dependency = root / "vendor/EmergencyStorage/emergency_storage.sh"
            dependency.parent.mkdir(parents=True)
            dependency.touch()
            binary = root / "bin"
            binary.mkdir()
            stub = binary / "python3"
            stub.write_text("#!/bin/sh\necho 'fixture: compose failed' >&2\nexit 1\n")
            stub.chmod(0o755)
            result = subprocess.run(["bash", str(script), "interactive"], input="start\nquit\n",
                                    capture_output=True, text=True,
                                    env={**os.environ, "PATH": str(binary) + ":/usr/bin:/bin"})
        self.assertNotIn("Services are ready", result.stdout)
        self.assertIn("Command failed", result.stderr)

    def test_help_does_not_require_docker(self):
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "babylonpiles.sh"
            script.write_text((ROOT / "babylonpiles.sh").read_text())
            result = subprocess.run(["bash", str(script), "help"],
                                    capture_output=True, text=True, env={**os.environ, "PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("add-drive", result.stdout)


if __name__ == "__main__":
    unittest.main()
