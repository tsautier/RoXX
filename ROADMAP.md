# RoXX Roadmap Delivery Record

This file records what was implemented from the original short-, medium-, and long-term roadmap. Runtime claims are separated from automation that still requires operator infrastructure or secrets.

## Previously Delivered

- `1.0.0`: Windows PyInstaller CI, checksums, probes, service documentation and release verification.
- `1.0.1`: one Windows application executable with all modes routed through `roxx.exe`.
- `1.0.2`: one pip command on every platform and systemd migration to `roxx server`.

## Short-Term Roadmap Implemented

- Applied 80 safe Ruff fixes, reducing findings from 162 to 75 without unsafe rewrites.
- Added rotating `roxx-server.log` service logs with five 10 MiB backups and preserved console/event output.
- Added readiness checks for writable directories, SQLite, and operator-defined TCP dependencies without returning addresses, credentials, exception text, or timing.

## Medium-Term Roadmap Implemented

- Added conditional Authenticode signing and signature verification for the single Windows executable.
- Added Windows install, uninstall, and guarded upgrade scripts around the single `roxx.exe` application.
- Added standalone Linux, Debian and RPM build definitions with hardened systemd lifecycle integration.
- Added automated readiness-based upgrade and rollback scripts plus operator documentation.
- Added repeated server restart and liveness integration tests with log capture.
- Added systemd command tests, Windows service command validation, and multi-platform CI.
- Extracted liveness, readiness and metrics into the `roxx.web.routes.observability` domain router.

## Long-Term Roadmap Implemented

- Added active/passive Keepalived and load-balanced HAProxy deployment patterns.
- Added Prometheus metrics and JSONL audit export pipelines.
- Added explicit production security profiles for TLS-adjacent session and HTTP hardening.
- Added SPDX 2.3 SBOMs and signed GitHub/Sigstore provenance and SBOM attestations.
- Added scheduled compatibility tests for Ubuntu 22.04, Ubuntu 24.04, Windows Server 2022 and Windows Server 2025 GitHub-hosted images.
- Added guided interactive setup fixes and repeatable non-interactive production bootstrap, certificate generation/import, environment creation and optional service installation.

## External Enablement Required

The implementation is present, but these outcomes cannot be truthfully claimed until the corresponding external resources are supplied:

- Authenticode signing requires `ROXX_WINDOWS_CERTIFICATE` and `ROXX_WINDOWS_CERTIFICATE_PASSWORD` repository secrets.
- Real HA validation requires at least two deployed RoXX nodes, a load balancer or virtual IP, shared operational configuration and production certificates.
- Compatibility beyond GitHub-hosted images requires representative Windows domain policies, Linux distributions, HSMs, identity providers, RADIUS clients and network appliances.
- Package publication and attestation run on the next tagged release; ordinary pushes run tests but do not publish release assets.
- Native package installation/removal and real Windows service registration/removal require disposable privileged hosts; local validation covered parsers, rendering, builds, process lifecycle and packaging without changing the workstation service registry.

## Verification Baseline

- `135` local tests pass on Python 3.12 for Windows.
- The local PyInstaller build and executable smoke suite pass with exactly one `roxx.exe`.
- Ruff critical rules, ShellCheck, workflow YAML, PowerShell syntax, wheel/sdist builds, dependency integrity and Git whitespace checks pass.
- Linux-native builds and the four-image compatibility matrix are configured for GitHub Actions and must complete there after push.

## Next Review Horizon

- Finish the remaining 75 Ruff findings in behavior-reviewed batches.
- Add real provider contract tests where test tenants and credentials are available.
- Add package installation tests on disposable native Debian, RHEL-compatible and Windows hosts.
- Review HA state storage before enabling active/active administration without session affinity.
