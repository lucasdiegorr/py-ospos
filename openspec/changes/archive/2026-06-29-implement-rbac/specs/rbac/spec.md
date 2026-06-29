## ADDED Requirements

### Requirement: Permission codes list

The system SHALL define a fixed set of permission codes covering every API resource. Each code SHALL follow the format `<resource>.<action>`.

The complete set of permission codes SHALL be:
- `sales.create`, `sales.edit`, `sales.complete`, `sales.suspend`, `sales.void`, `sales.view_suspended`
- `customers.read`, `customers.create`, `customers.update`, `customers.delete`
- `items.read`, `items.create`, `items.update`, `items.delete`, `items.manage_categories`
- `employees.read`, `employees.create`, `employees.update`, `employees.delete`
- `expenses.read`, `expenses.create`, `expenses.update`, `expenses.delete`, `expenses.manage_categories`
- `invoices.read`, `invoices.create`, `invoices.update`, `invoices.void`, `invoices.send`, `invoices.manage_credit_notes`
- `quotations.read`, `quotations.create`, `quotations.update`, `quotations.delete`, `quotations.send`
- `cash_ups.create`, `cash_ups.read`
- `admin.permissions`, `admin.roles`, `admin.settings`
- `reports.view`

#### Scenario: Permission code exists in seed
- **WHEN** the system runs migration 002
- **THEN** every permission code listed above SHALL exist in the `permissions` table

#### Scenario: Permission code format validation
- **WHEN** a permission code is created
- **THEN** its format SHALL match `<resource>.<action>`

### Requirement: Role CRUD API

The system SHALL expose CRUD endpoints for roles at `/api/v1/roles`.

- `POST /api/v1/roles` — create a role (requires `admin.roles`)
- `GET /api/v1/roles` — list all roles (requires `admin.roles`)
- `GET /api/v1/roles/{id}` — get role detail with assigned permissions (requires `admin.roles`)
- `PATCH /api/v1/roles/{id}` — update role name, description, or permission associations (requires `admin.roles`)
- `DELETE /api/v1/roles/{id}` — delete a role (requires `admin.roles`)

#### Scenario: Create role
- **WHEN** an admin sends POST to `/api/v1/roles` with name, description, and permission_ids
- **THEN** the system SHALL create the role and return it with status 201

#### Scenario: List roles
- **WHEN** an admin sends GET to `/api/v1/roles`
- **THEN** the system SHALL return all roles with their metadata

#### Scenario: Non-admin cannot manage roles
- **WHEN** a user without `admin.roles` sends any request to `/api/v1/roles`
- **THEN** the system SHALL return 403

#### Scenario: Delete role
- **WHEN** an admin sends DELETE to `/api/v1/roles/{id}`
- **THEN** the system SHALL delete the role and return 204

### Requirement: Permissions list API

The system SHALL expose a read-only endpoint at `/api/v1/permissions` that returns all available permission codes.

#### Scenario: List all permissions
- **WHEN** any authenticated user sends GET to `/api/v1/permissions`
- **THEN** the system SHALL return all permission codes with their names and descriptions

### Requirement: Employee role assignment

The system SHALL expose endpoints to manage role assignments for employees.

- `POST /api/v1/employees/{id}/roles` — assign roles to an employee (requires `admin.roles`)
- `GET /api/v1/employees/{id}/roles` — list an employee's assigned roles (requires `employees.read`)
- `DELETE /api/v1/employees/{id}/roles/{role_id}` — remove a role from an employee (requires `admin.roles`)
- `POST /api/v1/employees/{id}/permissions` — add a direct permission override (requires `admin.permissions`)
- `DELETE /api/v1/employees/{id}/permissions/{perm_id}` — remove a direct permission override (requires `admin.permissions`)

#### Scenario: Assign role to employee
- **WHEN** an admin sends POST to `/api/v1/employees/{id}/roles` with role_ids
- **THEN** the system SHALL associate the employee with those roles

#### Scenario: Get employee roles
- **WHEN** a user with `employees.read` sends GET to `/api/v1/employees/{id}/roles`
- **THEN** the system SHALL return the employee's assigned roles

#### Scenario: Direct permission override
- **WHEN** an admin sends POST to `/api/v1/employees/{id}/permissions` with permission_id
- **THEN** the system SHALL grant that permission directly to the employee

### Requirement: Effective permission resolution

The system SHALL resolve an employee's effective permissions as the union of:
1. Permissions from all assigned roles
2. Direct permission overrides

#### Scenario: Employee permission set
- **WHEN** an employee is assigned roles with permissions `[customers.read, items.read]` and a direct override `sales.create`
- **THEN** the employee's effective permissions SHALL be `{customers.read, items.read, sales.create}`

### Requirement: Current user returns permissions

