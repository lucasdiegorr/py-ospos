from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ItemCategory(BaseModel):
    __tablename__ = "item_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("item_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    items: Mapped[list["Item"]] = relationship("Item", back_populates="category")


class Item(BaseModel):
    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    item_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("item_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    quantity: Mapped[float] = mapped_column(default=0)
    reorder_level: Mapped[float] = mapped_column(default=0)

    cost_price: Mapped[float] = mapped_column(default=0)
    unit_price: Mapped[float] = mapped_column(default=0)

    is_service: Mapped[bool] = mapped_column(default=False)
    is_serialized: Mapped[bool] = mapped_column(default=False)

    tax_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    deleted: Mapped[bool] = mapped_column(default=False)

    category: Mapped[ItemCategory | None] = relationship("ItemCategory", back_populates="items")

    @property
    def is_below_reorder_level(self) -> bool:
        return self.quantity < self.reorder_level


class ItemAttribute(BaseModel):
    __tablename__ = "item_attributes"

    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("items.id", ondelete="CASCADE"))
    attribute_name: Mapped[str] = mapped_column(String(50))
    attribute_value: Mapped[str] = mapped_column(String(255))


class ItemKit(BaseModel):
    __tablename__ = "item_kits"

    kit_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("items.id", ondelete="CASCADE"))
    component_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("items.id", ondelete="CASCADE"))
    quantity: Mapped[float] = mapped_column(default=1)


class ItemBarcode(BaseModel):
    __tablename__ = "item_barcodes"

    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("items.id", ondelete="CASCADE"))
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)