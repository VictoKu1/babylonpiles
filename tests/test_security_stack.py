"""Disposable Docker integration checks for the security boundaries.

Run with Python on the Docker host. The default prepares/validates configuration
only; --run starts the four already-built images and always removes its own
project's containers, network, and volumes. No host ports or host mounts are used.
"""

import argparse
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time


PROJECT = "babylonpiles-security-check"
SERVICES = ("backend", "frontend", "storage", "mirrorer")
ORIGIN = "http://localhost:3000"


def docker(arguments, *, input_text=None, check=True, timeout=120):
    result = subprocess.run(
        ["docker", *arguments], input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
    )
    if check and result.returncode:
        raise RuntimeError(f"Docker command failed ({result.returncode}):\n{result.stdout}")
    return result


def make_config(root):
    result = docker(["compose", "-f", str(root / "docker-compose.yml"), "config", "--format", "json"])
    source = json.loads(result.stdout)
    mounts = {
        "backend": {"content": "/mnt/babylonpiles/data", "piles": "/mnt/babylonpiles/piles", "state": "/app/state", "secrets": "/run/babylonpiles/secrets"},
        "frontend": {},
        "storage": {"drive": "/mnt/hdd1", "storage": "/app/data", "secrets": "/run/babylonpiles/secrets"},
        "mirrorer": {"content": "/mnt/babylonpiles/data", "piles": "/mnt/babylonpiles/piles", "secrets": "/run/babylonpiles/secrets"},
    }
    environments = {
        "backend": {
            "STATE_DIR": "/app/state", "DATA_DIR": "/mnt/babylonpiles/data", "PILES_DIR": "/mnt/babylonpiles/piles",
            "STORAGE_URL": "http://storage:8001", "MIRRORER_URL": "http://mirrorer:8002",
            "PUBLIC_ORIGIN": "", "COOKIE_SECURE": "false", "PYTHONDONTWRITEBYTECODE": "1",
            "MAX_UPLOAD_SIZE": "1048576", "MAX_FILE_SIZE": "1048576", "MAX_CATALOG_SIZE": "1048576",
        },
        "frontend": {"BACKEND_PROXY_URL": "http://backend:8080"},
        "storage": {"MAX_DRIVES": "1", "CHUNK_SIZE": "104857600", "MAX_FILE_SIZE": "1048576"},
        "mirrorer": {},
    }
    config = {"name": PROJECT, "services": {}, "volumes": {}, "networks": {"isolated": {"internal": True}}}
    for name in SERVICES:
        original = source["services"][name]
        service = {
            "image": f"babylonpiles-{name}:latest", "pull_policy": "never",
            "restart": "no", "networks": ["isolated"], "environment": environments[name],
            "volumes": [{"type": "volume", "source": volume, "target": target} for volume, target in mounts[name].items()],
        }
        for key in ("read_only", "tmpfs", "healthcheck"):
            if key in original:
                service[key] = copy.deepcopy(original[key])
        if original.get("depends_on"):
            service["depends_on"] = {dependency: {"condition": "service_started"} for dependency in original["depends_on"] if dependency in SERVICES}
        config["services"][name] = service
        for volume in mounts[name]:
            config["volumes"][volume] = {}
    assert config["services"]["backend"].get("read_only") is True
    for service in config["services"].values():
        assert not service.get("ports") and not service.get("build")
        assert all(mount["type"] == "volume" for mount in service["volumes"])
    destination = root / "tmp/security-compose.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return destination


def check_no_existing_project():
    label = f"com.docker.compose.project={PROJECT}"
    for arguments in (["ps", "-aq", "--filter", f"label={label}"],
                      ["volume", "ls", "-q", "--filter", f"label={label}"],
                      ["network", "ls", "-q", "--filter", f"label={label}"]):
        if docker(arguments).stdout.strip():
            raise RuntimeError("The security-check project already has resources; refusing to reuse or remove them")
    # Also reject unlabelled name collisions before Compose could adopt a volume.
    for volume in ("content", "piles", "state", "secrets", "drive", "storage"):
        if docker(["volume", "inspect", f"{PROJECT}_{volume}"], check=False).returncode == 0:
            raise RuntimeError(f"Volume name already exists: {PROJECT}_{volume}")
    if docker(["network", "inspect", f"{PROJECT}_isolated"], check=False).returncode == 0:
        raise RuntimeError("The isolated network name already exists; refusing to reuse it")


