# RBAC Guide

This document describes the administrative roles available in RoXX and what each role is allowed to do.

## Roles

### `superadmin`

Highest-privilege administrative role.

Can:
- Create admin accounts
- Delete admin accounts
- Change admin roles
- Manage RADIUS users
- Manage RADIUS backends
- Manage RADIUS/NPS migration tooling
- Manage authentication providers
- Manage MFA settings and admin MFA flows
- Manage system configuration
- Manage SSL/TLS
- Manage PKI
- Manage API tokens
- View dashboard, logs, and system information

### `admin`

Operational administrator role for day-to-day platform management.

Can:
- Manage RADIUS users
- Manage RADIUS backends
- Use RADIUS/NPS migration tooling
- Manage authentication providers
- Manage MFA settings and self-service/admin MFA flows
- Manage API tokens
- View dashboard, logs, and system information

Cannot:
- Create admin accounts
- Delete admin accounts
- Change admin roles
- Change core system configuration
- Manage SSL/TLS
- Manage PKI

### `auditor`

Read-only administrative role.

Can:
- View dashboard
- View audit logs
- View system information

Cannot:
- Perform write actions
- Manage users, backends, MFA, providers, or system configuration

## Permission Matrix

| Action | superadmin | admin | auditor |
| --- | --- | --- | --- |
| View dashboard | Yes | Yes | Yes |
| View logs | Yes | Yes | Yes |
| View system info | Yes | Yes | Yes |
| Manage admin accounts | Yes | No | No |
| Change admin roles | Yes | No | No |
| Delete admin accounts | Yes | No | No |
| Manage RADIUS users | Yes | Yes | No |
| Manage RADIUS backends | Yes | Yes | No |
| Manage RADIUS/NPS migration | Yes | Yes | No |
| Manage auth providers | Yes | Yes | No |
| Manage MFA | Yes | Yes | No |
| Manage API tokens | Yes | Yes | No |
| Manage system settings | Yes | No | No |
| Manage SSL/TLS | Yes | No | No |
| Manage PKI | Yes | No | No |

## Where Roles Are Managed

Roles are managed from the admin portal on `/admins`.

Current flows:
- Create an admin with a role from the "Add New Admin" form
- Change an existing admin role from the role selector on the admin list

Only `superadmin` can access those role-management operations.

## Implementation Notes

The live RBAC implementation is enforced in:
- [`roxx/core/auth/rbac.py`](/C:/RoXX/roxx/core/auth/rbac.py)
- [`roxx/web/app.py`](/C:/RoXX/roxx/web/app.py)
- [`roxx/core/auth/db.py`](/C:/RoXX/roxx/core/auth/db.py)

The database source of truth for roles is the `admins.role` column in `roxx.db`.
