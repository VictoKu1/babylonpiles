"""Exercise publication checks against real temporary Git repositories."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


GUARD = Path(__file__).resolve().parents[1] / "scripts" / "check_privacy.py"
HOOKS = GUARD.parents[1] / ".githooks"
ZERO = "0" * 40


def fake_provider_key():
    # Assemble synthetic values so this test source itself is safe to publish.
    return "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


class PrivacyGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="privacy-guard-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith("GIT_"):
                self.env.pop(key)
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
        self.git("init", "-q", "-b", "main")

    def git(self, *arguments, input=None):
        result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, *arguments],
                                cwd=self.repo, env=self.env, input=input,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout.decode().strip()

    def write(self, name, content):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content if isinstance(content, bytes) else content.encode())

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "fixture")
        return self.git("rev-parse", "HEAD")

    def scan(self, mode="--staged", stdin="", remote=None):
        arguments = [sys.executable, str(GUARD), mode]
        if remote is not None:
            arguments.extend(["--remote", remote])
        return subprocess.run(arguments, cwd=self.repo,
                              env=self.env, input=stdin, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def assert_blocked(self, result, rule, path=None):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(rule, result.stderr)
        if path:
            self.assertIn(path, result.stderr)
        self.assertNotIn(fake_provider_key(), result.stdout + result.stderr)

    def push_line(self, local, remote=ZERO, name="main"):
        return f"refs/heads/{name} {local} refs/heads/{name} {remote}\n"

    def test_scans_exact_index_bytes_even_when_disk_is_clean(self):
        self.write("space name.txt", fake_provider_key())
        self.git("add", "space name.txt")
        self.write("space name.txt", "safe on disk")
        self.assert_blocked(self.scan(), "provider-key", "space name.txt")

    def test_does_not_scan_unstaged_content_in_staged_mode(self):
        self.write("safe.txt", "safe in index")
        self.git("add", "safe.txt")
        self.write("safe.txt", fake_provider_key())
        self.assertEqual(self.scan().returncode, 0)

    def test_checks_unchanged_tracked_files_even_if_ignored(self):
        self.write("exposed.txt", fake_provider_key())
        self.commit()
        self.write(".gitignore", "exposed.txt\n")
        self.git("add", ".gitignore")
        self.assert_blocked(self.scan(), "provider-key", "exposed.txt")

    def test_working_tree_includes_untracked_but_respects_ignores(self):
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", fake_provider_key())
        self.assertEqual(self.scan("--working-tree").returncode, 0)
        self.write("notes.txt", fake_provider_key())
        self.assert_blocked(self.scan("--working-tree"), "provider-key", "notes.txt")

    def test_env_examples_allow_placeholders_but_not_actual_keys(self):
        self.write(".env.example", "SECRET_KEY=replace-me\n")
        self.write("nested/.env.template", "SERVICE_API_KEY=\n")
        self.git("add", "--all")
        self.assertEqual(self.scan().returncode, 0)
        self.write(".env.example", "TOKEN=" + fake_provider_key())
        self.git("add", ".env.example")
        self.assert_blocked(self.scan(), "provider-key")
        self.write(".env.example", "SERVICE_API_KEY=" + "1a2B3c4D" * 6)
        self.git("add", ".env.example")
        self.assert_blocked(self.scan(), "credential-literal")

    def test_private_artifact_filenames_are_rejected(self):
        for name in [".env.production.local", "db.sqlite3-wal", "secret_key.tmp.123",
                     "service_api_key.deadbeef", "cookies.txt", "id_ed25519",
                     "config.local.json", ".codex/reports/result.json",
                     ".babylonpiles-storage.json", "data/runtime.bin", ".jwt.key.123",
                     ".service.key.leftover", "browser.har", "compose.override.yml",
                     "service_secrets/token", ".permissions.json", ".vscode/settings.json",
                     ".idea/workspace.xml"]:
            with self.subTest(name=name):
                self.write(name, b"\x00fixture")
                self.git("add", "-f", "--", name)
                self.assert_blocked(self.scan(), "private-artifact", name)
                self.git("rm", "-f", "--", name)

    def test_shared_agent_instructions_and_environment_templates_remain_allowed(self):
        for name in [".agents/skills/review/SKILL.md", ".codex/skills/public/SKILL.md",
                     ".env.sample", "backend/.env.production.example"]:
            self.write(name, "Public guidance and placeholders only")
        self.git("add", "--all")
        self.assertEqual(self.scan().returncode, 0)

    def test_sqlite_signature_is_rejected_despite_innocent_filename(self):
        self.write("renamed.bin", b"SQLite format 3\x00" + bytes(80))
        self.git("add", "renamed.bin")
        self.assert_blocked(self.scan(), "database-content")

    def test_private_key_and_jwt_are_rejected_without_echoing_values(self):
        samples = ["-----BEGIN " + "PRIVATE KEY-----\nfixture\n",
                   "ey" + "JhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0." + "abcdefgh12345678"]
        for value, rule in zip(samples, ["private-key", "jwt-token"]):
            self.write("notes.txt", value)
            self.git("add", "notes.txt")
            result = self.scan()
            self.assert_blocked(result, rule)
            self.assertNotIn(value, result.stderr)

    def test_machine_paths_are_rejected_and_portable_examples_allowed(self):
        self.write("docs.md", "/home/" + "user/project\n/Users/" + "example/project\n"
                   + "https://github.com/public-author/project\n")
        self.git("add", "docs.md")
        self.assertEqual(self.scan().returncode, 0)
        for value in ["C:\\" + "Users\\real-person\\AppData\\state",
                      '"C:\\\\' + 'Users\\\\real-person\\\\Desktop\\\\state"',
                      "F:/" + "real-person/Desktop/project",
                      "/home/" + "real-person/project", "/Users/" + "real-person/project"]:
            self.write("docs.md", value)
            self.git("add", "docs.md")
            result = self.scan()
            self.assert_blocked(result, "machine-path")
            self.assertNotIn("real-person", result.stderr)

    def test_no_tests_directory_allowlist(self):
        self.write("tests/test_fixture.py", 'value = "' + fake_provider_key() + '"\n')
        self.git("add", "--all")
        self.assert_blocked(self.scan(), "provider-key")

    def test_deleted_files_and_gitlinks_are_not_read_as_blobs(self):
        self.write("safe.txt", "safe")
        base = self.commit()
        self.git("update-index", "--add", "--cacheinfo", "160000," + base + ",vendor/sample")
        self.git("rm", "safe.txt")
        self.assertEqual(self.scan().returncode, 0)
        self.assertEqual(self.scan("--working-tree").returncode, 0)

    def test_push_detects_secret_added_then_removed_in_history(self):
        self.write("safe.txt", "safe")
        base = self.commit()
        self.write("past leak.txt", fake_provider_key())
        leaked = self.commit()
        self.git("rm", "past leak.txt")
        tip = self.commit()
        result = self.scan("--pre-push", self.push_line(tip, base))
        self.assert_blocked(result, "provider-key", "past leak.txt")
        self.assertIn(leaked[:12], result.stderr)

    def test_new_branch_excludes_already_public_content_but_checks_tip_paths(self):
        self.git("remote", "add", "origin", "https://example.invalid/public.git")
        self.write("historic.txt", fake_provider_key())
        self.commit()
        self.git("rm", "historic.txt")
        self.write("safe.txt", "safe")
        base = self.commit()
        self.git("update-ref", "refs/remotes/origin/main", base)
        self.write("new.txt", "safe")
        tip = self.commit()
        self.assertEqual(self.scan("--pre-push", self.push_line(tip), remote="origin").returncode, 0)
        self.write(".env.production", "placeholder")
        tip = self.commit()
        self.git("update-ref", "refs/remotes/origin/main", tip)
        self.assert_blocked(self.scan("--pre-push", self.push_line(tip), remote="origin"), "private-artifact")

    def test_new_branch_does_not_exclude_other_remote_or_skip_tip_content(self):
        self.git("remote", "add", "origin", "https://example.invalid/public.git")
        self.git("remote", "add", "backup", "https://example.invalid/private.git")
        self.write("safe.txt", "safe")
        base = self.commit()
        self.git("update-ref", "refs/remotes/origin/main", base)
        self.write("private.txt", fake_provider_key())
        self.commit()
        self.git("rm", "private.txt")
        tip = self.commit()
        self.git("update-ref", "refs/remotes/backup/main", tip)
        self.assert_blocked(self.scan("--pre-push", self.push_line(tip), remote="origin"), "provider-key")
        self.git("update-ref", "refs/remotes/origin/main", tip)
        self.assert_blocked(self.scan("--pre-push", self.push_line(tip)), "provider-key")
        self.write("tip.txt", fake_provider_key())
        tip = self.commit()
        self.git("update-ref", "refs/remotes/origin/main", tip)
        self.assert_blocked(self.scan("--pre-push", self.push_line(tip), remote="origin"), "provider-key", "tip.txt")

    def test_push_accepts_revision_expression_local_ref(self):
        self.write("safe.txt", "safe")
        tip = self.commit()
        self.assertEqual(self.scan("--pre-push", f"HEAD~1 {tip} refs/heads/release {ZERO}\n").returncode, 0)

    def test_push_accepts_deletion_only_and_rejects_empty_or_invalid_input(self):
        self.assertEqual(self.scan("--pre-push", f"(delete) {ZERO} refs/heads/old {'a' * 40}\n").returncode, 0)
        for value in ["", "nonsense\n", self.push_line("b" * 40)]:
            with self.subTest(value=value):
                result = self.scan("--pre-push", value)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("privacy", result.stderr.lower())

    def test_push_handles_annotated_tags(self):
        self.write("secret.txt", fake_provider_key())
        self.commit()
        self.git("tag", "-a", "release", "-m", "release")
        tag = self.git("rev-parse", "refs/tags/release")
        self.assert_blocked(self.scan("--pre-push", f"refs/tags/release {tag} refs/tags/release {ZERO}\n"),
                            "provider-key")

    def test_push_scans_commit_and_nested_tag_messages(self):
        self.write("safe.txt", "safe")
        base = self.commit()
        self.git("commit", "--allow-empty", "-q", "-m", fake_provider_key())
        tip = self.git("rev-parse", "HEAD")
        self.assert_blocked(self.scan("--pre-push", self.push_line(tip, base)), "provider-key")
        self.git("tag", "-a", "inner", base, "-m", fake_provider_key())
        self.git("tag", "-a", "outer", "inner", "-m", "safe")
        tag = self.git("rev-parse", "outer")
        self.assert_blocked(self.scan("--pre-push", f"refs/tags/outer {tag} refs/tags/outer {ZERO}\n"),
                            "provider-key")

    def test_push_checks_tags_pointing_directly_to_blob_or_tree(self):
        self.write("secret.txt", fake_provider_key())
        self.commit()
        for target in ["HEAD:secret.txt", "HEAD^{tree}"]:
            oid = self.git("rev-parse", target)
            self.assert_blocked(self.scan("--pre-push", f"refs/tags/raw {oid} refs/tags/raw {ZERO}\n"),
                                "provider-key")

    def test_hook_uses_local_interpreter_and_propagates_failure(self):
        shell = shutil.which("sh")
        if not shell:
            self.skipTest("POSIX shell unavailable")
        self.git("config", "--local", "privacy.python", sys.executable)
        (self.repo / "scripts").mkdir()
        shutil.copyfile(GUARD, self.repo / "scripts" / GUARD.name)
        self.write("notes.txt", fake_provider_key())
        self.git("add", "notes.txt")
        for hook, stdin in [("pre-commit", ""), ("pre-push", "")]:
            result = subprocess.run([shell, str(HOOKS / hook)], cwd=self.repo,
                                    env=self.env, text=True, input=stdin,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if hook == "pre-commit":
                self.assert_blocked(result, "provider-key")
            else:
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("Privacy guard", result.stderr)
        tip = self.commit()
        result = subprocess.run([shell, str(HOOKS / "pre-push"), "origin"], cwd=self.repo,
                                env=self.env, text=True, input=self.push_line(tip),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assert_blocked(result, "provider-key")

    def test_hook_fails_closed_for_bad_configured_interpreter(self):
        shell = shutil.which("sh")
        if not shell:
            self.skipTest("POSIX shell unavailable")
        self.git("config", "--local", "privacy.python", "definitely-missing-python")
        result = subprocess.run([shell, str(HOOKS / "pre-commit")], cwd=self.repo,
                                env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("privacy.python", result.stderr)


if __name__ == "__main__":
    unittest.main()
