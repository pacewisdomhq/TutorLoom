# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.5] - 2026-11-12

### Security

- Only the super admin can now create, rename or delete roles through `/api/roles/`. Before this, any signed-in user could delete the org_admin role and rename the student role to org_admin, making every student an org admin of their own organisation. Org admins on `/api/user-roles/` are now scoped by their org_admin membership in every case, can only assign or remove the org_admin, teacher and student roles, and can no longer change the roles of a super admin.
- If you ran 1.0.4 or earlier, check the `rbac_role` table: a clean install has exactly 4 rows, none with `is_deleted` true, 1 each for superadmin, org_admin, teacher and student. A missing role can be created again on next use, so a deleted row or a 5th row means a role was deleted or renamed. This release does not repair that, and a deleted or renamed role keeps its user assignments, so restore the rows by hand.

### Changed

- Frontend build tooling: Vite 8 and @vitejs/plugin-react 6. Production builds now target Chrome/Edge 111, Firefox 114 and Safari 16.4 or newer.

## [1.0.4] - 2026-11-12

### Security

- Organisation admins and teachers can no longer change, lock out or delete the shared account of a user who belongs to another organisation or is a platform admin, and only platform admins can now list users or read or edit another user's account through `/api/users/`. Teachers can no longer resend invites.
- poetry.lock now pins Django 6.1.3, a Django security release.

### Changed

- poetry.lock now pins celery 5.7.0.

### Fixed

- `pyproject.toml` now asks for celery with its redis extra, as `requirements.txt` does, so `poetry install --only main` installs everything the Redis broker needs.

## [1.0.3] - 2026-11-10

### Security

- Assignment submissions now check that the learner is enrolled in the course, as task and quiz submissions already do. Before this, any learner of the organisation could submit an assignment in a course they were not enrolled in. Reported by Santoshkumarpuppala.
- Updated dompurify to 3.4.17 and fflate (both used by jsPDF), the build tools @babel/core and esbuild, and the poetry.lock entries for urllib3, sqlparse, idna and Pygments, clearing their Dependabot alerts. minimatch stays open: it is used only by the ESLint toolchain, whose latest release still requires minimatch 10.

### Changed

- Dependency updates: Pillow 13, lucide-react 1, @testing-library/jest-dom 7, React 19.3.1, Vite 7.3, Vitest 5.1 and other minor and patch updates.

## [1.0.2] - 2026-11-10

### Security

- Removed the task grade endpoint (`/api/submissions/<id>/grade/`), which let any signed-in user read and grade task submissions. Teachers review task submissions through the organisation-scoped review endpoint.

## [1.0.1] - 2026-11-10

### Security

- Course assignment, task and quiz submissions no longer create or change organisation memberships. Only active learners of the course's organisation can submit; organisation admins, teachers and superusers get 403.

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

[Unreleased]: https://github.com/pacewisdomhq/TutorLoom/compare/v1.0.5...HEAD
[1.0.5]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.5
[1.0.4]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.4
[1.0.3]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.3
[1.0.2]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.2
[1.0.1]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.1
[1.0.0]: https://github.com/pacewisdomhq/TutorLoom/releases/tag/v1.0.0
