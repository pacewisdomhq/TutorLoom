# Security Policy

## Supported versions

Security fixes are made on the `main` branch and released as a patch to the latest minor version.

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

Report them privately through GitHub's private vulnerability reporting:

1. Open the **[Security tab → Report a vulnerability](../../security/advisories/new)** for this repository.
2. Describe the issue, including:
   - the affected component (backend app, endpoint, or frontend page) and version or commit,
   - steps to reproduce, or a proof of concept,
   - the impact you think it has (for example, data from one organisation being visible to another).

Only the maintainers can see your report.

## What to expect

- We aim to acknowledge your report within **3 working days**.
- We will keep you updated while we investigate and fix the issue.
- Once a fix is released, we will publish a security advisory and credit you, unless you would rather stay anonymous.

Please give us a reasonable amount of time to fix the issue before disclosing it publicly.

## Deployment security

Some defaults in this repository are meant **only for local development**: the fallback `SECRET_KEY`, `DEBUG=True`, `ALLOWED_HOSTS=*`, and Django's `runserver`. Before deploying, follow the checklist in the [Deployment section of the README](README.md#deployment).
