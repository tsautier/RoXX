# RoXX Roadmap

This roadmap is intentionally practical: prioritize reliability, operational clarity, and security before large feature expansion.

## Short Term

- Stabilize Windows executable distribution with PyInstaller smoke checks in CI.
- Keep release assets reproducible enough to verify with SHA256 checksums.
- Add clearer operator docs for Windows Service and Linux systemd deployments.
- Reduce the existing Ruff debt in small, low-risk batches.
- Add a minimal readiness endpoint that can validate required storage and auth backends without exposing sensitive details.
- Improve logging defaults for service mode on Windows and Linux.

## Medium Term

- Add signed release artifacts for Windows executables.
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
