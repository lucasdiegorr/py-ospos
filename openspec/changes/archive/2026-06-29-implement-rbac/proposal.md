## Why

The current authorization system uses a binary `is_admin` boolean on the Employee model. This provides no granularity — non-admin employees cannot access features like customers, items, or expenses, even if they should have limited access. A role-based access control (RBAC) system is needed to support the real-world POS workflow where cashiers, managers, and back-office staff need different permission levels. The RBAC database models already exist but have no API or frontend.

## What Changes

- **NEW** Permission codes for every feature (`entidade.acao` pattern)
- **NEW** `/api/v1/roles` CRUD endpoints
- **NEW** `/api/v1/permissions` list endpoint
- **NEW** `/api/v1/employees/{id}/roles` assign/unassign endpoints
- **NEW** `require_permission()` FastAPI dependency replacing `is_admin` checks
- **BREAKING** `Employee.is_admin` column removed from model and schemas
- **BREAKING** `/employees/me` response changes: `is_admin` removed, `permissions: string[]` added
- **NEW** Migration seed with default roles (Admin, Manager, Cashier, View-only)
- **NEW** Frontend `can(perm)` helper and `<Can>` component replacing `isAdmin`
- **NEW** Frontend `/admin/roles` and `/admin/employees/{id}/permissions` pages
- **NEW** Frontend sidebar/bottom-nav gating based on permissions instead of admin flag

## Capabilities

### New Capabilities

- `rbac`: Role-based access control — permission codes, role management, and per-employee permission resolution

### Modified Capabilities

<!-- No existing specs have their requirements changed. Permission checks are implementation details within each feature's existing spec. -->

## Impact

- `app/models/employee.py`: remove `is_admin` column
- `app/schemas/employee.py`: remove `is_admin` from response, add `permissions`
- `app/api/v1/employee.py`: remove `is_admin` usage, add permission-based checks
- `app/api/v1/customer.py`: replace `is_admin` checks with `require_permission()`
- `app/api/v1/item.py`: replace `is_admin` checks with `require_permission()`
- `app/core/auth.py`: add `require_permission()` dependency; add `get_current_user_permissions()`
- `app/models/role.py`: already exists, no changes needed
- `alembic/versions/`: new migration for seed data and column removal
- `frontend/src/lib/auth-context.tsx`: replace `isAdmin` with `permissions`
- `frontend/src/lib/api.ts`: update Employee and User types, add role/permission endpoints
- `frontend/src/components/sidebar.tsx`: permission-based gating
- `frontend/src/components/bottom-nav.tsx`: permission-based gating
- `frontend/src/app/`: new `/admin/roles` and `/admin/employees` permission management pages
