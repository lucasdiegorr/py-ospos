import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock
from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean

from app.main import app
from app.core.auth import get_current_user, get_db

TABLE_TO_MODEL = {
    'expense_categories': 'ExpenseCategory',
    'expenses': 'Expense',
    'cash_ups': 'CashUp',
    'customers': 'Customer',
    'employees': 'Employee',
    'items': 'Item',
    'item_categories': 'ItemCategory',
    'item_attributes': 'ItemAttribute',
    'item_barcodes': 'ItemBarcode',
    'item_kits': 'ItemKit',
    'invoices': 'Invoice',
    'invoice_lines': 'InvoiceLine',
    'invoice_payments': 'InvoicePayment',
    'credit_notes': 'CreditNote',
    'quotations': 'Quotation',
    'quotation_lines': 'QuotationLine',
    'sales': 'Sale',
    'sale_lines': 'SaleLine',
    'payments': 'Payment',
}


class MockEmployee:
    id = "test-user-id"
    username = "testuser"
    first_name = "Test"
    last_name = "User"
    email = "test@example.com"
    is_admin = True
    is_active = True


class MockResult:
    def __init__(self, data):
        self._data = data

    def scalars(self):
        return self

    def all(self):
        return self._data

    def one_or_none(self):
        return self._data[0] if self._data else None

    def scalar_one_or_none(self):
        return self._data[0] if self._data else None

    def scalar(self):
        return self._data[0] if self._data else None


class MockDbSession:
    def __init__(self):
        self._data: dict[str, dict[str, object]] = {}

    def _get_store(self, table_name: str) -> dict[str, object]:
        if table_name not in self._data:
            self._data[table_name] = {}
        return self._data[table_name]

    def _get_table_data(self, table_name: str) -> list:
        if table_name in ('expense_categories', 'customers', 'employees', 'items', 'item_categories',
                          'invoices', 'quotations', 'sales'):
            return list(self._get_store(table_name).values())
        return list(self._get_store(table_name).values())

    def _apply_where_conditions(self, data, query, primary_table=None):
        from sqlalchemy import Select

        if not isinstance(query, Select):
            return data

        try:
            for clause in query._where_criteria:
                left = clause.left
                op = clause.operator
                right = clause.right

                col_name = left.key

                if primary_table is not None and hasattr(left, 'table'):
                    if left.table.name != primary_table:
                        continue

                if hasattr(right, 'value'):
                    value = right.value
                elif hasattr(right, 'right'):
                    value = right.right
                elif hasattr(right, 'clause_element'):
                    value = right.clause_element()
                else:
                    value = right

                if op.__name__ == 'eq':
                    data = [d for d in data if getattr(d, col_name, None) == value]
                elif op.__name__ == 'ne':
                    data = [d for d in data if getattr(d, col_name, None) != value]
                elif op.__name__ == 'lt':
                    data = [d for d in data if getattr(d, col_name, None) is not None and getattr(d, col_name) < value]
                elif op.__name__ == 'le':
                    data = [d for d in data if getattr(d, col_name, None) is not None and getattr(d, col_name) <= value]
                elif op.__name__ == 'gt':
                    data = [d for d in data if getattr(d, col_name, None) is not None and getattr(d, col_name) > value]
                elif op.__name__ == 'ge':
                    data = [d for d in data if getattr(d, col_name, None) is not None and getattr(d, col_name) >= value]
                elif op.__name__ == 'in_op':
                    data = [d for d in data if getattr(d, col_name, None) in value]
        except Exception:
            pass

        return data

    def add(self, obj):
        obj_id = getattr(obj, 'id', None)
        if obj_id is None:
            obj_id = str(uuid.uuid4())
            obj.id = obj_id
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now(timezone.utc)

        table = getattr(obj, '__table__', None)
        if table is not None:
            for col in table.columns:
                if col.default is not None and col.default.is_scalar:
                    if getattr(obj, col.name, None) is None:
                        setattr(obj, col.name, col.default.arg)

        table_name = getattr(table, 'name', None)
        if table_name:
            store = self._get_store(table_name)
            store[obj_id] = obj

    async def delete(self, obj):
        table_name = getattr(getattr(obj, '__table__', None), 'name', None)
        if table_name:
            obj_id = getattr(obj, 'id', None)
            store = self._get_store(table_name)
            if obj_id in store:
                del store[obj_id]

    async def flush(self):
        pass

    async def refresh(self, obj):
        obj_id = getattr(obj, 'id', None)
        if obj_id is None:
            return
        table_name = getattr(getattr(obj, '__table__', None), 'name', None)
        if table_name:
            store = self._get_store(table_name)
            if obj_id in store:
                stored = store[obj_id]
                for attr_name in ('created_at', 'updated_at', 'suspended_at', 'completed_at', 'amount_paid',
                                  'balance_due', 'total', 'subtotal', 'status', 'line_total'):
                    if hasattr(stored, attr_name):
                        setattr(obj, attr_name, getattr(stored, attr_name))

    async def execute(self, query):
        from sqlalchemy import Select

        mock_result = MagicMock()

        if isinstance(query, Select):
            table_name = None
            if query._from_objects:
                table_name = query._from_objects[0].name
            if not table_name and query._raw_columns:
                raw_col = query._raw_columns[0]
                table_name = getattr(raw_col, 'name', None)
                if table_name is None and hasattr(raw_col, 'table'):
                    table_name = raw_col.table.name
                if table_name is None:
                    table_name = getattr(raw_col, '__tablename__', None)

            data = self._get_table_data(table_name)
            data = self._apply_where_conditions(data, query, table_name)

            mock_result.scalars.return_value = MockResult(data)
            mock_result.scalar_one_or_none.return_value = data[0] if len(data) == 1 else None
            mock_result.one_or_none.return_value = data[0] if data else None
            mock_result.scalar.return_value = data[0] if data else None
            mock_result.all.return_value = data
        else:
            mock_result.scalars.return_value = MockResult([])
            mock_result.scalar_one_or_none.return_value = None
            mock_result.one_or_none.return_value = None
            mock_result.scalar.return_value = None
            mock_result.all.return_value = []

        return mock_result


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    from app.models.employee import Employee

    async def mock_get_current_user():
        return MockEmployee()

    mock_session = MockDbSession()
    me = MockEmployee()
    emp = Employee(
        id=me.id,
        username=me.username,
        first_name=me.first_name,
        last_name=me.last_name,
        email=me.email,
        is_active=me.is_active,
    )
    mock_session.add(emp)

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()