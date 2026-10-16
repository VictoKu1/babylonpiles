# Contributing to BabylonPiles

Contributions can include code, documentation, bug reports, and feature requests. Use Docker Compose for local application development.

## Set up a development environment

Install Docker with Compose v2 and Git. The optional Unix operator helper and host-side test scripts also need Python 3.11 or newer; the helper needs Bash. Node.js and backend Python dependencies come from the container images.

Clone the `security` branch with its submodules. The administrator setup below is on this branch and is not yet included in the default `main` branch:

```bash
git clone --branch security --recurse-submodules https://github.com/VictoKu1/babylonpiles.git
cd babylonpiles
```

If you already cloned without submodules, run `git submodule update --init --recursive` before building.

Enable the local publication checks in each clone (Python 3 is required):

```sh
git config --local core.hooksPath .githooks
python scripts/check_privacy.py --working-tree
```

On Unix, make the hooks executable if your checkout did not preserve executable permissions: `chmod +x .githooks/pre-commit .githooks/pre-push`. If Python is not on `PATH`, set the local Git option `privacy.python` to your interpreter's absolute path. That setting stays in `.git/config`; do not copy machine-specific paths into tracked files. See [Publication privacy checks](docs/PRIVACY.md).

Start the services from the repository root:

```bash
docker compose up --build -d --wait
```

You can also start them with `bash ./babylonpiles.sh start`. See [Installation](docs/INSTALL.md) for platform requirements and troubleshooting.

### Create the first administrator

A fresh installation has no default administrator or password. The browser login form expects an account that already exists in the database; it cannot create the first administrator. In a terminal on the Docker host, run:

```bash
docker compose exec backend python -m app.admin create --username admin
```

Enter and confirm a password of at least 12 characters. The terminal hides your password input. If the command reports `Account already exists`, sign in with that administrator's credentials or [reset its password](docs/SECURITY_SETUP.md#reset-an-existing-administrators-password). A password reset does not promote an ordinary user to administrator.

The optional helper manages additional storage with `bash ./babylonpiles.sh add-drive`. Once you use managed storage, use the helper's `compose` command for subsequent Compose operations so its saved mapping is applied, including `bash ./babylonpiles.sh compose exec backend python -m app.admin create --username admin` for account creation. See [Storage](docs/STORAGE.md).

### Open the application

- Frontend: http://localhost:3000. Sign in with username `admin` and the password you chose.
- Backend API: http://localhost:8080.
- Interactive API reference: http://localhost:8080/docs. Administrator endpoints require authentication; see [API](docs/API.md).

The frontend container runs Vite's development server. The Compose stack does not configure a production HTTPS reverse proxy; see [Security setup](docs/SECURITY_SETUP.md) before exposing it beyond local development.

## Make and verify changes

Create a branch for your work:

```bash
git switch -c feature/your-feature-name
```

Frontend source is bind-mounted, so Vite reloads source edits. Rebuild the frontend image and recreate its container after dependency changes:

```bash
docker compose up --build -d --no-deps --renew-anon-volumes frontend
```

The anonymous volume holds `/app/node_modules`; renewing it lets the recreated frontend use the dependencies installed in the rebuilt image.

Backend, storage, and mirrorer source is copied into images. Rebuild and recreate the service you changed, for example:

```bash
docker compose up --build -d backend
```

With helper-managed storage, use `bash ./babylonpiles.sh compose` in place of `docker compose` in these commands.

Follow the [test guide](tests/README.md) to run isolated backend regressions, frontend tests, type checking, linting, and a frontend build. For authentication or service integration changes, also run the disposable stack checks described there. Rebuild the test images after source changes so image-based checks include your edits.

`tests/run_all_tests.py` includes legacy scripts that assume anonymous administration and a directly exposed storage service. Its service probe can skip those scripts, and it does not run frontend checks or the full stack exercise. Do not use its summary as the sole validation for a change.

### Code and test guidelines

- Follow the surrounding Python and TypeScript style. Use type hints and document behavior or constraints that callers need to understand.
- Keep blocking work out of asynchronous request handlers where practical.
- Validate inputs and preserve authentication, authorization, path containment, and request limits when changing endpoints.
- Keep backend regressions in `tests/` and frontend tests in `frontend/tests/`.
- Use temporary files, databases, and mocked network boundaries in isolated tests. Run backend scripts in separate processes because several configure application settings at import time.
- For an API regression, exercise the request and response contract, including the required authentication. Add cleanup for resources your test creates.
- Update the relevant documentation when a command, API contract, or user-visible behavior changes.

The repository does not currently include a GitHub Actions workflow. Record the checks you actually ran in your pull request, including any skips or platform limitations.

## Submit a pull request

Review your diff and stage the files that belong to the change before committing. Push your branch and open a pull request against the intended base branch.

Include:

- The problem and the resulting behavior.
- How you tested it, with the commands and results.
- Any migration steps, compatibility changes, or checks you could not run.

For a bug report, use [GitHub Issues](https://github.com/VictoKu1/babylonpiles/issues) and include reproduction steps, expected and actual behavior, operating system, Docker/Compose versions, and relevant logs. Remove credentials, session cookies, and personal data from logs before posting them. Feature requests should describe the use case and expected behavior.

## Security

Keep credentials and runtime data out of commits. For deployment and administrator recovery, see [Security setup](docs/SECURITY_SETUP.md).

Follow [SECURITY.md](SECURITY.md) to report vulnerabilities privately through GitHub. Keep exploit details out of public issues until disclosure is coordinated with the maintainer.

## Documentation

- [README.md](README.md): overview and quick start.
- [docs/INSTALL.md](docs/INSTALL.md): installation and operator commands.
- [docs/SECURITY_SETUP.md](docs/SECURITY_SETUP.md): administrator setup and deployment security.
- [docs/API.md](docs/API.md): API reference.
- [tests/README.md](tests/README.md): test coverage, commands, and limitations.

By contributing, you agree to license your contribution under the project's [license](LICENSE).
