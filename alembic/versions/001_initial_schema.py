"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-06-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credit_notes",
        sa.Column("credit_note_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("invoice_id", sa.String(36), nullable=True),
        sa.Column("customer_id", sa.String(36), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(None, "credit_notes", ["credit_note_number"], unique=True)

    op.create_table(
        "customers",
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("first_name", sa.String(50), nullable=False),
        sa.Column("last_name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=True, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column("address_line_1", sa.String(255), nullable=True),
        sa.Column("address_line_2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(50), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("comments", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "employees",
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(50), nullable=False),
        sa.Column("last_name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=True, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(None, "employees", ["username"], unique=True)

    op.create_table(
        "expense_categories",
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "invoices",
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.String(36), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("amount_paid", sa.Float(), nullable=False),
        sa.Column("balance_due", sa.Float(), nullable=False),
        sa.Column("due_date", sa.String(36), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(None, "invoices", ["invoice_number"], unique=True)

    op.create_table(
        "item_categories",
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["item_categories.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "quotations",
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.String(36), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cash_ups",
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("expected_cash", sa.Float(), nullable=False),
        sa.Column("actual_cash", sa.Float(), nullable=False),
        sa.Column("variance", sa.Float(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "expenses",
        sa.Column("category_id", sa.String(36), nullable=True),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column("recurrence_pattern", sa.String(20), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "invoice_lines",
        sa.Column("invoice_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount_percent", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "invoice_payments",
        sa.Column("invoice_id", sa.String(36), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_date", sa.String(36), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "items",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sku", sa.String(50), nullable=True, unique=True),
        sa.Column("item_number", sa.String(50), nullable=True),
        sa.Column("category_id", sa.String(36), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("reorder_level", sa.Float(), nullable=False),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("is_service", sa.Boolean(), nullable=False),
        sa.Column("is_serialized", sa.Boolean(), nullable=False),
        sa.Column("tax_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["item_categories.id"], ondelete="SET NULL"),
    )
    op.create_index(None, "items", ["sku"], unique=True)

    op.create_table(
        "quotation_lines",
        sa.Column("quotation_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount_percent", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "sales",
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("customer_id", sa.String(36), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.String(36), nullable=True),
        sa.Column("suspended_at", sa.String(36), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "item_attributes",
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("attribute_name", sa.String(50), nullable=False),
        sa.Column("attribute_value", sa.String(255), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "item_barcodes",
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=False),
        sa.Column("format", sa.String(20), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "item_kits",
        sa.Column("kit_item_id", sa.String(36), nullable=False),
        sa.Column("component_item_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["kit_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_item_id"], ["items.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "payments",
        sa.Column("sale_id", sa.String(36), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "permissions",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(None, "permissions", ["code"], unique=True)

    op.create_table(
        "roles",
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(None, "roles", ["name"], unique=True)

    op.create_table(
        "employee_permissions",
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("permission_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "employee_roles",
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("role_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), nullable=False),
        sa.Column("permission_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "sale_lines",
        sa.Column("sale_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("discount_percent", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("sale_lines")
    op.drop_table("payments")
    op.drop_table("item_kits")
    op.drop_table("item_barcodes")
    op.drop_table("item_attributes")
    op.drop_table("sales")
    op.drop_table("quotation_lines")
    op.drop_table("items")
    op.drop_table("invoice_payments")
    op.drop_table("invoice_lines")
    op.drop_table("expenses")
    op.drop_table("cash_ups")
    op.drop_table("quotations")
    op.drop_table("item_categories")
    op.drop_table("invoices")
    op.drop_table("expense_categories")
    op.drop_table("employees")
    op.drop_table("customers")
    op.drop_table("credit_notes")
    op.drop_table("employee_roles")
    op.drop_table("employee_permissions")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
