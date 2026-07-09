# RoXX Release Checklist

Use this checklist for every tagged release.

## 1. Versioning

- Confirm `pyproject.toml` contains the intended version.
- Confirm `README.md` displays the same version badge.
- Confirm release notes or `CHANGELOG.md` include user-visible changes.
- Confirm the Git working tree is clean before tagging.

## 2. Local Verification

- Run `python -m pytest`.
- Run `python -m build`.
- Run `python -m pip check`.
- Run `python scripts/build_binaries.py` on Windows when validating executables locally.
- Smoke check `dist/bin/roxx.exe --help`.
- Smoke check `dist/bin/roxx-service.exe print-systemd`.
- Smoke check `dist/bin/roxx-server.exe` with `GET /livez`.

## 3. Tagging

- Create an annotated tag: `git tag -a vX.Y.Z -m "RoXX vX.Y.Z"`.
- Push the tag: `git push origin vX.Y.Z`.
- Monitor the `Release` GitHub Actions workflow until completion.

## 4. Release Asset Verification

- Confirm the release contains the Windows zip archive.
- Confirm the release contains raw `.exe` assets for CLI/server/service binaries.
- Confirm `SHA256SUMS.txt` is present.
- Confirm the workflow asset verification step passed.
- Download at least one executable and compare its SHA256 with `SHA256SUMS.txt`.

## 5. Post-Release Smoke Checks

- Install or unpack the Windows archive on a clean Windows host.
- Run `roxx.exe --help`.
- Run `roxx-server.exe` and verify `/livez`.
- Register the Windows service in a test environment and verify start/stop behavior.
- Generate a Linux systemd unit with `roxx-service print-systemd`.

## 6. Rollback

- If a release is broken, mark it as a pre-release or delete the release assets.
- Move users back to the previous known-good tag.
- Create a fix branch from `master`.
- Publish a patch tag after tests, smoke checks, and asset verification pass.
