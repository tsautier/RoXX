# RoXX v1.1.3 Release Notes

**Release Date:** September 23, 2026
**Tag:** v1.1.3

## Security fixes

- The administration service no longer accepts the legacy unsigned `session` cookie as proof of authentication. Only the signed `roxx_session` cookie is accepted.
- Unknown administrator names and database records with an absent or invalid role no longer receive an implicit `admin` role. Signed sessions are checked against the current database role on every request, so deletion and role changes take effect on subsequent requests.
- `/ws/logs` no longer accepts HTTP Basic credentials, including the previous default fallback. It requires an active signed session with log-viewing permission.

## Upgrade impact

Legacy unsigned-cookie sessions must sign in again. Existing signed sessions for valid accounts continue to work. WebSocket clients using Basic credentials must switch to the signed session obtained through the normal login and MFA flow. Accounts whose stored role is missing or invalid cannot authenticate until an authorized administrator repairs the role in the database. Do not set a blanket default role to work around this check.

Back up configuration and data before upgrading. On Windows, services registered before v1.1.2 still require the service reinstallation described in `docs/OPERATIONS.md`; a v1.1.2 service can use the normal upgrade path. Linux and macOS binaries and Linux packages use their existing upgrade procedures.

## Verification and limits

The release workflow runs the test suite on Windows, Linux, and macOS, builds and smokes platform executables, publishes packages and SPDX SBOMs, generates SHA256 checksums and attestations, and verifies downloaded release assets. Real enterprise identity providers, HA deployments, and a production RADIUS integration are not certified by those automated checks.
