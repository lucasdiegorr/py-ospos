from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.customer import router as customer_router
from app.api.v1.employee import router as employee_router
from app.api.v1.item import router as item_router
from app.api.v1.quotation import router as quotation_router
from app.api.v1.sale import router as sale_router

app = FastAPI(
    title="py-ospos",
    description="Python rewrite of Open Source Point of Sale",
    version="0.1.0",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(customer_router, prefix="/api/v1")
app.include_router(employee_router, prefix="/api/v1")
app.include_router(item_router, prefix="/api/v1")
app.include_router(quotation_router, prefix="/api/v1")
app.include_router(sale_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "py-ospos API"}