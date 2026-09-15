#!/usr/bin/env python3
"""Operator storage configuration. Host side effects are explicit and transactional.

Compose normalizes YAML; this helper never edits it with regular expressions.
Every command reapplies the small storage map to the current base configuration.
"""
import argparse
from contextlib import contextmanager
import copy
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = ".babylonpiles-storage.json"
DRIVE = re.compile(r"^/mnt/hdd([1-9][0-9]*)$")


def run(command, *, capture=True, input=None, cwd=None):
    result = subprocess.run(command, input=input, text=True, capture_output=capture, cwd=cwd)
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed ({result.returncode}): {(result.stderr or '').strip()}")
    return result.stdout or ""


def empty_state():
    return {"version": 1, "added": [], "removed": []}


def real_directory(path, *, must_exist=True):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Storage directories cannot contain symbolic links")
    if must_exist and not path.is_dir():
        raise ValueError(f"Not an existing directory: {path}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    return path


def load_state(path):
    if path.is_symlink():
        raise ValueError("Storage state cannot be a symbolic link")
    state = json.loads(path.read_text()) if path.exists() else empty_state()
    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("Unrecognized storage state")
    if not isinstance(state.get("added"), list) or not isinstance(state.get("removed"), list):
        raise ValueError("Invalid storage state")
    for entry in state["added"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("target"), str)
                or not DRIVE.fullmatch(entry["target"])):
            raise ValueError("Invalid managed drive target")
        source = entry.get("source")
        if not isinstance(source, str) or not Path(source).is_absolute():
            raise ValueError("Managed storage must use absolute host paths")
    if any(not isinstance(target, str) or not DRIVE.fullmatch(target) for target in state["removed"]):
        raise ValueError("Invalid removed drive target")
    return state


def effective_config(base, state):
    config = copy.deepcopy(base)
    storage = config["services"]["storage"]
    volumes = [v for v in storage.get("volumes", []) if v["target"] not in state["removed"]]
    targets = {v["target"] for v in volumes}
    for entry in state["added"]:
        if entry["target"] in targets:
            raise ValueError(f"Managed drive conflicts with base Compose: {entry['target']}")
        targets.add(entry["target"])
        # Refuse a missing host directory at container creation instead of having
        # Docker silently create a root-owned directory on the wrong filesystem.
        volumes.append({"type": "bind", **entry, "bind": {"create_host_path": False}})
    storage["volumes"] = volumes
    storage.setdefault("environment", {})["MAX_DRIVES"] = str(max(
        (int(match.group(1)) for target in targets if (match := DRIVE.fullmatch(target))), default=0))
    return config


def add_mapping(base, state, source, *, must_exist=True):
    directory = real_directory(source, must_exist=must_exist) / "babylonpiles"
    real_directory(directory, must_exist=False)
    current = effective_config(base, state)["services"]["storage"]["volumes"]
    for volume in current:
        if DRIVE.fullmatch(volume["target"]) and volume.get("type") == "bind":
            existing = Path(volume["source"])
            if directory == existing or directory in existing.parents or existing in directory.parents:
                raise ValueError("This storage directory overlaps an existing allocation")
    used = {int(match.group(1)) for v in current if (match := DRIVE.fullmatch(v["target"]))}
    index = 1
    while index in used:
        index += 1
    target = f"/mnt/hdd{index}"
    updated = copy.deepcopy(state)
    updated["removed"] = [item for item in updated["removed"] if item != target]
    # Reusing a removed base target would expose both mappings on merge.
    if any(v["target"] == target for v in base["services"]["storage"].get("volumes", [])):
        updated["removed"].append(target)
    updated["added"].append({"source": str(directory), "target": target})
    return updated, target


def remove_mapping(base, state, drive_id):
    target = f"/mnt/{drive_id}"
    if not DRIVE.fullmatch(target):
        raise ValueError("Use a drive ID such as hdd1")
    current = effective_config(base, state)["services"]["storage"]["volumes"]
    if not any(v["target"] == target for v in current):
        raise ValueError("Drive is not configured")
    updated = copy.deepcopy(state)
    updated["added"] = [entry for entry in updated["added"] if entry["target"] != target]
    if target not in updated["removed"]:
        updated["removed"].append(target)
    return updated


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix=f"{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_transaction(state_file, state, config, validate, prepare, recreate, verify, rollback):
    original = state_file.read_bytes() if state_file.exists() else None
    validate(config)
    try:
        prepare()
        atomic_write(state_file, (json.dumps(state, indent=2) + "\n").encode())
        recreate()
        verify()
    except BaseException as exc:
        if original is None:
            state_file.unlink(missing_ok=True)
        else:
            atomic_write(state_file, original)
        try:
            rollback()
        except Exception as rollback_error:
            raise RuntimeError(f"Operation failed: {exc}; rollback also needs attention: {rollback_error}") from exc
        raise


