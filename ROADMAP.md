# RoXX Roadmap

This roadmap is intentionally practical: prioritize reliability, operational clarity, and security before large feature expansion.

## Completed For 1.0.0

- Stabilized Windows executable distribution with PyInstaller smoke checks in CI.
- Added SHA256 checksum generation for Windows release assets.
- Added clearer operator docs for Windows Service and Linux systemd deployments.
- Added `/livez` and `/readyz` probes for service supervision.
- Added release checklist, release badge, and release asset verification.

## Completed For 1.0.1

- Simplified the Windows release layout to one application executable: `roxx.exe`.
- Routed Windows application modes through `roxx.exe server`, `roxx.exe service ...`, `roxx.exe setup`, and `roxx.exe windows-service ...`.
- Updated release packaging and asset verification so tagged releases publish only `roxx.exe`, the Windows ZIP archive, and `SHA256SUMS.txt`.

## Completed For 1.0.2

- Unified pip-installed commands behind the single `roxx` launcher on Linux and Windows.
- Updated generated and example systemd units to start the server with `roxx server`.
- Documented the systemd migration required when upgrading from the legacy `roxx-server` entry point.

## Short Term

- Reduce the existing Ruff debt in small, low-risk batches.
- Improve logging defaults for service mode on Windows and Linux.
- Add more detailed readiness checks for optional authentication backends without exposing sensitive details.

## Medium Term

- Add signed release artifacts for the Windows executable.
- Add installer packaging for Windows, including service registration and removal.
- Add Linux package formats for Debian/Ubuntu and RHEL-compatible systems.
- Add automated upgrade and rollback documentation.
- Add long-running service tests that exercise restart behavior and `/livez` monitoring.
- Add CI coverage for generated systemd units and Windows service command behavior.
- Split the large FastAPI app into smaller modules by domain to reduce maintenance risk.

## Long Term

- Build high-availability deployment patterns with documented active/passive and load-balanced modes.
- Add first-class observability exports for metrics, health, and audit pipelines.
- Add hardened production profiles for TLS, session security, headers, and rate limits.
- Add release provenance and software bill of materials generation.
- Add automated compatibility tests against supported Windows Server and Linux distribution versions.
- Provide a guided admin setup flow for production bootstrap, certificates, and service installation.
