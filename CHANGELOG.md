# Changelog

All notable changes to RoXX will be documented in this file.

## [1.0.0-beta8] - 2026-03-24

### Major Features
- Completed the `beta8` feature set around RBAC hardening, GUI/API symmetry, and enterprise MFA integrations.
- Added Duo Security and Okta Verify support for RADIUS backends.
- Introduced API-first management flows for system settings, MFA self-service, observability, and integration tooling.
- Added RBAC documentation and aligned admin-role management with the permission matrix.

### Security
- Reworked session and RBAC enforcement so roles are resolved server-side instead of trusting client cookies.
- Applied authentication and authorization checks consistently across sensitive pages, APIs, and the log WebSocket.
- Tightened access around PKI, SSL/TLS, MFA, health, observability, and management surfaces.

### MFA And Identity
- Finalized SMS MFA self-service, including phone registration and login OTP delivery.
- Completed the self-service MFA experience across TOTP, WebAuthn, client certificates, and SMS.
- Improved Duo and Okta testing and integration points in both backend logic and the admin UI.

### Admin Portal
- Fixed dynamic RADIUS backend forms and added real provider-specific configuration fields.
- Corrected sidebar active-state handling across multiple pages.
- Replaced synthetic dashboard authentication metrics with real audit-log aggregation and filtering.
- Added 24-hour and 1-hour metric filters with hourly and minute granularity.
- Completed PKI and certificate download flows in the GUI.
- Improved NPS Migration so selected clients and backend stubs can be imported explicitly.

### Technical Improvements
- Replaced deprecated FastAPI startup hooks with lifespan handling.
- Updated template rendering to current Starlette/FastAPI conventions.
- Fixed Windows issues around SQLite cleanup and command execution portability.
- Hardened API error handling so business errors remain `400` instead of being masked as `500`.
- Removed tenant support entirely from code, UI, API surface, and docs.

### Verification
- Full test suite passing at release cut: `114 passed`.

## [1.0.0-beta7] - 2026-03-22

### Major Features
- Added the NPS Migration Assistant for importing Microsoft NPS XML exports.
- Added the visual analytics dashboard and advanced live log visibility.
- Introduced AGPLv3 licensing and integrity protections.

### Security
- Added integrity manifests and ownership headers.
- Added rate limiting and CSRF protection groundwork.

### Platform
- Stabilized CI/CD and packaging dependencies.
- Fixed MFA management, template unification, and SAML UI issues.