The system SHALL return the current employee's effective permissions in the `/api/v1/employees/me` response.

`EmployeeResponse` SHALL include a `permissions: list[str]` field listing all effective permission codes.

#### Scenario: Get own permissions
- **WHEN** an authenticated user sends GET to `/api/v1/employees/me`
- **THEN** the response SHALL include a `permissions` array with all their effective permission codes

### Requirement: Permission-based authorization

Every protected API endpoint SHALL use the `require_permission(code)` dependency to enforce authorization. Endpoints that previously checked `is_admin` SHALL be updated to check specific permission codes.

The mapping SHALL be:
- `customers.delete` → `DELETE /api/v1/customers/{id}`
- `employees.create` → `POST /api/v1/employees/`
- `employees.delete` → `DELETE /api/v1/employees/{id}`
- `items.delete` → `DELETE /api/v1/items/{id}`

#### Scenario: Missing permission returns 403
- **WHEN** an authenticated user without `customers.delete` sends DELETE to `/api/v1/customers/{id}`
- **THEN** the system SHALL return 403 Forbidden

#### Scenario: Sufficient permission allows action
- **WHEN** an authenticated user with `customers.delete` sends DELETE to `/api/v1/customers/{id}`
- **THEN** the system SHALL soft-delete the customer and return 204

### Requirement: Default roles seeding

The system SHALL seed the following default roles in migration 002:

| Role | Permissions |
|------|-------------|
| Admin | All permission codes |
| Manager | All except `admin.*` and `employees.delete` |
| Cashier | `sales.*`, `customers.read`, `customers.create`, `items.read` |
| View-only | All `*.read` permissions |

The existing admin Employee (username: `admin`) SHALL be assigned the Admin role.

#### Scenario: Default roles exist after migration
- **WHEN** migration 002 runs
- **THEN** roles Admin, Manager, Cashier, and View-only SHALL exist in the `roles` table

#### Scenario: Admin user gets Admin role
- **WHEN** migration 002 runs
- **THEN** the existing admin Employee SHALL be associated with the Admin role via `employee_roles`

### Requirement: is_admin column removal

The `Employee.is_admin` column SHALL be removed in migration 003. No code SHALL reference `is_admin` after the refactor.

#### Scenario: is_admin removed from API
- **WHEN** any authenticated user sends GET to `/api/v1/employees/me`
- **THEN** the response SHALL NOT contain an `is_admin` field

### Requirement: Frontend permission helper

The frontend SHALL provide a `can(permission: string): boolean` function that returns whether the current user has a given permission.

The frontend SHALL provide a `<Can permission="..." fallback={null}>` component that conditionally renders children based on permission.

#### Scenario: can() returns true for owned permission
- **WHEN** the current user has `customers.read` in their permissions array
- **THEN** `can("customers.read")` SHALL return true

#### Scenario: can() returns false for missing permission
- **WHEN** the current user does NOT have `admin.roles` in their permissions array
- **THEN** `can("admin.roles")` SHALL return false

### Requirement: Frontend sidebar permission gating

The sidebar navigation SHALL use `can(perm)` instead of `isAdmin` to show/hide items.

Each nav item SHALL specify a required permission code. The item SHALL only render if the user has that permission.

| Route | Permission |
|-------|-----------|
| `/customers` | `customers.read` |
| `/items` | `items.read` |
| `/employees` | `employees.read` |
| `/expenses` | `expenses.read` |
| `/invoices` | `invoices.read` |
| `/quotations` | `quotations.read` |

#### Scenario: Sidebar shows permitted items
- **WHEN** a user with only `customers.read` and `items.read` views the sidebar
- **THEN** the sidebar SHALL show Customers and Items links only

### Requirement: Frontend admin role management page

The system SHALL provide a `/admin/roles` page where users with `admin.roles` permission can:
- View all roles
- Create new roles with selected permissions
- Edit role name, description, and permission associations
- Delete roles

#### Scenario: Admin views roles page
- **WHEN** a user with `admin.roles` navigates to `/admin/roles`
- **THEN** the page SHALL display a list of all roles with their permission counts

#### Scenario: User without permission redirected
- **WHEN** a user without `admin.roles` navigates to `/admin/roles`
- **THEN** the page SHALL show an "access denied" message or redirect away

### Requirement: Frontend employee permissions page

The system SHALL provide a `/admin/employees/{id}/permissions` page where users with `admin.roles` or `admin.permissions` can:
- View an employee's current roles and direct permission overrides
- Assign and remove roles
- Add and remove direct permission overrides
- See the employee's effective resolved permission set

#### Scenario: Admin manages employee permissions
- **WHEN** a user with `admin.roles` navigates to `/admin/employees/{id}/permissions`
- **THEN** the page SHALL show the employee's roles and allow assignment changes
