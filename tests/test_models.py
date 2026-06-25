from datetime import datetime

from app.models.customer import Customer
from app.models.employee import Employee
from app.models.item import Item
from tests.conftest import MockDbSession


class TestCustomer:
    def test_full_name(self) -> None:
        customer = Customer(first_name="John", last_name="Doe")
        assert customer.full_name == "John Doe"

    def test_full_name_with_middle_initial_in_first(self) -> None:
        customer = Customer(first_name="Mary Jane", last_name="Watson")
        assert customer.full_name == "Mary Jane Watson"

    def test_full_address_all_parts(self) -> None:
        customer = Customer(
            first_name="A",
            last_name="B",
            address_line_1="123 Main St",
            address_line_2="Apt 4B",
            city="Springfield",
            state="IL",
            postal_code="62701",
        )
        assert customer.full_address == "123 Main St, Apt 4B, Springfield, IL, 62701"

    def test_full_address_partial(self) -> None:
        customer = Customer(
            first_name="A",
            last_name="B",
            address_line_1="456 Oak Ave",
            city="Portland",
            state="OR",
        )
        assert customer.full_address == "456 Oak Ave, Portland, OR"

    def test_full_address_none(self) -> None:
        customer = Customer(first_name="A", last_name="B")
        assert customer.full_address is None

    def test_full_address_single_part(self) -> None:
        customer = Customer(first_name="A", last_name="B", city="Metropolis")
        assert customer.full_address == "Metropolis"


class TestEmployee:
    def test_full_name(self) -> None:
        employee = Employee(
            first_name="Jane",
            last_name="Smith",
            username="jsmith",
            password_hash="hash",
        )
        assert employee.full_name == "Jane Smith"

    def test_full_name_single_first(self) -> None:
        employee = Employee(
            first_name="Bob",
            last_name="Jones",
            username="bjones",
            password_hash="hash",
        )
        assert employee.full_name == "Bob Jones"


class TestItem:
    def test_is_below_reorder_level_true(self) -> None:
        item = Item(name="Widget", quantity=2, reorder_level=5)
        assert item.is_below_reorder_level is True

    def test_is_below_reorder_level_false(self) -> None:
        item = Item(name="Widget", quantity=10, reorder_level=5)
        assert item.is_below_reorder_level is False

    def test_is_below_reorder_level_equal(self) -> None:
        item = Item(name="Widget", quantity=5, reorder_level=5)
        assert item.is_below_reorder_level is False

    def test_is_below_reorder_level_zero_quantity(self) -> None:
        item = Item(name="Widget", quantity=0, reorder_level=5)
        assert item.is_below_reorder_level is True

    def test_is_below_reorder_level_zero_reorder(self) -> None:
        item = Item(name="Widget", quantity=5, reorder_level=0)
        assert item.is_below_reorder_level is False


class TestBaseModelAttributes:
    def test_id_is_generated(self) -> None:
        session = MockDbSession()
        customer = Customer(first_name="A", last_name="B")
        session.add(customer)
        assert isinstance(customer.id, str)
        assert len(customer.id) > 0

    def test_id_is_unique(self) -> None:
        session = MockDbSession()
        c1 = Customer(first_name="A", last_name="B")
        c2 = Customer(first_name="C", last_name="D")
        session.add(c1)
        session.add(c2)
        assert c1.id != c2.id

    def test_created_at_is_datetime(self) -> None:
        session = MockDbSession()
        customer = Customer(first_name="A", last_name="B")
        session.add(customer)
        assert isinstance(customer.created_at, datetime)

    def test_updated_at_is_datetime(self) -> None:
        session = MockDbSession()
        customer = Customer(first_name="A", last_name="B")
        session.add(customer)
        assert isinstance(customer.updated_at, datetime)

    def test_employee_has_base_attrs(self) -> None:
        session = MockDbSession()
        employee = Employee(
            first_name="X",
            last_name="Y",
            username="xy",
            password_hash="hash",
        )
        session.add(employee)
        assert isinstance(employee.id, str)
        assert isinstance(employee.created_at, datetime)
        assert isinstance(employee.updated_at, datetime)
