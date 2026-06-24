from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    parent_id: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: str

    model_config = {"from_attributes": True}


class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sku: str | None = None
    item_number: str | None = None
    category_id: str | None = None
    quantity: float = 0
    reorder_level: float = 0
    cost_price: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)
    is_service: bool = False
    is_serialized: bool = False
    tax_id: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: str | None = None
    quantity: float | None = None
    reorder_level: float | None = None
    cost_price: float | None = None
    unit_price: float | None = None
    is_service: bool | None = None
    is_serialized: bool | None = None
    tax_id: str | None = None


class ItemResponse(ItemBase):
    id: str
    is_active: bool
    is_below_reorder_level: bool | None = None

    model_config = {"from_attributes": True}


class ItemAttributeCreate(BaseModel):
    attribute_name: str
    attribute_value: str


class ItemAttributeResponse(BaseModel):
    id: str
    item_id: str
    attribute_name: str
    attribute_value: str

    model_config = {"from_attributes": True}


class ItemBarcodeCreate(BaseModel):
    barcode: str
    format: str | None = None


class ItemBarcodeResponse(BaseModel):
    id: str
    item_id: str
    barcode: str
    format: str | None

    model_config = {"from_attributes": True}


class KitComponentCreate(BaseModel):
    component_item_id: str
    quantity: float = Field(default=1, gt=0)


class KitComponentResponse(BaseModel):
    id: str
    kit_item_id: str
    component_item_id: str
    quantity: float

    model_config = {"from_attributes": True}