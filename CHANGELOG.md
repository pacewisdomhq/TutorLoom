# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

First stable release of TutorLoom, the open-source learning management system.

### Added

- First open-source release of the 🆓 Community edition: login and invites, Institute Admin portal, course builder, Trainer and Student portals, progress tracking, and points & levels.
- Chapters between levels and items in the course builder.
- Course certificates: generated automatically on completion, with PDF export.
- Learner mobile app for Android and iOS (`student_mobile_app/`): courses, roadmap, lessons, tasks, quizzes, progress, certificates, and switching between organisations, with setup and device requirements documented.
- A footer across the web app and the mobile app.
- Apache License 2.0 (`LICENSE`), `NOTICE`, and SPDX license headers on source files.
- Community files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, issue and pull request templates, `CODEOWNERS`, and Dependabot configuration.
- GitHub Actions CI: backend tests, frontend tests and build, lint, and a license-header check.
- Docker Compose setup for running the full stack locally.

### Changed

- Rebranded to TutorLoom: new SVG logo, theme colours, mobile app icon and name, and a redesigned README.
- Admin dashboard analytics routes updated, with tighter permissions.
- Batch analytics include task and quiz scores, scope the batch average to enrolled students, and no longer run one query per student.
- Students can be added to a batch according to the batch's lifecycle.
- The mobile app's progress and status colours use the primary brand colour.
- The coding module is removed from the mobile app.
- Python 3.14 is supported alongside 3.13, and the backend Docker image now uses `python:3.14-slim`. The frontend Docker image uses `node:26-alpine`.
- Dependency updates: Redis client 8, django-redis 7, Pillow 12, drf-spectacular 0.30, django-environ 0.14, Flower 2.2, and a group of Python minor and patch updates; on the frontend, Vitest 5, ESLint 10, jsdom 30, and 16 npm minor and patch updates; `actions/setup-node` 7.1 in CI. `requirements.txt` now allows the same versions as `pyproject.toml`.
- The React Compiler rules that `eslint-plugin-react-hooks` 7.1 added to its recommended set report as warnings for now; existing code trips them in 22 places.
- TypeScript stays on 5.9: `typescript-eslint` does not support TypeScript 7 yet.

### Fixed

- A node is completed only once its task and quiz requirements are met.
- Quiz submissions are graded against the quiz's passing percentage.
- Completion points are awarded once per student and node.
- Switching organisations in the mobile app.
- The product name is spelled TutorLoom everywhere; the mobile app id is `com.tutorloom.student`.

### Security

- Rate limiting on the login, password reset, and invite endpoints.

[Unreleased]: https://github.com/pacewisdomhq/TutorLoom/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.0
