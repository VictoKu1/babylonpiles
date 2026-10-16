# Security Policy

## Branches

| Branch | Current role |
| --- | --- |
| `main` | Default branch; does not yet include the administrator setup described in this checkout |
| `security` | Authentication and security updates; the branch used by the current installation guide |

Include the affected branch and commit in a vulnerability report. Follow [Installation](docs/INSTALL.md) and [Security setup and upgrades](docs/SECURITY_SETUP.md) for the code you deploy; a branch name alone does not establish that a build is free of vulnerabilities.

## Reporting a Vulnerability

If you discover a security vulnerability, **do not open a public issue**.

Instead, please use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/repository-security-advisories/about-private-vulnerability-reporting) feature for this repository.
Include reproduction steps, impact, and affected deployment settings. Remove real credentials, tokens, and private content from examples and logs.

We will respond as soon as possible and coordinate a fix and disclosure.

## Security Best Practices

- Always keep your dependencies up to date.
- Do not share sensitive information (such as credentials or API keys) in public forums or code.
- Review third-party modules for security before use.

## Disclosure Policy

We will acknowledge receipt of your report within 2 business days and strive to resolve all security issues promptly.
