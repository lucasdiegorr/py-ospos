"""ORM models for the py-ospos domain.

Importing this module registers all models on ``app.db.Base.metadata`` so
Alembic autogenerate and ``create_all`` see the full schema. Capabilities
import their models from here (or from their own module).
"""

from app.models.cash_register import CashMovement, Shift
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.inventory import StockBatch, StockMovement
from app.models.payment import PaymentMethod
from app.models.product import Category, Product
from app.models.sales import Payment, Sale, SaleItem
from app.models.sync import IdempotencyRecord, OutboxEntry
from app.models.user import RefreshToken, User

__all__ = [
    "CashMovement",
    "Category",
    "Customer",
    "Delivery",
    "IdempotencyRecord",
    "OutboxEntry",
    "Payment",
    "PaymentMethod",
    "Product",
    "RefreshToken",
    "Sale",
    "SaleItem",
    "Shift",
    "StockBatch",
    "StockMovement",
    "User",
]
