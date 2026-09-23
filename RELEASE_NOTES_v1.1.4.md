# RoXX v1.1.4 Release Notes

**Release Date:** September 23, 2026
**Tag:** v1.1.4

## Security hardening

- Cookie-authenticated POST, PUT, PATCH, and DELETE requests now reject untrusted browser origins. The WebSocket logs handshake also requires a trusted `Origin`, an active signed session, and log-viewing permission.
- `ROXX_ALLOWED_ORIGINS` sets exact accepted public origins for reverse-proxy deployments. When configured, no implicit host-derived origin is accepted. The SAML assertion callback remains exempt from the HTTP origin check because it uses provider-response validation.
- Logout now requires `POST /logout`; `GET /logout` no longer changes session state.
- `/api/users` no longer exposes RADIUS user passwords, and the users page renders untrusted names as text rather than HTML.
- Documented an OWASP ASVS 5.0.0 Level 2 review target and release security gates. This is not a claim of full ASVS compliance.

## Upgrade impact

Set `ROXX_ALLOWED_ORIGINS` to the exact public `http://` or `https://` origin when the public URL differs from the application's internal URL. Update custom WebSocket clients to send a matching `Origin`, and update external logout links to use POST. Browser clients must send a same-origin `Origin` or `Referer` on cookie-authenticated mutations. Non-cookie API clients are not affected by this origin check. Back up configuration and data before upgrading.

## Verification limits

Automated tests cover accepted and rejected origins, logout methods, and secret redaction. The release workflow must still finish its multi-platform builds, smoke checks, checksums, and post-upload verification before the release is considered published. This release does not certify full OWASP ASVS coverage or production identity-provider, HA, or RADIUS integrations.
