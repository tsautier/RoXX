# RoXX Configuration Templates

This directory contains modern configuration templates for RoXX deployment.

## Files

### FreeRADIUS Configuration
- `freeradius_sites.conf.template` - Main site configuration
- `freeradius_eap.conf.template` - EAP/802.1X module (TLS 1.2+)
- `freeradius_mschap.conf.template` - MS-CHAP module
- `freeradius_ldap.conf.template` - LDAP/AD integration
- `freeradius_yubikey.conf.template` - YubiKey OTP module
- `freeradius_exec.conf.example` - Python auth scripts integration
- `radius_clients.conf.template` - NAS clients configuration

### Authentication
- `inwebo.conf.template` - inWebo Push configuration
- `totp.conf.template` - TOTP settings
- `totp_secrets.txt.template` - TOTP user secrets
- `yubikey_mapping.conf.template` - YubiKey user mapping

### Users
- `users.conf.template` - Local users database

## Usage

These templates are used by the RoXX setup wizard (`roxx-setup`) to generate
production-ready configuration files based on your environment.

All templates use modern best practices and are optimized for security.
