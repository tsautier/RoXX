# Security Policy

## Supported Versions

Security fixes target the latest published release. Older branches are not guaranteed to receive backports; check the [releases](https://github.com/tsautier/RoXX/releases) for the current version before reporting or upgrading.

## Secure Development Baseline

RoXX uses [OWASP ASVS 5.0.0](https://owasp.org/projects/asvs) as a security review checklist, with Level 2 as the target for its administrative web service. This is a target, **not a claim that RoXX currently passes every ASVS requirement or has an OWASP certification**. Each release must record and prioritize gaps instead of silently treating a passing test suite or dependency audit as proof of compliance.

For changes that touch authentication, authorization, sessions, APIs, WebSockets, configuration, or secrets:

- Define the trust boundary and affected roles. Deny by default; check authorization on every route and object, including read-only endpoints and WebSocket handshakes/messages. Never infer a privileged role from a missing value. See the [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).
- Accept only integrity-protected session state. Review expiration, logout, privilege changes, MFA transitions, and cookie attributes against the [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
- Protect cookie-authenticated state-changing requests against CSRF; `SameSite` is defense in depth, not a blanket substitute. Review browser-initiated WebSockets for explicit origin validation and long-lived session revocation. See the [OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) and [WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html) cheat sheets.
- Validate untrusted input, avoid disclosing credentials or sensitive configuration in responses and logs, and keep secrets out of source control and release assets.
- Add negative security tests for unauthenticated, low-privilege, deleted, and malformed-session cases. Run the full test suite, dependency audit, platform builds, smoke checks, and release-asset verification before publication. Document any unverified control and its remediation owner in the release notes or roadmap.

## Reporting a Vulnerability

We take the security of RoXX seriously. If you have discovered a security vulnerability, we appreciate your help in disclosing it to us in a responsible manner.

### How to Report

Please **DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, use [GitHub private vulnerability reporting](https://github.com/tsautier/RoXX/security/advisories/new). Do not include exploit details in a public issue or discussion.

### What to Include

*   A description of the vulnerability.
*   Steps to reproduce the issue.
*   Potential impact.
*   Any proof-of-concept code or screenshots.

### Response Timeline

We aim to acknowledge reports within 48 hours and provide a fix or workaround within 14 days where feasible. These are response targets, not guaranteed deadlines; severity and the complexity of a safe fix may change the timeline.

Thank you for helping keep RoXX secure!
