#!/usr/bin/env python3
"""Fail closed on common accidental-publication hazards, without dependencies.

This is a bounded safety net, not proof that arbitrary private data is absent.
Ignored untracked files and submodule contents are outside a parent repo's push.
Use --staged for the complete index, --working-tree for tracked and unignored
files, and --pre-push only with Git's standard ref-update tuples on stdin.
"""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
PORTABLE_USERS = {"user", "username", "example", "your-user", "your-username",
                  "your_username", "yourname", "<user>", "<username>",
                  "$user", "${user}", "%username%"}
PATTERNS = [
    ("provider-key", re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{40,255}"
        rb"|(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{35}"
        rb"|sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{32,255}"
        rb"|(?:sk|rk)_live_[A-Za-z0-9]{20,255}|xox[baprs]-[A-Za-z0-9-]{20,255}"
        rb"|SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b")),
    ("private-key", re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
    ("jwt-token", re.compile(rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{12,}\b")),
]
USER_PATH = re.compile(
    rb"(?i)(?:\b[A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+|/(?:home|Users)/+)"
    rb"(?P<user>[^\\/\s\"'`:,;\)\]]+)")
DESKTOP_PATH = re.compile(
    rb"(?i)\b[A-Z]:[\\/]+(?:[^\\/\s\"'`<>]+[\\/]+){1,8}"
    rb"(?:Desktop|Documents|AppData)(?:[\\/]+|\b)")
ROOT_PATH = re.compile(rb"(?<![A-Za-z0-9])/(?:root|run/user/\d+)(?:/|\b)")
LITERAL_CREDENTIAL = re.compile(
    rb"(?i)\b(?:secret_key|service_api_key|jwt_secret|api_key|access_token|client_secret)"
    rb"[\"']?\s*[:=]\s*[\"'](?P<value>[A-Za-z0-9_+/=.-]{24,})[\"']")
ENV_CREDENTIAL = re.compile(
    rb"(?m)^[\t ]*(?:export[\t ]+)?(?:SECRET_KEY|SERVICE_API_KEY|JWT_SECRET|API_KEY|ACCESS_TOKEN|CLIENT_SECRET)"
    rb"[\t ]*=[\t ]*(?P<value>[A-Za-z0-9_+/=.-]{24,})[\t ]*(?:#.*)?\r?$")


class ScanError(Exception):
    """An incomplete check must block publication without leaking Git output."""


def git(*args):
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_NO_LAZY_FETCH"] = "1"
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=environment)
    if result.returncode:
        raise ScanError("Git could not read the required repository objects or index")
    return result.stdout


def nul_records(data):
    if data and not data.endswith(b"\0"):
        raise ScanError("incomplete NUL-delimited Git output")
    return data[:-1].split(b"\0") if data else []


def checked_oid(value):
    if not OID.fullmatch(value):
        raise ScanError("invalid Git object identifier")
    return value


def index_entries():
    entries = []
    for record in nul_records(git("ls-files", "--stage", "-z")):
        metadata, path = record.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise ScanError("resolve the unmerged index before checking publication")
        entries.append((mode, checked_oid(oid), os.fsdecode(path)))
    return entries


def tree_entries(oid):
    for record in nul_records(git("ls-tree", "-r", "-z", "--full-tree", oid)):
        metadata, path = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        if kind == "blob":
            yield mode, checked_oid(blob), os.fsdecode(path)
        elif kind != "commit" or mode != "160000":
            raise ScanError("unexpected Git tree entry")


def destination_commits(remote):
    # A different remote may be private. Only trust the named destination's
    # existing tracking refs; URLs, unusual names and absent context scan all.
    if not remote or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
        return set()
    if remote.encode() not in git("remote").splitlines():
        return set()
    prefix = "refs/remotes/" + remote + "/"
    commits = set()
    for line in git("for-each-ref", "--format=%(objectname) %(refname)", "refs/remotes/").splitlines():
        oid, ref = line.decode("ascii").split()
        if ref.startswith(prefix):
            checked_oid(oid)
            if git("cat-file", "-t", oid).strip() == b"commit":
                commits.add(oid)
    return commits


def private_path(path):
    parts = PurePosixPath(path.replace("\\", "/")).parts
    lowered = [part.lower() for part in parts]
    name = lowered[-1] if lowered else ""
    if (name == ".env" or name.startswith(".env.")) and not name.endswith((".example", ".template", ".sample")):
        return True
    if re.search(r"\.(?:db|sqlite|sqlite3)(?:$|[-.])", name):
        return True
    if re.search(r"(?:^|[._-])(?:secret[-_]?key|service[-_]?api[-_]?key|jwt[-_]?secret|credentials?|cookies?)(?:$|[._-])", name):
        return True
    if name in {".envrc", ".netrc", "_netrc", ".npmrc", ".pypirc", ".authinfo", "authorized_keys", "known_hosts",
                ".permissions.json", ".metadata.json"}:
        return True
    if name.startswith((".jwt.key.", ".service.key.", "cookiejar")):
        return True
    if re.match(r"id_(?:rsa|dsa|ecdsa|ed25519)(?:$|\.)", name) or name.endswith((".pem", ".key", ".p12", ".pfx", ".ppk", ".jks", ".keystore", ".har")):
        return True
    if re.search(r"(?:^|[._-])local(?:[._-](?:json|ya?ml|toml|ini|conf|config|settings|py))$", name):
        return True
    if name.startswith((".babylonpiles-", "local_settings.", "settings.local.")):
        return True
    if re.fullmatch(r"(?:docker-)?compose(?:\.[^.]+)*\.(?:local|override)\.ya?ml", name):
        return True
    if any(part in {".ssh", ".aws", ".azure", ".kube", ".direnv", ".vscode", ".idea", ".secrets", "secrets", "service_secrets",
                    "data", "state", "runtime", "logs", "piles", "backups", "backend_state"} for part in lowered[:-1]):
        return True
    for index, part in enumerate(lowered[:-1]):
        following = lowered[index + 1]
        if part in {".codex", ".agents", ".claude", ".cursor"} and (
            following in {"auth.json", "config.toml", "local.json", "history.jsonl", "mcp.json", "sessions",
                          "log", "logs", "reports", "projects"} or ".local." in following
        ):
            return True
    if path.replace("\\", "/").lower().startswith("storage/info/"):
        return True
    return False


def content_findings(data):
    findings = set()
    if data.startswith(b"SQLite format 3\0"):
        findings.add(("database-content", 1))
    # Most text is ASCII-compatible; also inspect UTF-16 files with a BOM.
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        data = data.decode("utf-16").encode("utf-8")
    for rule, pattern in PATTERNS:
        for match in pattern.finditer(data):
            findings.add((rule, data.count(b"\n", 0, match.start()) + 1))
    for match in USER_PATH.finditer(data):
        if match.group("user").decode("ascii", errors="replace").lower() not in PORTABLE_USERS:
            findings.add(("machine-path", data.count(b"\n", 0, match.start()) + 1))
    for match in DESKTOP_PATH.finditer(data):
        standard = USER_PATH.match(match.group())
        if standard and standard.group("user").decode("ascii", errors="replace").lower() in PORTABLE_USERS:
            continue
        findings.add(("machine-path", data.count(b"\n", 0, match.start()) + 1))
    for match in ROOT_PATH.finditer(data):
        findings.add(("machine-path", data.count(b"\n", 0, match.start()) + 1))
    for match in list(LITERAL_CREDENTIAL.finditer(data)) + list(ENV_CREDENTIAL.finditer(data)):
        value = match.group("value").lower()
        if value in {b"your-secret-key-change-in-production", b"replace-with-a-long-random-secret"}:
            continue
        findings.add(("credential-literal", data.count(b"\n", 0, match.start()) + 1))
    return sorted(findings)


class Scanner:
    def __init__(self):
        self.findings = set()
        self.content_cache = {}
        self.scanned = 0

    def path(self, path, commit=""):
        if private_path(path):
            self.findings.add((path, "private-artifact", 1, commit))

    def content(self, path, data, commit="", oid=None):
        self.path(path, commit)
        if oid is None or oid not in self.content_cache:
            found = content_findings(data)
            if oid is not None:
                self.content_cache[oid] = found
        else:
            found = self.content_cache[oid]
        for rule, line in found:
            self.findings.add((path, rule, line, commit))
        self.scanned += 1

    def blob(self, path, oid, commit=""):
        data = git("cat-file", "blob", oid) if oid not in self.content_cache else b""
        self.content(path, data, commit, oid)

    def staged(self):
        for mode, oid, path in index_entries():
            if mode != "160000":
                self.blob(path, oid)

    def working_tree(self):
        entries = index_entries()
        gitlinks = {path for mode, _, path in entries if mode == "160000"}
        paths = {path for mode, _, path in entries if mode != "160000"}
        paths.update(os.fsdecode(path) for path in nul_records(git("ls-files", "--others", "--exclude-standard", "-z")))
        for path in sorted(paths):
            if any(path == link or path.startswith(link + "/") for link in gitlinks):
                continue
            candidate = Path(path)
            if candidate.is_symlink():
                data = os.fsencode(os.readlink(candidate))
            elif not candidate.exists():
                continue
            elif candidate.is_file():
                data = candidate.read_bytes()
            else:
                raise ScanError("a tracked or unignored path is not a regular file")
            self.content(path, data)

    def pushed(self, input_text, destination=None):
        updates = []
        for line in input_text.splitlines():
            fields = line.split()
            if len(fields) != 4:
                raise ScanError("malformed pre-push input; run --working-tree for a manual check")
            _, local, remote_ref, remote = fields
            checked_oid(local)
            checked_oid(remote)
            # Git may supply arbitrary revision expressions as the local ref.
            # Never execute that field; the independently validated OID is used.
            if not remote_ref.startswith("refs/"):
                raise ScanError("malformed pre-push reference names")
            if set(local) != {"0"}:
                updates.append((local, remote))
        if not input_text.strip():
            raise ScanError("empty pre-push input; run --working-tree or --staged for a manual check")
        old_commits = set()
        for _, old in updates:
            if set(old) != {"0"}:
                peeled = git("rev-parse", "--verify", old + "^{}").decode("ascii").strip()
                if git("cat-file", "-t", peeled).strip() == b"commit":
                    old_commits.add(checked_oid(peeled))
        existing_destination = destination_commits(destination) if updates else set()
        seen_commits = set()
        for local, old in updates:
            tip = local
            kind = git("cat-file", "-t", tip).strip()
            seen_tags = set()
            while kind == b"tag":
                if tip in seen_tags:
                    raise ScanError("cyclic outgoing tag references")
                seen_tags.add(tip)
                tag = git("cat-file", "tag", tip)
                header, separator, message = tag.partition(b"\n\n")
                first_line = header.split(b"\n", 1)[0]
                if not separator or not first_line.startswith(b"object "):
                    raise ScanError("malformed annotated tag object")
                self.content("<tag-message>", message, tip)
                tip = checked_oid(first_line[7:].decode("ascii"))
                kind = git("cat-file", "-t", tip).strip()
            if kind == b"blob":
                self.blob("<tagged-blob>", tip, local)
                continue
            if kind == b"tree":
                for _, oid, path in tree_entries(tip):
                    self.blob(path, oid, local)
                continue
            if kind != b"commit":
                raise ScanError("unsupported outgoing Git object type")
            # Check new branch content even when tracking refs exclude history.
            for _, blob, path in tree_entries(tip):
                if set(old) == {"0"}:
                    self.blob(path, blob, tip)
                else:
                    self.path(path, tip)
            exclusions = old_commits.copy()
            if set(old) == {"0"}:
                exclusions.update(existing_destination)
            args = ["rev-list", tip, *["^" + oid for oid in sorted(exclusions)]]
            for commit_bytes in git(*args).splitlines():
                commit = checked_oid(commit_bytes.decode("ascii"))
                if commit in seen_commits:
                    continue
                seen_commits.add(commit)
                _, separator, message = git("cat-file", "commit", commit).partition(b"\n\n")
                if not separator:
                    raise ScanError("malformed outgoing commit object")
                self.content("<commit-message>", message, commit)
                records = nul_records(git("diff-tree", "--root", "-r", "-m", "--no-commit-id",
                                          "--no-renames", "--no-ext-diff", "--no-textconv",
                                          "--diff-filter=ACMT", "--raw", "-z", commit))
                if len(records) % 2:
                    raise ScanError("unexpected Git diff output")
                for metadata, raw_path in zip(records[::2], records[1::2]):
                    fields = metadata.decode("ascii").split()
                    if len(fields) != 5 or not fields[0].startswith(":"):
                        raise ScanError("unexpected Git diff metadata")
                    if fields[1] != "160000":
                        self.blob(os.fsdecode(raw_path), checked_oid(fields[3]), commit)

    def report(self):
        if self.findings:
            print("Privacy guard blocked publication:", file=sys.stderr)
            for path, rule, line, commit in sorted(self.findings):
                context = " commit=" + commit[:12] if commit else ""
                print(f"  {json.dumps(path, ensure_ascii=True)}:{line}: {rule}{context}", file=sys.stderr)
            print("Remove private files or replace sensitive values, then rerun the check. "
                  "Outgoing history may require removing the value from earlier commits.", file=sys.stderr)
            return 1
        print(f"Privacy guard: checked {self.scanned} file versions; no configured hazards found.")
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--working-tree", action="store_true")
    mode.add_argument("--pre-push", action="store_true")
    parser.add_argument("--remote", help="destination remote name supplied by Git's pre-push hook")
    arguments = parser.parse_args()
    try:
        root = os.fsdecode(git("rev-parse", "--show-toplevel").rstrip(b"\r\n"))
        os.chdir(root)
        scanner = Scanner()
        if arguments.staged:
            scanner.staged()
        elif arguments.working_tree:
            scanner.working_tree()
        else:
            scanner.pushed(sys.stdin.read(), arguments.remote)
        return scanner.report()
    except (ScanError, OSError, ValueError, UnicodeError) as error:
        detail = str(error) if isinstance(error, ScanError) else "could not safely read or parse required input"
        print("Privacy guard could not complete: " + detail + ". Publication blocked.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
