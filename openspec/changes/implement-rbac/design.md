## Context

The application currently authorizes via a single `Employee.is_admin` boolean. Five RBAC database models (`roles`, `permissions`, `role_permissions`, `employee_roles`, `employee_permissions`) exist but have zero API endpoints. The frontend uses `isAdmin` to gate sidebar items and features.

The change introduces a complete permission-code-based authorization system with role management, removing the `is_admin` column entirely.

## Goals / Non-Goals

**Goals:**
- Define a fixed set of permission codes covering every API resource
- Expose CRUD for roles (group permissions into named roles)
- Expose assignment of roles and individual permissions to employees
- Replace every `if not current_user.is_admin` check with `require_permission(perm_code)` dependency
- Provide a `get_current_user_permissions()` function that resolves a user's effective permissions (role-based + direct overrides)
- Return effective permissions in `/employees/me`
- Frontend: replace `isAdmin` with `can(perm)` helper throughout sidebar, bottom-nav, and dashboard cards
- Frontend: admin pages for managing roles and employee permissions
- Seed migrations for default permissions, roles, and assignment to existing admin user

**Non-Goals:**
- Permission scoping by resource ownership (e.g., "edit only own sales") — not needed yet
- UI-level row/field-level permission control — future enhancement
- Real-time permission updates (token must be re-issued on permission change) — acceptable for now
- Audit logging of permission changes — future enhancement

## Decisions

### Permission Code Format

`<resource>.<action>` where resources match API router names and actions are standard CRUD + feature-specific verbs.

```
sales.create           customers.read         items.read
sales.edit             customers.create       items.create
sales.complete         customers.update       items.update
sales.suspend          customers.delete       items.delete
sales.void                                    items.manage_categories
sales.view_suspended
                      employees.read         expenses.read
                      employees.create       expenses.create
                      employees.update       expenses.update
                      employees.delete       expenses.delete
                                             expenses.manage_categories
invoices.read          quotations.read
invoices.create        quotations.create     cash_ups.create
invoices.update        quotations.update     cash_ups.read
invoices.void          quotations.delete
invoices.send          quotations.send       admin.permissions
invoices.manage_credit_notes                 admin.roles
                                             admin.settings
                                             reports.view
```

Rationale: matches the existing API structure, easy to read, easy to check in code via `require_permission("customers.delete")`.

### Permission Resolution Algorithm

```python
def get_effective_permissions(employee):
    # 1. Role-based permissions (from all assigned roles)
    perms = set()
    for role in employee.roles:
        for rp in role.permissions:
            perms.add(rp.permission.code)

    # 2. Direct positive overrides
    for ep in employee.direct_permissions:
        perms.add(ep.permission.code)

    return perms
```

No negative permissions — an employee either has a permission or doesn't. This keeps the mental model simple.

### `require_permission()` Dependency

A factory function that returns a FastAPI dependency:

```python
def require_permission(code: str):
    async def dependency(current_user: Employee = Depends(get_current_user)) -> None:
        if not current_user.is_active:
            raise HTTPException(403, "Account is disabled")
        perms = await get_effective_permissions(current_user)
        if code not in perms:
            raise HTTPException(403, "Insufficient permissions")
    return dependency
```

Usage: `require_permission("items.create")` as a `Depends()` parameter.

**Alternative considered:** Using `Annotated` type alias like `CurrentUserDep`. Rejected because each permission needs its own dependency instance; a factory function is cleaner.

### Default Roles (Seeded)

| Role | Permissions |
|------|-------------|
| Admin | All codes |
| Manager | All except `admin.*`, `employees.delete` |
| Cashier | `sales.*`, `customers.read`, `customers.create`, `items.read` |
| View-only | `*.read` (every read permission) |

The existing `admin` Employee gets the Admin role assigned in the seed migration.

### Migration Strategy

1. **Migration 002**: Insert all permission codes, create default roles, assign Admin role to existing admin employee. This migration runs before any code changes.
2. **Migration 003**: Remove `is_admin` column from employees table. This runs after all code is deployed.

Both migrations are reversible (`downgrade()`).

### Frontend Permission Gating

```typescript
// auth-context.tsx
interface User {
  id: string;
  username: string;
  permissions: string[];
}

function can(permission: string): boolean {
  return user.permissions.includes(permission);
}
```

Component wrapper:

```tsx
function Can({ permission, children, fallback = null }: CanProps) {
  const { user } = useAuth();
  if (!user) return fallback;
  return user.permissions.includes(permission) ? children : fallback;
}
```

Sidebar nav items change from `admin: boolean` to `perm: string`:

```tsx
{ href: "/customers", label: "Customers", icon: Users, perm: "customers.read" }
```

## Risks / Trade-offs

- **Token staleness**: Permissions are resolved at login time and embedded in the JWT (as metadata) or fetched via `/employees/me`. If an admin changes an employee's roles, the employee's current token is still valid with old permissions. Mitigation: fetch permissions from `/employees/me` on each page load (already done for user data). No need for JWT permission embedding.
- **Migration ordering**: Migration 002 (seed) must run before the refactored code is deployed. Migration 003 (column removal) must run after. Mitigation: deploy code changes in two phases — first the new API + frontend (with is_admin still present but ignored), then the column removal.
- **Frontend breakage during transition**: The sidebar/bottom-nav rely on `isAdmin`. They must switch to `can()` before `is_admin` is removed from the API response. Mitigation: deploy PR 4 (frontend gating) before PR 3 (backend refactor removing is_admin).
