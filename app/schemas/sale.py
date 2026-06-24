from datetime import datetime
from pydantic import BaseModel, Field


class SaleLineBase(BaseModel):
    item_id: str | None = None
    item_name: str
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)
    discount_amount: float = Field(default=0, ge=0)


class SaleLineCreate(SaleLineBase):
    pass


class SaleLineUpdate(BaseModel):
    quantity: float | None = None
    unit_price: float | None = None
    discount_percent: float | None = None
    discount_amount: float | None = None


class SaleLineResponse(SaleLineBase):
    id: str
    sale_id: str
    cost_price: float
    line_total: float

    model_config = {"from_attributes": True}


class PaymentBase(BaseModel):
    payment_type: str
    amount: float = Field(gt=0)
    reference_number: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: str
    sale_id: str

    model_config = {"from_attributes": True}


class SaleBase(BaseModel):
    customer_id: str | None = None
    comment: str | None = None


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    customer_id: str | None = None
    comment: str | None = None
    discount_amount: float | None = None


class SaleResponse(SaleBase):
    id: str
    status: str
    employee_id: str
    subtotal: float
    tax_amount: float
    discount_amount: float
    total: float
    created_at: datetime
    completed_at: datetime | None = None
    suspended_at: datetime | None = None

    model_config = {"from_attributes": True}


class SaleDetailResponse(SaleResponse):
    lines: list[SaleLineResponse] = []
    payments: list[PaymentResponse] = []


class CartAddItemRequest(BaseModel):
    item_id: str | None = None
    item_name: str | None = None
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)


class CartUpdateItemRequest(BaseModel):
    line_id: str
    quantity: float | None = None
    discount_percent: float | None = None
    discount_amount: float | None = None


class CompleteSaleRequest(BaseModel):
    payments: list[PaymentCreate]
    customer_id: str | None = None
    comment: str | None = None