def host_main(run):
    root = Path(__file__).resolve().parents[1]
    config = make_config(root)
    compose = ["compose", "-p", PROJECT, "-f", str(config)]
    docker([*compose, "config", "--quiet"])
    print(f"Validated isolated configuration: {config}", flush=True)
    if not run:
        print("No services started. Run with --run only after the images have been rebuilt.")
        return
    check_no_existing_project()
    started = False
    try:
        started = True
        print("Starting disposable security-check project (no ports, host mounts, or external network).", flush=True)
        docker([*compose, "up", "-d", "--no-build", "--pull", "never"], timeout=120)
        source = Path(__file__).read_text(encoding="utf-8")
        deadline = time.monotonic() + 90
        while True:
            copied = docker([*compose, "exec", "-T", "backend", "python", "-c", "import sys; open('/tmp/security_stack_probe.py','w').write(sys.stdin.read())"], input_text=source, check=False)
            if copied.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Backend did not start in time")
            time.sleep(1)
        ready = docker([*compose, "exec", "-T", "backend", "python", "/tmp/security_stack_probe.py", "--probe", "ready"], timeout=100)
        print(ready.stdout, end="", flush=True)
        password = secrets.token_urlsafe(32)
        docker([*compose, "exec", "-T", "backend", "python", "-m", "app.admin", "create", "--username", "stack-admin", "--password-stdin"], input_text=password + "\n")
        first = docker([*compose, "exec", "-T", "backend", "python", "/tmp/security_stack_probe.py", "--probe", "first"], input_text=json.dumps({"password": password}), check=False, timeout=100)
        print(first.stdout, end="", flush=True)
        docker([*compose, "restart", "backend"], timeout=60)
        # tmpfs is recreated on restart; copy the probe again without host mounts.
        docker([*compose, "exec", "-T", "backend", "python", "-c", "import sys; open('/tmp/security_stack_probe.py','w').write(sys.stdin.read())"], input_text=source)
        second = docker([*compose, "exec", "-T", "backend", "python", "/tmp/security_stack_probe.py", "--probe", "restart"], input_text=json.dumps({"password": password}), check=False, timeout=100)
        print(second.stdout, end="", flush=True)
        if first.returncode or second.returncode:
            raise RuntimeError("Full-stack security integration checks failed")
        print("Full-stack security integration checks passed, including backend restart.", flush=True)
    except Exception:
        if started:
            print(docker([*compose, "logs", "--no-color", "--tail", "25", *SERVICES], check=False).stdout, flush=True)
        raise
    finally:
        if started:
            result = docker([*compose, "down", "--volumes", "--remove-orphans", "--timeout", "5"], check=False, timeout=90)
            print(result.stdout, end="", flush=True)
            if result.returncode:
                raise RuntimeError("Could not clean up the disposable security-check project")


