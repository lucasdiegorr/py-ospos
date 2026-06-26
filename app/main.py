from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from app.api.v1.auth import router as auth_router
from app.api.v1.customer import router as customer_router
from app.api.v1.employee import router as employee_router
from app.api.v1.expense import router as expense_router
from app.api.v1.invoice import router as invoice_router
from app.api.v1.item import router as item_router
from app.api.v1.quotation import router as quotation_router
from app.api.v1.sale import router as sale_router
from app.core.exceptions import integrity_error_handler

app = FastAPI(
    title="py-ospos",
    description="Python rewrite of Open Source Point of Sale",
    version="0.1.0",
    exception_handlers={
        IntegrityError: integrity_error_handler,
    },
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(customer_router, prefix="/api/v1")
app.include_router(employee_router, prefix="/api/v1")
app.include_router(expense_router, prefix="/api/v1")
app.include_router(invoice_router, prefix="/api/v1")
app.include_router(item_router, prefix="/api/v1")
app.include_router(quotation_router, prefix="/api/v1")
app.include_router(sale_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "py-ospos API"}