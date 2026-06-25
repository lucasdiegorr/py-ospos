import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import uuid

from app.main import app
from app.core.auth import get_current_user, get_db


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
        self._categories = {}
        self._expenses = {}
        self._cash_ups = {}

    def _get_table_data(self, table_name):
        if table_name == 'expense_categories':
            return list(self._categories.values())
        elif table_name == 'expenses':
            return list(self._expenses.values())
        elif table_name == 'cash_ups':
            return list(self._cash_ups.values())
        return []

    def _apply_where_conditions(self, data, query):
        from sqlalchemy import Select

        if not isinstance(query, Select):
            return data

        try:
            for clause in query._where_criteria:
                left = clause.left
                op = clause.operator
                right = clause.right

                col_name = left.key
                if hasattr(right, 'value'):
                    value = right.value
                else:
                    value = right

                if op.__name__ == 'eq':
                    data = [d for d in data if getattr(d, col_name, None) == value]
                elif op.__name__ == 'ne':
                    data = [d for d in data if getattr(d, col_name, None) != value]
                elif op.__name__ == 'is_':
                    if right.left is None:
                        data = [d for d in data if getattr(d, col_name, None) is None]
                    else:
                        data = [d for d in data if getattr(d, col_name, None) == right.right]
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

        if obj.__class__.__name__ == 'ExpenseCategory':
            self._categories[obj_id] = obj
        elif obj.__class__.__name__ == 'Expense':
            self._expenses[obj_id] = obj
        elif obj.__class__.__name__ == 'CashUp':
            self._cash_ups[obj_id] = obj

    async def flush(self):
        pass

    async def refresh(self, obj):
        obj_id = getattr(obj, 'id', None)
        if obj_id is None:
            return
        if obj.__class__.__name__ == 'ExpenseCategory':
            if obj_id in self._categories:
                stored = self._categories[obj_id]
                obj.created_at = stored.created_at
                obj.updated_at = stored.updated_at
        elif obj.__class__.__name__ == 'Expense':
            if obj_id in self._expenses:
                stored = self._expenses[obj_id]
                obj.created_at = stored.created_at
                obj.updated_at = stored.updated_at
        elif obj.__class__.__name__ == 'CashUp':
            if obj_id in self._cash_ups:
                stored = self._cash_ups[obj_id]
                obj.created_at = stored.created_at
                obj.updated_at = stored.updated_at

    async def execute(self, query):
        from sqlalchemy import Select

        mock_result = MagicMock()

        if isinstance(query, Select):
            table_name = None
            if query._from_objects:
                table_name = query._from_objects[0].name
            if not table_name and query._raw_columns:
                table_name = getattr(query._raw_columns[0], 'name', None)

            data = self._get_table_data(table_name)
            data = self._apply_where_conditions(data, query)

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
    async def mock_get_current_user():
        return MockEmployee()

    mock_session = MockDbSession()

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()