def fstab_entry(original, uuid, filesystem, mountpoint):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", uuid):
        raise ValueError("Invalid device UUID")
    if filesystem not in {"ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "exfat", "ntfs", "ntfs3"}:
        raise ValueError("Configure this filesystem with the host's mount tools first")
    if not re.fullmatch(r"/media/babylonpiles/[A-Za-z0-9_-]+", mountpoint):
        raise ValueError("Automatic mounts must use the dedicated BabylonPiles mount directory")
    pass_number = 2 if filesystem in {"ext2", "ext3", "ext4"} else 0
    line = f"UUID={uuid} {mountpoint} {filesystem} defaults,nofail,x-systemd.device-timeout=10s 0 {pass_number}"
    for existing in original.splitlines():
        fields = existing.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == f"UUID={uuid}" or (len(fields) > 1 and fields[1] == mountpoint):
            if existing == line:
                return original
            raise ValueError("Device or mountpoint already has an fstab entry; preserve it and mount through the OS")
    return original.rstrip("\n") + "\n# BabylonPiles managed removable storage\n" + line + "\n"


class ApiClient:
    def __init__(self, base_url, token=None):
        self.base_url, self.token = base_url.rstrip("/"), token

    def request(self, method, path, body=None):
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        try:
            with urlopen(Request(self.base_url + path, data=data, headers=headers, method=method), timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"API request failed with HTTP {exc.code}; check administrator access") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Backend API is unavailable or returned invalid JSON") from exc

    @classmethod
    def connect(cls):
        client = cls(os.environ.get("BABYLONPILES_API_URL", "http://127.0.0.1:8080/api/v1"),
                     os.environ.get("BABYLONPILES_TOKEN"))
        if not client.token:
            username = input("Administrator username: ").strip()
            password = getpass.getpass("Password: ")
            client.token = client.request("POST", "/auth/login", {"username": username, "password": password})["data"]["access_token"]
        client.request("GET", "/storage/drives")
        return client


def require_empty_drive(drive_id, response):
    if not isinstance(response, dict) or not isinstance(response.get("chunks"), list):
        raise ValueError("Cannot verify drive allocations")
    if any(chunk.get("drive_id") == drive_id for chunk in response["chunks"]):
        raise ValueError("Drive still has allocated chunks; migrate or delete its allocations before removal")


class Compose:
    def __init__(self, root):
        self.root = root
        self.command = ["docker", "compose"]
        try:
            run([*self.command, "version"])
        except (OSError, RuntimeError) as exc:
            raise RuntimeError("Install the Docker Compose v2 plugin (docker compose)") from exc

    def base(self):
        return json.loads(run([*self.command, "--project-directory", str(self.root), "config", "--format", "json"], cwd=self.root))

    def execute(self, config, args, *, capture=False):
        fd, temporary = tempfile.mkstemp(prefix=".babylonpiles-compose-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w") as output:
                # Compose's normalized JSON already escapes literal dollar signs
                # for reparsing. Preserve it, including shell commands, verbatim.
                json.dump(config, output)
            return run([*self.command, "--project-directory", str(self.root), "-p", config["name"],
                        "-f", temporary, *args], capture=capture, cwd=self.root)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def validate(self, config):
        self.execute(config, ["config", "--quiet"], capture=True)

    def recreate(self, config):
        self.execute(config, ["up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "60", "storage"])


def verify_drive(client, target, *, present):
    for attempt in range(15):
        try:
            client.request("POST", "/storage/drives/scan")
            response = client.request("GET", "/storage/drives")
            matches = [drive for drive in response["drives"] if drive.get("path") == target]
            if (present and any(drive.get("status") == "active" for drive in matches)) or (not present and not matches):
                return
        except (RuntimeError, KeyError, TypeError):
            pass
        time.sleep(1)
    raise RuntimeError("Storage did not confirm the expected drive configuration")


def replace_fstab(original, updated):
    """Compare-and-replace the privileged file; no shell interpolation."""
    program = """import hashlib,json,os,pathlib,sys,tempfile
p=pathlib.Path('/etc/fstab'); request=json.load(sys.stdin); current=p.read_bytes()
if hashlib.sha256(current).hexdigest()!=request['expected']: raise SystemExit('fstab changed; refusing overwrite')
info=p.stat(); fd,name=tempfile.mkstemp(prefix='.fstab-babylonpiles-',dir='/etc')
try:
 with os.fdopen(fd,'wb') as output:
  output.write(request['content'].encode()); output.flush(); os.fsync(output.fileno())
 os.chmod(name,info.st_mode & 0o777); os.chown(name,info.st_uid,info.st_gid); os.replace(name,p)
finally:
 if os.path.exists(name): os.unlink(name)
"""
    run(["sudo", "python3", "-c", program], input=json.dumps({"expected": hashlib.sha256(original.encode()).hexdigest(), "content": updated}))


class DeviceMount:
    def __init__(self, device, *, persistent=False):
        device = Path(device).resolve(strict=True)
        if not stat.S_ISBLK(device.stat().st_mode):
            raise ValueError("Expected a block device")
        self.device = str(device)
        self.uuid = run(["sudo", "blkid", "-s", "UUID", "-o", "value", self.device]).strip()
        self.filesystem = run(["sudo", "blkid", "-s", "TYPE", "-o", "value", self.device]).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.uuid):
            raise ValueError("Device must have a stable filesystem UUID")
        existing = subprocess.run(["findmnt", "-rn", "-S", self.device, "-o", "TARGET"], capture_output=True, text=True)
        targets = existing.stdout.splitlines()
        if len(targets) > 1:
            raise ValueError("Device has multiple mounts; select its mounted directory")
        self.directory = real_directory(targets[0]) if targets else Path("/media/babylonpiles") / self.uuid
        self.was_mounted = bool(targets)
        self.mounted = self.fstab_changed = False
        self.original_fstab = Path("/etc/fstab").read_text() if persistent else None
        self.updated_fstab = fstab_entry(self.original_fstab, self.uuid, self.filesystem, str(self.directory)) if persistent else None

    def prepare(self):
        real_directory(self.directory, must_exist=False)
        if not self.was_mounted:
            run(["sudo", "mkdir", "-p", str(self.directory)])
            run(["sudo", "mount", "-t", self.filesystem, self.device, str(self.directory)])
            self.mounted = True
        if self.updated_fstab is not None and self.updated_fstab != self.original_fstab:
            # Validate a complete candidate before replacing the real fstab.
            with tempfile.NamedTemporaryFile(mode="w", suffix=".fstab") as candidate:
                candidate.write(self.updated_fstab)
                candidate.flush()
                run(["findmnt", "--verify", "--tab-file", candidate.name])
            replace_fstab(self.original_fstab, self.updated_fstab)
            self.fstab_changed = True

    def rollback(self):
        if self.fstab_changed:
            replace_fstab(self.updated_fstab, self.original_fstab)
        if self.mounted:
            run(["sudo", "umount", str(self.directory)])


def prepare_directory(directory):
    real_directory(directory, must_exist=False)
    if not directory.exists():
        # Only the new dedicated child gets permissions; never recurse over a disk.
        try:
            directory.mkdir(mode=0o750)
        except PermissionError:
            run(["sudo", "install", "-d", "-m", "0750", "-o", str(os.getuid()), "-g", str(os.getgid()), str(directory)])


def modify_storage(compose, base, state_file, action, location, persistent=False):
    client = ApiClient.connect()
    state = load_state(state_file)
    previous = effective_config(base, state)
    device = None
    if action == "add":
        selected = Path(location).expanduser()
        if selected.exists() and stat.S_ISBLK(selected.stat().st_mode):
            device = DeviceMount(selected, persistent=persistent)
            selected = device.directory
        elif persistent:
            raise ValueError("auto-mount requires a block device; use add-drive for existing directories")
        updated, target = add_mapping(base, state, selected, must_exist=device is None or device.was_mounted)
        directory = Path(updated["added"][-1]["source"])
        print(f"Add {directory} as {target}. Existing files and ownership are preserved.")
    else:
        require_empty_drive(location, client.request("GET", "/storage/chunks"))
        updated = remove_mapping(base, state, location)
        target = f"/mnt/{location}"
        print(f"Detach {target} from BabylonPiles. Host mounts and files will be preserved.")
    candidate = effective_config(base, updated)
    compose.validate(candidate)
    if input("Apply this configuration? [y/N]: ").strip().lower() != "y":
        print("Cancelled.")
        return
    def prepare():
        if device:
            device.prepare()
        if action == "add":
            prepare_directory(directory)
        else:
            require_empty_drive(location, client.request("GET", "/storage/chunks"))
    def rollback():
        compose.recreate(previous)
        if device:
            device.rollback()
    apply_transaction(state_file, updated, candidate, compose.validate, prepare,
                      lambda: compose.recreate(candidate),
                      lambda: verify_drive(client, target, present=action == "add"), rollback)
    print("Storage configuration applied and verified.")


@contextmanager
def configuration_lock(root):
    import fcntl
    with (root / ".babylonpiles-storage.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another storage/Compose operation is in progress") from exc
        yield


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("add", "remove"):
        command = commands.add_parser(action)
        command.add_argument("location")
        if action == "add":
            command.add_argument("--persistent", action="store_true")
    commands.add_parser("scan")
    commands.add_parser("status")
    command = commands.add_parser("compose")
    command.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        with configuration_lock(ROOT):
            if args.action in {"scan", "status"}:
                client = ApiClient.connect()
                if args.action == "scan":
                    client.request("POST", "/storage/drives/scan")
                print(json.dumps(client.request("GET", "/storage/drives"), indent=2))
                return
            compose = Compose(ROOT)
            base = compose.base()
            state_file = ROOT / STATE_NAME
            if args.action == "compose":
                if not args.arguments:
                    raise ValueError("Specify a Compose command")
                compose.execute(effective_config(base, load_state(state_file)), args.arguments)
            else:
                modify_storage(compose, base, state_file, args.action, args.location, getattr(args, "persistent", False))
    except (OSError, ValueError, RuntimeError, KeyError, EOFError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
