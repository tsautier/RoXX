# Changelog

All notable changes to RoXX will be documented in this file.

## [1.0.0-beta6] - 2026-01-22

### 🎉 Major Features

#### MFA Credential Management
- **Complete MFA management interface** at `/admins/{username}/mfa`
- View all WebAuthn credentials (security keys, biometrics)
- Delete individual credentials with confirmation
- Reset TOTP/authenticator app configuration
- Real-time MFA status dashboard showing:
  - TOTP/Authenticator status
  - Number of registered WebAuthn keys
  - SMS MFA status
- Fixed binary data serialization bug (credential_id, public_key → base64)

#### Template System Unification
- **Unified all 12 templates** to use `base.html` for consistent UI
- Removed obsolete `layout.html` template
- "User Management" link now visible on all pages
- Consistent sidebar navigation across entire application
- Professional, cohesive admin interface

#### SAML Configuration Enhancements
- **SP Metadata Information Box** in SAML provider configuration
- Clear display of Metadata URL and ACS URL endpoints  
- Test Connection functionality for provider validation
- Comprehensive SAML setup guide with provider-specific instructions:
  - Okta integration guide
  - Azure AD / Entra ID guide
  - Google Workspace guide

### ✨ UX Improvements

#### Toast Notification System
- **Modern, non-blocking notifications** replacing all `alert()` calls
- 4 notification types: Success, Error, Warning, Info
- Auto-dismiss after 5 seconds with manual close option
- Smooth slide-in/slide-out animations
- Contextual error messages throughout the application
- Implemented in:
  - MFA credential deletion
  - TOTP reset operations
  - API error handling

### 🔒 Security Enhancements

#### Rate Limiting
- **slowapi integration** for endpoint protection
- Configured rate limits by endpoint type:
  - Login: 5 requests/minute
  - MFA verification: 10 requests/minute
  - API writes: 30 requests/minute
  - API reads: 60 requests/minute
  - SAML/Auth: 20-30 requests/minute
- Custom rate limit exception handler with audit logging
- Automatic logging of all rate limit violations

#### CSRF Protection
- **CSRF token generation and validation** utilities
- Token expiration (1 hour default)
- Support for form data, headers, and query parameters
- Ready for integration in state-changing operations

### 📚 Documentation

#### Comprehensive Guides
- **Complete README.md** with:
  - Installation instructions
  - Quick start guide
  - API documentation with examples
  - Security best practices
  - Troubleshooting section
  
- **SAML Setup Guide** (`docs/saml-setup.md`):
  - Step-by-step configuration
  - Provider-specific guides (Okta, Azure AD, Google)
  - Attribute mapping explained
  - Common troubleshooting scenarios
  
- **Security Integration Guide** (`docs/security-integration.md`):
  - Rate limiting implementation
  - CSRF protection integration
  - Priority list of routes to protect
  - Testing and monitoring procedures

### 🐛 Bug Fixes

- Fixed WebAuthn credential binary data serialization
- Corrected template inheritance issues
- Resolved navigation link visibility across pages
- Fixed alert() blocking UX in MFA management

### 🛠️ Technical Improvements

- Created reusable toast notification component (CSS + JS)
- Implemented security module structure:
  - `roxx/core/security/rate_limit.py`
  - `roxx/core/security/csrf.py`
  - `roxx/core/security/__init__.py`
- Enhanced error handling with contextual messages
- Improved code organization and maintainability

### 📦 Files Added

- `/static/css/toast.css` - Toast notification styles
- `/static/js/toast.js` - Toast notification API
- `roxx/core/security/` - Security utilities module
- `docs/saml-setup.md` - SAML configuration guide
- `docs/security-integration.md` - Security implementation guide
- `README.md` - Complete project documentation

### 📝 Files Modified

- `roxx/web/app.py` - Rate limiter integration, version bump
- `roxx/web/templates/base.html` - Toast system integration
- `roxx/web/templates/admin_mfa.html` - Toast notifications
- 12 HTML templates - Unified to base.html
- `roxx/core/auth/db.py` - MFA management methods

### 🚀 Commits (8 total)

1. `6745851` - feat: implement MFA credential management for admin users
2. `7cc4fc9` - fix: complete template unification - all 12 templates now extend base.html
3. `c5328d1` - feat: complete SAML UI with SP metadata display and cleanup
4. `b99c4fd` - feat(ux): add toast notification system
5. `a57e65c` - feat(ux): integrate toast notifications and add comprehensive docs
6. `5795497` - feat(security): add rate limiting and CSRF protection modules
7. `15e8103` - docs: add security integration guide for rate limiting and CSRF
8. `VERSION` - chore: bump version to 1.0.0-beta6

---

## [1.0.0-beta5] - Previous Release

- SAML 2.0 SSO integration
- Dashboard redesign with system monitor
- LDAP/AD authentication backend
- Basic MFA support (TOTP  + WebAuthn)
- User management interface

---

**Full Changelog**: https://github.com/tsautier/RoXX/compare/v1.0.0-beta5...v1.0.0-beta6
