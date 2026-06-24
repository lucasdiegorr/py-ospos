from datetime import datetime
from pydantic import BaseModel, Field


class QuotationLineBase(BaseModel):
    item_id: str | None = None
    item_name: str
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)
    discount_amount: float = Field(default=0, ge=0)


class QuotationLineCreate(QuotationLineBase):
    pass


class QuotationLineUpdate(BaseModel):
    quantity: float | None = None
    unit_price: float | None = None
    discount_percent: float | None = None
    discount_amount: float | None = None


class QuotationLineResponse(QuotationLineBase):
    id: str
    quotation_id: str
    line_total: float

    model_config = {"from_attributes": True}


class QuotationBase(BaseModel):
    customer_id: str | None = None
    comment: str | None = None
    expires_at: str | None = None


class QuotationCreate(QuotationBase):
    pass


class QuotationUpdate(BaseModel):
    customer_id: str | None = None
    comment: str | None = None
    discount_amount: float | None = None


class QuotationResponse(QuotationBase):
    id: str
    status: str
    employee_id: str
    subtotal: float
    discount_amount: float
    total: float
    created_at: datetime

    model_config = {"from_attributes": True}


class QuotationDetailResponse(QuotationResponse):
    lines: list[QuotationLineResponse] = []