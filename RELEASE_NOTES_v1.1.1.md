# RoXX v1.1.1 Release Notes

**Release Date:** September 22, 2026
**Tag:** v1.1.1

## Website and community

- Added a responsive GitHub Pages website at `https://tsautier.github.io/RoXX/` with an architecture overview, capability summary, platform-specific downloads, and links to maintained operator guides.
- The download view reads the latest GitHub Release metadata when available and falls back to the latest-release page when it is not.
- Added structured issue forms for reproducible bugs, feature proposals, and usage questions. Security reports are directed to the repository security policy instead of public issues.

## Upgrade

There is no configuration or database migration from 1.1.0. Existing deployments can use the normal backup, replace, and restart procedure in `docs/OPERATIONS.md`. This release retains one `roxx.exe` on Windows and the same Linux and macOS asset formats.

## Verification

CI runs the Python test suite on Windows, Linux, and macOS. The release workflow builds and smoke-checks platform artifacts, publishes SHA256 checksums and attestations, then downloads release assets to verify their checksums. The website workflow deploys the static `site/` directory to GitHub Pages.
