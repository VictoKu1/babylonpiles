# Publication privacy checks

Keep local credentials, account state, downloaded content, and machine-specific configuration outside tracked files. Git ignore rules apply to untracked files; they do not remove content already in the index or history.

## Enable the checks

Run from the repository root in each clone:

```sh
git config --local core.hooksPath .githooks
python scripts/check_privacy.py --working-tree
```

The hooks use Python 3. On Unix, preserve their executable bits or run `chmod +x .githooks/pre-commit .githooks/pre-push`. If Python is not on `PATH`, set `privacy.python` with `git config --local` to the absolute path of a trusted interpreter. Local Git settings are not part of a commit.

The pre-commit hook checks the complete staged index. It reads staged bytes even if you have since changed the working copy. The pre-push hook checks outgoing content, including earlier commits that added a value and later removed it. Findings identify paths, rules, and line numbers without printing the secret values. A check that cannot read its required inputs blocks the operation.

For manual review:

```sh
python scripts/check_privacy.py --working-tree
python scripts/check_privacy.py --staged
```

These checks cover common credential formats, private key blocks, local home paths, databases, and private artifact names. They cannot identify every form of personal or confidential text. Review the diff before publishing. Hooks are local safeguards and need setup in each clone; they do not replace repository access controls or a broader secret scan.

## Local files and Docker builds

Keep real environment values in ignored `.env` files or their local variants. Commit only sanitized `.env.example`, `.env.sample`, or `.env.template` files; the guard still checks their contents. Leave sample credential values empty and let the application generate persistent service/signing keys as described in [Security setup](SECURITY_SETUP.md).

The ignore rules exclude keys, cookie/session exports, account databases and SQLite sidecars, runtime metadata, local Compose overrides, and local editor/agent state. Shared source, documentation, and sanitized templates remain trackable. Use `git check-ignore -v -- <path>` to confirm the rule for a proposed local file.

Docker has separate exclusions. The root build context permits only the inputs needed by storage and mirrorer; backend and frontend exclude private artifacts from their own contexts. Git metadata is excluded from image copies. If a Dockerfile needs another source file, update its context rules and verify that private files remain excluded.

The vendored EmergencyStorage checkout is a separate Git repository. A parent commit stores its revision, while Docker uses the files in the current vendor checkout. Inspect vendor changes as well as parent changes before building or updating its revision.

## Existing history

Deleting a secret from the current file or adding an ignore rule does not remove it from earlier commits. If a real credential was published, revoke or rotate it and coordinate history cleanup. Review author/committer identity too; public GitHub noreply addresses avoid adding a personal email to new commits.

Published contributor metadata belongs to existing history. Coordinate any history rewrite with maintainers and collaborators; a local rewrite cannot erase copies already downloaded by others.
