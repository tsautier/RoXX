# Changelog

All notable changes to RoXX will be documented in this file.

## [1.0.2] - 2026-07-10

### Unified Application Command
- Reduced pip-installed application entry points to the single `roxx` command on Linux and Windows.
- Changed generated and bundled systemd units from the removed `roxx-server` entry point to `roxx server`.
- Updated deployment examples to use `roxx service`, `roxx server`, and `roxx windows-service` subcommands.

### Upgrade Notice
- Existing Linux systemd units must replace `ExecStart=.../roxx-server` with `ExecStart=.../roxx server` after upgrading.
- Operators must run `systemctl daemon-reload` and restart the service after replacing the unit.

### Verification
- Added regression coverage for the single pip command and the unified systemd `ExecStart` command.
- Full test suite passing at release cut: `124 passed`.
- Built wheel contains only the `roxx = roxx.__main__:main` console entry point.
- Local Windows PyInstaller build produced only `roxx.exe`; executable liveness and readiness smoke checks passed.

## [1.0.1] - 2026-07-10

### Windows Release Packaging
- Changed the Windows PyInstaller release layout to publish a single `roxx.exe` application executable.
- Added single-executable routing for `roxx.exe server`, `roxx.exe service ...`, `roxx.exe setup`, and `roxx.exe windows-service ...`.
- Updated GitHub Actions smoke checks, release uploads, ZIP packaging, SHA256 generation, and release asset verification to expect only `roxx.exe`, `roxx-windows-vX.Y.Z.zip`, and `SHA256SUMS.txt`.
- Updated release documentation and checklist to match the single Windows executable model.

### Verification
- Full test suite passing at release cut: `122 passed`.
- Local Windows PyInstaller build completed and produced only `roxx.exe`.
- Local smoke checks passed for CLI help, systemd unit rendering through `roxx.exe service`, and server `/livez` plus `/readyz` through `roxx.exe server`.

## [1.0.0] - 2026-07-09

### Final Release
- Promoted RoXX from beta to the first stable `1.0.0` release.
- Added the Windows PyInstaller release pipeline with tests, smoke checks, ZIP packaging, raw executable uploads, SHA256 checksums, and release asset verification.
- Added `roxx-service.exe` generation and bundled required `fido2` data for standalone Windows server startup.
- Added public `/livez` and `/readyz` probes for process liveness and service readiness checks.
- Added the release workflow badge, release checklist, and project roadmap.
- Aligned package metadata, README version badge, app version, and visible UI footer with `1.0.0`.

### Verification
- Full test suite passing at release cut: `119 passed`.
- Local Windows PyInstaller build completed and produced `roxx.exe`, `roxx-server.exe`, `roxx-service.exe`, `roxx-setup.exe`, and `roxx-windows-service.exe`.
- Local smoke checks passed for CLI help, systemd unit rendering, and `roxx-server.exe` `/livez`.

## [1.0.0-beta10] - 2026-07-09

### Release Infrastructure
- Added production server runtime and service helpers for long-running Linux and Windows deployments.
- Added Windows service wrapper and systemd unit generation.
- Added Windows executable release pipeline, SHA256 checksums, and release asset verification.
- Added release checklist and roadmap.

## [1.0.0-beta9] - 2026-05-23

### Platform Hardening
- Reworked remaining warning-prone test files so pytest no longer reports `PytestReturnNotNoneWarning`.
- Migrated RoXX UTC timestamp generation to timezone-aware datetimes across audit logging, PKI, certificate management, and CLI certificate generation.
- Reduced release noise so the suite now passes with only two third-party `pyasn1` deprecation warnings remaining.

### MFA And Identity
- Completed login OTP handling for both SMS and email factors using session-backed expiring verification codes.
- Added admin email lookup support required for email-based login OTP delivery.
- Removed stale MFA TODO logic and aligned the implementation with the actual login UX.

### Admin Portal
- Normalized legacy `alert()` usage behind the toast notification system for base-template admin pages, improving consistency without breaking existing flows.
- Improved NPS Migration so remote RADIUS server imports require a real shared secret instead of creating unusable backends with placeholder secrets.
- Updated the NPS import preview to collect and validate per-server secrets before import.

### Verification
- Full test suite passing at release cut: `115 passed`.

## [1.0.0-beta8] - 2026-03-24

### Major Features
- Completed the `beta8` feature set around RBAC hardening, GUI/API symmetry, and enterprise MFA integrations.
- Added Duo Security and Okta Verify support for RADIUS backends.
- Introduced API-first management flows for system settings, MFA self-service, observability, and integration tooling.
- Added RBAC documentation and aligned admin-role management with the permission matrix.

### Security
- Reworked session and RBAC enforcement so roles are resolved server-side instead of trusting client cookies.
- Applied authentication and authorization checks consistently across sensitive pages, APIs, and the log WebSocket.
- Tightened access around PKI, SSL/TLS, MFA, health, observability, and management surfaces.

### MFA And Identity
- Finalized SMS MFA self-service, including phone registration and login OTP delivery.
- Completed the self-service MFA experience across TOTP, WebAuthn, client certificates, and SMS.
- Improved Duo and Okta testing and integration points in both backend logic and the admin UI.

### Admin Portal
- Fixed dynamic RADIUS backend forms and added real provider-specific configuration fields.
- Corrected sidebar active-state handling across multiple pages.
- Replaced synthetic dashboard authentication metrics with real audit-log aggregation and filtering.
- Added 24-hour and 1-hour metric filters with hourly and minute granularity.
- Completed PKI and certificate download flows in the GUI.
- Improved NPS Migration so selected clients and backend stubs can be imported explicitly.

### Technical Improvements
- Replaced deprecated FastAPI startup hooks with lifespan handling.
- Updated template rendering to current Starlette/FastAPI conventions.
- Fixed Windows issues around SQLite cleanup and command execution portability.
- Hardened API error handling so business errors remain `400` instead of being masked as `500`.
- Removed tenant support entirely from code, UI, API surface, and docs.

### Verification
- Full test suite passing at release cut: `114 passed`.

## [1.0.0-beta7] - 2026-03-22

### Major Features
- Added the NPS Migration Assistant for importing Microsoft NPS XML exports.
- Added the visual analytics dashboard and advanced live log visibility.
- Introduced AGPLv3 licensing and integrity protections.

### Security
- Added integrity manifests and ownership headers.
- Added rate limiting and CSRF protection groundwork.

### Platform
- Stabilized CI/CD and packaging dependencies.
- Fixed MFA management, template unification, and SAML UI issues.
