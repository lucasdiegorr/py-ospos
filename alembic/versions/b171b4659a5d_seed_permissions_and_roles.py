"""seed_permissions_and_roles

Revision ID: b171b4659a5d
Revises: 001
Create Date: 2026-06-29 14:57:23.826609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision: str = "b171b4659a5d"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION_CODES: dict[str, tuple[str, str]] = {
    "sales.create": ("Create Sale", "Can create a new sale via POS"),
    "sales.edit": ("Edit Sale", "Can edit items in an open sale"),
    "sales.complete": ("Complete Sale", "Can complete/finalize a sale"),
    "sales.suspend": ("Suspend Sale", "Can suspend a sale for later recall"),
    "sales.void": ("Void Sale", "Can void a completed sale"),
    "sales.view_suspended": ("View Suspended Sales", "Can view suspended sales"),
    "customers.read": ("View Customers", "Can view customer list and details"),
    "customers.create": ("Create Customers", "Can create new customers"),
    "customers.update": ("Update Customers", "Can update customer details"),
    "customers.delete": ("Delete Customers", "Can soft-delete customers"),
    "items.read": ("View Items", "Can view item list and details"),
    "items.create": ("Create Items", "Can create new items"),
    "items.update": ("Update Items", "Can update item details"),
    "items.delete": ("Delete Items", "Can soft-delete items"),
    "items.manage_categories": ("Manage Item Categories", "Can create/update/delete item categories"),
    "employees.read": ("View Employees", "Can view employee list and details"),
    "employees.create": ("Create Employees", "Can create new employees"),
    "employees.update": ("Update Employees", "Can update employee details"),
    "employees.delete": ("Delete Employees", "Can soft-delete employees"),
    "expenses.read": ("View Expenses", "Can view expense list and details"),
    "expenses.create": ("Create Expenses", "Can create new expenses"),
    "expenses.update": ("Update Expenses", "Can update expense details"),
    "expenses.delete": ("Delete Expenses", "Can soft-delete expenses"),
    "expenses.manage_categories": ("Manage Expense Categories", "Can create/update/delete expense categories"),
    "invoices.read": ("View Invoices", "Can view invoice list and details"),
    "invoices.create": ("Create Invoices", "Can create new invoices"),
    "invoices.update": ("Update Invoices", "Can update invoice details"),
    "invoices.void": ("Void Invoices", "Can void an invoice"),
    "invoices.send": ("Send Invoices", "Can send invoices to customers"),
    "invoices.manage_credit_notes": ("Manage Credit Notes", "Can create and manage credit notes"),
    "quotations.read": ("View Quotations", "Can view quotation list and details"),
    "quotations.create": ("Create Quotations", "Can create new quotations"),
    "quotations.update": ("Update Quotations", "Can update quotation details"),
    "quotations.delete": ("Delete Quotations", "Can delete draft quotations"),
    "quotations.send": ("Send Quotations", "Can send quotations to customers"),
    "cash_ups.create": ("Create Cash Ups", "Can create end-of-day cash up records"),
    "cash_ups.read": ("View Cash Ups", "Can view cash up records"),
    "admin.permissions": ("Manage Permissions", "Can manage direct permission overrides for employees"),
    "admin.roles": ("Manage Roles", "Can create/update/delete roles and assign them to employees"),
    "admin.settings": ("Manage Settings", "Can change system-wide settings"),
    "reports.view": ("View Reports", "Can access reporting and analytics"),
}


ROLES_CONFIG: dict[str, tuple[str, bool, list[str]]] = {
    "Admin": ("Full system access", False, list(PERMISSION_CODES.keys())),
    "Manager": (
        "Access to all features except system administration",
        False,
        [
            code for code in PERMISSION_CODES
            if not code.startswith("admin.") and code != "employees.delete"
        ],
    ),
    "Cashier": (
        "Can process sales and manage customers",
        False,
        [
            "sales.create", "sales.edit", "sales.complete", "sales.suspend",
            "sales.void", "sales.view_suspended",
            "customers.read", "customers.create",
            "items.read",
        ],
    ),
    "View-only": (
        "Read-only access to all features",
        True,
        [code for code in PERMISSION_CODES if code.endswith(".read")],
    ),
}


def _gen_uuid(seed: str) -> str:
    import hashlib
    hex_digest = hashlib.md5(seed.encode()).hexdigest()
    return f"{hex_digest[0:8]}-{hex_digest[8:12]}-4{hex_digest[13:16]}-{hex_digest[16:20]}-{hex_digest[20:32]}"


def _generate_permissions(conn: sa.Connection) -> dict[str, str]:
    """Insert all permission codes and return a dict mapping code -> id."""
    perm_ids: dict[str, str] = {}
    for code, (name, desc) in PERMISSION_CODES.items():
        perm_id = _gen_uuid(f"perm:{code}")
        perm_ids[code] = perm_id
        conn.execute(
            text(
                "INSERT INTO permissions (id, code, name, description, created_at, updated_at) "
                "VALUES (:id, :code, :name, :description, NOW(), NOW()) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": perm_id, "code": code, "name": name, "description": desc},
        )
    return perm_ids


def _generate_roles(conn: sa.Connection, perm_ids: dict[str, str]) -> dict[str, str]:
    """Insert roles and role_permissions, return dict mapping role_name -> id."""
    role_ids: dict[str, str] = {}
    for role_name, (desc, is_default, codes) in ROLES_CONFIG.items():
        role_id = _gen_uuid(f"role:{role_name}")
        role_ids[role_name] = role_id
        conn.execute(
            text(
                "INSERT INTO roles (id, name, description, is_default, created_at, updated_at) "
                "VALUES (:id, :name, :description, :is_default, NOW(), NOW()) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"id": role_id, "name": role_name, "description": desc, "is_default": is_default},
        )

        for code in codes:
            perm_id = perm_ids.get(code)
            if not perm_id:
                continue
            rp_id = _gen_uuid(f"rp:{role_name}:{code}")
            conn.execute(
                text(
                    "INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) "
                    "VALUES (:id, :role_id, :perm_id, NOW(), NOW()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"id": rp_id, "role_id": role_id, "perm_id": perm_id},
            )
    return role_ids


def _assign_admin_role(conn: sa.Connection, role_ids: dict[str, str]) -> None:
    """Assign the Admin role to the existing admin employee."""
    result = conn.execute(
        text("SELECT id FROM employees WHERE username = 'admin'")
    )
    row = result.fetchone()
    if row is None:
        return

    admin_employee_id = row[0]
    admin_role_id = role_ids.get("Admin")
    if not admin_role_id:
        return

    er_id = _gen_uuid("er:admin:Admin")
    conn.execute(
        text(
            "INSERT INTO employee_roles (id, employee_id, role_id, created_at, updated_at) "
            "VALUES (:id, :employee_id, :role_id, NOW(), NOW()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": er_id, "employee_id": admin_employee_id, "role_id": admin_role_id},
    )


def upgrade() -> None:
    conn = op.get_bind()
    perm_ids = _generate_permissions(conn)
    role_ids = _generate_roles(conn, perm_ids)
    _assign_admin_role(conn, role_ids)


def downgrade() -> None:
    conn = op.get_bind()
    # Remove employee_roles for seeded roles
    for role_name in ROLES_CONFIG:
        role_id = _gen_uuid(f"role:{role_name}")
        conn.execute(
            text("DELETE FROM employee_roles WHERE role_id = :role_id"),
            {"role_id": role_id},
        )
    # Remove role_permissions for seeded roles
    for role_name in ROLES_CONFIG:
        role_id = _gen_uuid(f"role:{role_name}")
        conn.execute(
            text("DELETE FROM role_permissions WHERE role_id = :role_id"),
            {"role_id": role_id},
        )
    # Remove seeded roles
    for role_name in ROLES_CONFIG:
        role_id = _gen_uuid(f"role:{role_name}")
        conn.execute(
            text("DELETE FROM roles WHERE id = :role_id"),
            {"role_id": role_id},
        )
    # Remove seeded permissions
    for code in PERMISSION_CODES:
        perm_id = _gen_uuid(f"perm:{code}")
        conn.execute(
            text("DELETE FROM permissions WHERE id = :perm_id"),
            {"perm_id": perm_id},
        )