def probe_main(stage):
    # This branch runs only inside the disposable backend container.
    # The probe is copied to tmpfs; application packages remain under /app.
    sys.path.insert(0, "/app")
    import asyncio
    import httpx

    def wait_ready():
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=3, trust_env=False) as client:
                    checks = [client.get("http://backend:8080/health"),
                              client.get("http://storage:8001/health"),
                              client.get("http://mirrorer:8002/health"),
                              client.get("http://frontend:3000/", headers={"Host": "localhost:3000"})]
                    if all(response.status_code == 200 for response in checks):
                        return
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise AssertionError("The isolated stack did not become healthy")

    wait_ready()
    if stage == "ready":
        print("PASS: all four disposable services are reachable")
        return
    payload = json.load(sys.stdin)
    failures = []
    state_file = Path("/app/state/security-stack-probe.json")
    client = httpx.Client(base_url="http://frontend:3000", headers={"Host": "localhost:3000"}, timeout=10, trust_env=False)
    anonymous = httpx.Client(base_url="http://frontend:3000", headers={"Host": "localhost:3000"}, timeout=10, trust_env=False)
    content = b"0123456789abcdefghijklmnopqrstuvwxyz"
    file_name = "stack-private.zim"
    key_paths = (Path("/app/state/jwt.key"), Path("/run/babylonpiles/secrets/service.key"))

    def expect(response, status):
        assert response.status_code == status, f"{response.request.method} {response.request.url.path}: expected {status}, got {response.status_code}; {response.text[:160]}"
        return response

    def check(name, operation):
        try:
            operation()
            print(f"PASS: {name}", flush=True)
        except Exception as exc:
            failures.append(name)
            print(f"FAIL: {name}: {exc}", flush=True)

    def login():
        response = expect(client.post("/api/v1/auth/login", json={"username": "stack-admin", "password": payload["password"]}, headers={"Origin": ORIGIN}), 200)
        cookie = response.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
        expect(client.get("/api/v1/auth/me"), 200)

    try:
        if stage == "restart":
            saved = json.loads(state_file.read_text())
            client.headers["Cookie"] = "babylonpiles_session=" + saved["session"]

            def persistent_state():
                assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in key_paths] == saved["keys"]
                expect(client.get("/api/v1/auth/me"), 200)
                listing = expect(client.get("/api/v1/piles/sources-list"), 200).json()
                assert "Stack fixture" in listing
                assert expect(client.get("/api/v1/files/download", params={"path": file_name}), 200).content == content

            check("JWT/service key, account, content, and source catalog persist across backend restart", persistent_state)
            client.headers.pop("Cookie", None)
            check("original password still signs in after restart", login)
        else:
            check("real login through frontend proxy sets a usable protected session cookie", login)

            def denied_private():
                expect(anonymous.get("/api/v1/files"), 401)
                expect(anonymous.get("http://backend:8080/api/v1/files"), 401)
                expect(anonymous.post("/api/v1/auth/login", params={"username": "stack-admin", "password": "not-a-real-password"}), 422)

            check("anonymous private APIs and query-string login are rejected", denied_private)

            def ordinary_user():
                response = expect(client.post("/api/v1/auth/register", json={"username": "stack-user", "password": payload["password"], "role": "admin"}, headers={"Origin": ORIGIN}), 200)
                assert response.json()["data"]["role"] == "user"
                with httpx.Client(base_url="http://frontend:3000", headers={"Host": "localhost:3000"}, timeout=10, trust_env=False) as user:
                    expect(user.post("/api/v1/auth/login", json={"username": "stack-user", "password": payload["password"]}, headers={"Origin": ORIGIN}), 200)
                    expect(user.get("/api/v1/files"), 403)
                    expect(user.post("/api/v1/files/mkdir", data={"folder_name": "user-forbidden"}, headers={"Origin": ORIGIN}), 403)

            check("ordinary accounts cannot claim administrator role or access private management", ordinary_user)

            def origin_controls():
                expect(client.post("/api/v1/files/mkdir", data={"folder_name": "wrong-origin"}, headers={"Origin": "https://attacker.invalid"}), 403)
                expect(client.post("/api/v1/files/mkdir", data={"folder_name": "missing-origin"}), 403)
                expect(client.post("/api/v1/files/mkdir", data={"folder_name": "safe-folder"}, headers={"Origin": ORIGIN}), 200)

            check("cookie mutations require the browser's matching Origin", origin_controls)

            def upload_download():
                expect(client.post("/api/v1/files/upload", files={"file": (file_name, content, "application/octet-stream")}, data={"path": ""}, headers={"Origin": ORIGIN}), 200)
                assert expect(client.get("/api/v1/files/download", params={"path": file_name}), 200).content == content
                assert expect(client.get(f"/api/v1/files/preview/{file_name}"), 200).content == content
                expect(anonymous.get(f"/api/v1/files/preview/{file_name}"), 401)
                expect(client.post("/api/v1/files/upload", files={"file": ("too-large.bin", b"x" * 1048577)}, headers={"Origin": ORIGIN}), 413)
                expect(client.get("/api/v1/files/download", params={"path": "too-large.bin"}), 404)

            check("authenticated upload/download/preview work and oversized uploads leave no file", upload_download)

            def media_range():
                response = client.get(f"/api/v1/files/preview/{file_name}", headers={"Range": "bytes=2-5"})
                if response.status_code == 206:
                    assert response.content == b"2345"
                    assert response.headers.get("content-range") == "bytes 2-5/36"
                else:
                    # The pinned Starlette version ignored Range before this patch;
                    # HTTP permits a complete 200 response. Do not invent partial
                    # transfer support in either the headers or the test report.
                    expect(response, 200)
                    assert response.content == content
                    assert "content-range" not in response.headers
                    assert response.headers.get("accept-ranges", "").lower() != "bytes"
                    print("NOTE: media Range returns the complete file (existing Starlette limitation)", flush=True)

            check("authenticated Range requests return accurate partial or complete content", media_range)

            def public_content():
                url = f"/api/v1/system/hotspot/download/{file_name}"
                expect(anonymous.get(url), 403)
                expect(client.post(f"/api/v1/files/permission/{file_name}", data={"is_public": "true"}, headers={"Origin": ORIGIN}), 200)
                listing = expect(anonymous.get("/api/v1/system/hotspot/public-content"), 200).json()["data"]["files"]
                entry = next(item for item in listing if item["name"] == file_name)
                assert entry["download_url"] == url
                assert expect(anonymous.get(entry["download_url"]), 200).content == content
                expect(client.post(f"/api/v1/files/permission/{file_name}", data={"is_public": "false"}, headers={"Origin": ORIGIN}), 200)
                expect(anonymous.get(url), 403)

            check("public permission changes control the dedicated anonymous download route", public_content)

            def upload_request():
                request = expect(anonymous.post("/api/v1/system/hotspot/request-upload", json={"filename": "requested-file.txt", "editor_name": "Stack guest"}), 200).json()["data"]
                assert request["status"] == "pending"
                approval_url = f"/api/v1/system/hotspot/approve-request/{request['request_id']}"
                expect(anonymous.post(approval_url), 401)
                expect(client.post(approval_url, headers={"Origin": ORIGIN}), 200)
                expect(anonymous.post("/api/v1/files/upload", files={"file": ("requested-file.txt", b"unapproved write")}), 401)
                expect(anonymous.post("/api/v1/system/hotspot/request-upload", json={"filename": "../unsafe", "editor_name": "Stack guest"}), 422)

            check("public JSON upload requests are reviewable without granting anonymous file writes", upload_request)

            def source_catalog():
                assert isinstance(expect(client.get("/api/v1/piles/sources-list"), 200).json(), dict)
                response = expect(client.post("/api/v1/piles/add-source", json={"name": "Stack fixture", "repo_url": "https://example.org/library/", "info_url": None}, headers={"Origin": ORIGIN}), 200)
                assert "Stack fixture" in response.json()
                assert "Stack fixture" in json.loads(Path("/app/state/sources.json").read_text())

            check("source metadata seeds and writes its catalog under persistent state", source_catalog)

            def service_boundaries():
                with httpx.Client(timeout=10, trust_env=False) as direct:
                    for url in ("http://storage:8001/drives", "http://mirrorer:8002/api/v1/runs/42/logs"):
                        expect(direct.get(url), 401)
                        expect(direct.get(url, headers={"X-Service-Key": "wrong"}), 401)
                drives = expect(client.get("/api/v1/storage/drives"), 200).json()["drives"]
                assert drives, "backend storage client did not return the disposable drive"
                allocation = expect(client.post("/api/v1/storage/allocate", params={"file_size": 16, "file_id": "stack_safe"}, headers={"Origin": ORIGIN}), 200).json()
                assert allocation["file_size"] == 16
                log_path = Path("/mnt/babylonpiles/data/mirror_logs/42.log")
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text("stack-integration\n")

                async def mirror_logs():
                    from app.core.mirrorer_client import MirrorerClient
                    mirror = MirrorerClient("http://mirrorer:8002")
                    try:
                        result = await mirror.get_logs(42)
                        assert result["content"] == "stack-integration"
                    finally:
                        await mirror.close()

                asyncio.run(mirror_logs())

            check("actual storage and mirrorer clients authenticate; missing or wrong keys fail", service_boundaries)

            def readonly_application():
                try:
                    Path("/app/security-check-should-not-write").write_text("blocked")
                except OSError as exc:
                    assert exc.errno == errno.EROFS, f"unexpected write error {exc.errno}"
                else:
                    raise AssertionError("backend application filesystem is writable")
                Path("/tmp/security-check-writable").write_text("temporary")

            check("backend application root is read-only and tmpfs remains writable", readonly_application)
            session = client.cookies.get("babylonpiles_session")
            assert session, "No session available for restart checks"
            state_file.write_text(json.dumps({"session": session, "keys": [hashlib.sha256(path.read_bytes()).hexdigest() for path in key_paths]}))
            state_file.chmod(0o600)
    finally:
        client.close()
        anonymous.close()
    if failures:
        raise SystemExit(f"{len(failures)} integration check(s) failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Start, test, and remove the isolated project using already-built images")
    parser.add_argument("--probe", choices=["ready", "first", "restart"], help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.probe:
        probe_main(arguments.probe)
    else:
        host_main(arguments.run)
