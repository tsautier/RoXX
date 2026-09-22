# RoXX v1.1.0 Release Notes

**Release Date:** September 22, 2026
**Tag:** v1.1.0

RoXX 1.1.0 packages the completed production roadmap and removes the shared first-run
administrator password. It is the first release to publish standalone applications for Windows,
Linux, and macOS from one verified workflow.

## Security Upgrade Notice

- New installations receive a unique generated `superadmin` password in
  `initial-admin-credentials.txt` under `ROXX_CONFIG_DIR`.
- The initial password must be changed at first sign-in; RoXX then deletes the credential file.
- Existing installations still using the historical `admin/admin` password are rotated
  automatically. Operators must read the replacement credential file before signing in.
- SAML accounts can authenticate only through the validated ACS flow, and SAML identity names can
  no longer take over an existing local, LDAP, or RADIUS administrator.
- Deployments may provide `ROXX_BOOTSTRAP_ADMIN_PASSWORD` during setup. Supplied passwords are not
  written to the credential file and must satisfy the 12-character complexity policy.
- API token, MFA, WebAuthn, and RADIUS backend databases now honor `ROXX_CONFIG_DIR`. Before
  upgrading an installation that previously stored these files under `~/.roxx`, stop RoXX and
  copy `api_tokens.db`, `mfa.db`, `webauthn.db`, and `radius_backends.db` into the configured
  directory while preserving service-account ownership and mode `0600`.

## Production Operations

- Added rotating server logs, deeper readiness checks, Prometheus metrics, and JSONL audit export.
- Added production security profiles, hardened systemd units, and repeatable non-interactive setup.
- Added guarded Windows and Linux upgrades with readiness-based rollback.
- Added HAProxy and Keepalived deployment examples with active/passive guidance.

## Packaging And Supply Chain

- Retained one unified `roxx.exe` application on Windows.
- Added standalone Linux, Debian, RPM, and macOS release assets.
- Added SPDX 2.3 SBOMs, SHA256 checksums, provenance and SBOM attestations.
- Added post-upload download and checksum verification for every release asset.
- Authenticode signing remains conditional on the repository signing-certificate secrets.

## Compatibility And Remaining External Validation

CI covers supported GitHub-hosted Windows, Ubuntu, and macOS runners. Real identity-provider
contract tests, production network appliances, privileged package installation, Authenticode
signing, and multi-host HA still require operator infrastructure and credentials; this release
does not claim those external validations.

The local Python 3.12 release-candidate suite passes all `145` tests, and the resolved third-party
dependency audit reports no known vulnerabilities. Platform executables,
packages, smoke probes, SBOMs, attestations, and downloadable checksums are validated by the tag
workflow before the release is considered complete.

## Upgrade

Back up configuration and data, verify `SHA256SUMS.txt`, replace the existing application, and
restart the service. Linux installations upgrading from a legacy pre-1.0.2 service must ensure
that systemd uses `ExecStart=.../roxx server`.
