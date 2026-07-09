# RoXX v1.0.1 Release Notes

**Release Date:** July 10, 2026
**Tag:** v1.0.1

RoXX v1.0.1 is a corrective stable release for the Windows distribution model. It replaces the split Windows executable assets with one application executable, `roxx.exe`, while keeping the tagged release workflow, checksums, and smoke checks.

## Highlights

- Single Windows executable release asset: `roxx.exe`.
- Application modes are routed through one executable:
  - `roxx.exe server`
  - `roxx.exe service ...`
  - `roxx.exe setup`
  - `roxx.exe windows-service ...`
- GitHub Actions release workflow now builds, packages, uploads, and verifies only `roxx.exe`, the Windows ZIP archive, and `SHA256SUMS.txt`.
- Release checklist and roadmap updated for the single-executable Windows layout.
- Stable `1.0.1` version across package metadata, README, app runtime, and UI footer.

## Verification

- Local Python test suite: `122 passed`.
- Local syntax-critical Ruff check: passed.
- Local Python package build: passed.
- Local PyInstaller Windows build: produces only `roxx.exe`.
- Local executable smoke checks: CLI help, systemd rendering through `roxx.exe service`, and server `/livez` plus `/readyz` through `roxx.exe server`.

## Release Assets

- `roxx.exe`
- `roxx-windows-v1.0.1.zip`
- `SHA256SUMS.txt`

## Known Follow-Ups

- Add code signing for the Windows executable.
- Add installer packaging around the single executable, including service registration and removal.
- Add Linux distribution packages and long-running service restart tests.
