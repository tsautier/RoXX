# RoXX v1.0.0 Release Notes

**Release Date:** July 9, 2026
**Tag:** v1.0.0

RoXX v1.0.0 is the first stable release. It promotes the beta line into a production-oriented baseline with service runtime support, Windows executable packaging, release checksums, and release asset verification.

## Highlights

- Stable `1.0.0` version across package metadata, README, app runtime, and UI footer.
- Windows PyInstaller build for raw standalone executables.
- GitHub Actions release workflow for tests, Windows build, smoke checks, artifacts, tagged releases, SHA256 generation, and release asset verification.
- Raw executable upload alongside the Windows ZIP archive.
- Linux systemd helper and Windows service wrapper for long-running deployments.
- Public `/livez` and `/readyz` probes for service supervision.
- Release checklist and roadmap documentation.

## Verification

- Local Python test suite: `119 passed`.
- Local syntax-critical Ruff check: passed.
- Local Python package build: passed.
- Local PyInstaller Windows build: passed.
- Local executable smoke checks: CLI help, systemd rendering, and server `/livez`.

## Known Follow-Ups

- Continue reducing the broader Ruff debt in existing modules.
- Add richer readiness checks for optional identity and RADIUS backends.
- Add signed Windows artifacts and installer packaging.
- Add Linux distribution packages and long-running service restart tests.
