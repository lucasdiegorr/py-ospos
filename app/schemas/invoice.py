from datetime import datetime
from pydantic import BaseModel, Field


class InvoiceLineBase(BaseModel):
    item_id: str | None = None
    item_name: str
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)
    discount_amount: float = Field(default=0, ge=0)


class InvoiceLineCreate(InvoiceLineBase):
    pass


class InvoiceLineResponse(InvoiceLineBase):
    id: str
    invoice_id: str
    line_total: float

    model_config = {"from_attributes": True}


class InvoicePaymentBase(BaseModel):
    payment_type: str
    amount: float = Field(gt=0)
    payment_date: str | None = None
    reference_number: str | None = None


class InvoicePaymentCreate(InvoicePaymentBase):
    pass


class InvoicePaymentResponse(InvoicePaymentBase):
    id: str
    invoice_id: str

    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    customer_id: str | None = None
    due_date: str | None = None
    comment: str | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    customer_id: str | None = None
    due_date: str | None = None
    comment: str | None = None
    discount_amount: float | None = None


class InvoiceResponse(InvoiceBase):
    id: str
    invoice_number: str
    status: str
    employee_id: str
    subtotal: float
    tax_amount: float
    discount_amount: float
    total: float
    amount_paid: float
    balance_due: float
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetailResponse(InvoiceResponse):
    lines: list[InvoiceLineResponse] = []
    payments: list[InvoicePaymentResponse] = []


class CreditNoteBase(BaseModel):
    invoice_id: str | None = None
    customer_id: str | None = None
    reason: str | None = None


class CreditNoteCreate(CreditNoteBase):
    amount: float = Field(gt=0)


class CreditNoteResponse(CreditNoteBase):
    id: str
    credit_note_number: str
    status: str
    amount: float
    balance: float

    model_config = {"from_attributes": True}