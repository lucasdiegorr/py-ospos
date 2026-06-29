## 1. PR 1: Migration Seed (Permissions, Roles, Admin assignment)

- [x] 1.1 Create Alembic migration `002_seed_permissions_and_roles` that inserts all permission codes into `permissions` table
- [x] 1.2 In the same migration, create default roles (Admin, Manager, Cashier, View-only) with their permission associations in `role_permissions`
- [x] 1.3 In the same migration, assign the existing admin Employee to the Admin role via `employee_roles`
- [x] 1.4 Verify migration runs cleanly: `alembic upgrade head` and `alembic downgrade -1`

## 2. PR 2: Backend API — Roles & Permissions Endpoints

- [x] 2.1 Create `app/schemas/role.py` with `RoleCreate`, `RoleUpdate`, `RoleResponse`, `PermissionResponse`
- [x] 2.2 Create `app/api/v1/role.py` router with CRUD for roles (`POST/GET/GET/PATCH/DELETE /api/v1/roles`)
- [x] 2.3 Add `GET /api/v1/permissions` read-only endpoint
- [x] 2.4 Add `POST /api/v1/employees/{id}/roles` and `DELETE /api/v1/employees/{id}/roles/{role_id}` endpoints
- [x] 2.5 Add `POST /api/v1/employees/{id}/permissions` and `DELETE /api/v1/employees/{id}/permissions/{perm_id}` endpoints
- [x] 2.6 Create `get_effective_permissions()` function in `app/core/auth.py`
- [x] 2.7 Update `EmployeeResponse` schema to include `permissions: list[str]`
- [x] 2.8 Update `/api/v1/employees/me` to resolve and return effective permissions
- [x] 2.9 Register `role.py` router in `app/main.py`
- [x] 2.10 Write tests for all new endpoints (CRUD roles, employee assignment, permission resolution)
- [x] 2.11 Run `pytest --cov` to verify coverage

## 3. PR 3: Backend Refactor — Permission-Based Authorization

- [x] 3.1 Create `require_permission(code: str)` factory dependency in `app/core/auth.py`
- [x] 3.2 Refactor `app/api/v1/customer.py`: replace `is_admin` check with `require_permission("customers.delete")`
- [x] 3.3 Refactor `app/api/v1/employee.py`: replace `is_admin` checks with `require_permission("employees.create")` and `require_permission("employees.delete")`
- [x] 3.4 Refactor `app/api/v1/item.py`: replace `is_admin` check with `require_permission("items.delete")`
- [x] 3.5 Remove `is_admin` from `EmployeeResponse` schema
- [x] 3.6 Create Alembic migration `003_remove_is_admin_from_employees` that drops the `is_admin` column
- [x] 3.7 Remove `is_admin` column from `Employee` SQLAlchemy model
- [x] 3.8 Update `app/db/seed.py` to use role assignment instead of `is_admin=True`
- [x] 3.9 Write tests for: each refactored endpoint returns 403 when missing permission, 200/204 when permitted
- [x] 3.10 Run `pytest --cov` to verify coverage

## 4. PR 4: Frontend — Permission Gating

- [x] 4.1 Update `User` interface in `auth-context.tsx`: replace `isAdmin: boolean` with `permissions: string[]`
- [x] 4.2 Update login and `getCurrentUser` flows to store permissions array
- [x] 4.3 Add `can(permission: string): boolean` helper to auth context
- [x] 4.4 Create `<Can permission="..." fallback={null}>` component
- [x] 4.5 Update `sidebar.tsx`: change nav items from `admin: boolean` to `perm: string`; filter using `can()`
- [x] 4.6 Update `bottom-nav.tsx`: apply permission gating to customers, items, expenses links
- [x] 4.7 Update dashboard card page to use permission gating instead of `isAdmin`
- [x] 4.8 Update `EmployeeResponse` type in `api.ts`: remove `is_admin`, add `permissions`
- [x] 4.9 Remove `is_admin` references from login response types in `api.ts`
- [x] 4.10 Write tests: login returns permissions, `can()` helper, sidebar rendering with permissions
- [x] 4.11 Run `npm run build` and fix any type errors

## 5. PR 5: Frontend — Admin Permission Management Pages

- [ ] 5.1 Add `admin.roles` link to sidebar (visible only with that permission)
- [ ] 5.2 Create `frontend/src/app/admin/roles/page.tsx` — list all roles
- [ ] 5.3 Create role creation/edit form (modal or page) with permission checkboxes
- [ ] 5.4 Create role delete confirmation
- [ ] 5.5 Create `frontend/src/app/admin/employees/[id]/permissions/page.tsx` — view/assign roles and direct permissions
- [ ] 5.6 Add API methods to `api.ts`: `listRoles`, `createRole`, `updateRole`, `deleteRole`, `getEmployeeRoles`, `assignEmployeeRoles`, `removeEmployeeRole`
- [ ] 5.7 Write integration tests for role CRUD flow and employee permission assignment
- [ ] 5.8 Run `npm run build` and fix any type errors
- [ ] 5.9 Run `pytest --cov` to verify backend coverage
- [ ] 5.10 Run `npm test` to verify frontend tests pass
