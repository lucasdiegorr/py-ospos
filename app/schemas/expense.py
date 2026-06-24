from pydantic import BaseModel, Field


class ExpenseCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryResponse(ExpenseCategoryBase):
    id: str

    model_config = {"from_attributes": True}


class ExpenseBase(BaseModel):
    category_id: str | None = None
    amount: float = Field(gt=0)
    description: str | None = None
    reference_number: str | None = None


class ExpenseCreate(ExpenseBase):
    is_recurring: bool = False
    recurrence_pattern: str | None = None


class ExpenseUpdate(BaseModel):
    category_id: str | None = None
    amount: float | None = None
    description: str | None = None


class ExpenseResponse(ExpenseBase):
    id: str
    employee_id: str
    is_recurring: bool
    recurrence_pattern: str | None = None

    model_config = {"from_attributes": True}


class CashUpBase(BaseModel):
    expected_cash: float = Field(default=0)
    actual_cash: float = Field(default=0)
    note: str | None = None


class CashUpCreate(CashUpBase):
    pass


class CashUpResponse(CashUpBase):
    id: str
    employee_id: str
    variance: float

    model_config = {"from_attributes": True}