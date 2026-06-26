from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.item import Item, ItemAttribute, ItemBarcode, ItemCategory, ItemKit
from app.schemas.item import (
    CategoryCreate,
    CategoryResponse,
    ItemAttributeCreate,
    ItemAttributeResponse,
    ItemBarcodeCreate,
    ItemBarcodeResponse,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    KitComponentCreate,
    KitComponentResponse,
)

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> ItemCategory:
    category = ItemCategory(**category_data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[ItemCategory]:
    result = await db.execute(select(ItemCategory))
    return list(result.scalars().all())


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Item:
    item = Item(**item_data.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/", response_model=list[ItemResponse])
async def list_items(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    search: str | None = Query(None, description="Search by name, SKU, item_number"),
    category_id: str | None = None,
    is_service: bool | None = None,
    is_active: bool | None = None,
    below_reorder_level: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Item]:
    query = select(Item).where(Item.deleted == False)

    if is_active is not None:
        query = query.where(Item.is_active == is_active)

    if is_service is not None:
        query = query.where(Item.is_service == is_service)

    if category_id:
        query = query.where(Item.category_id == category_id)

    if below_reorder_level:
        query = query.where(Item.quantity < Item.reorder_level)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.name.ilike(search_term),
                Item.sku.ilike(search_term),
                Item.item_number.ilike(search_term),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    for item in items:
        item.__dict__['is_below_reorder_level'] = item.is_below_reorder_level

    return items


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Item:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    item_data: ItemUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Item:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete items",
        )

    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.deleted = True
    await db.flush()


@router.post("/{item_id}/attributes", response_model=ItemAttributeCreate, status_code=status.HTTP_201_CREATED)
async def add_item_attribute(
    item_id: str,
    attribute_data: ItemAttributeCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> ItemAttribute:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    attribute = ItemAttribute(
        item_id=item_id,
        attribute_name=attribute_data.attribute_name,
        attribute_value=attribute_data.attribute_value,
    )
    db.add(attribute)
    await db.flush()
    await db.refresh(attribute)
    return attribute


@router.post("/{item_id}/barcodes", response_model=ItemBarcodeCreate, status_code=status.HTTP_201_CREATED)
async def add_item_barcode(
    item_id: str,
    barcode_data: ItemBarcodeCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> ItemBarcode:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    barcode = ItemBarcode(
        item_id=item_id,
        barcode=barcode_data.barcode,
        format=barcode_data.format,
    )
    db.add(barcode)
    await db.flush()
    await db.refresh(barcode)
    return barcode


@router.get("/barcode/{barcode}", response_model=ItemResponse)
async def get_item_by_barcode(
    barcode: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Item:
    result = await db.execute(
        select(Item).join(ItemBarcode).where(ItemBarcode.barcode == barcode, Item.deleted == False)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return item


@router.post("/{item_id}/kits", response_model=KitComponentResponse, status_code=status.HTTP_201_CREATED)
async def add_kit_component(
    item_id: str,
    kit_data: KitComponentCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> ItemKit:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    component_result = await db.execute(select(Item).where(Item.id == kit_data.component_item_id))
    component = component_result.scalar_one_or_none()

    if component is None or component.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component item not found")

    kit = ItemKit(
        kit_item_id=item_id,
        component_item_id=kit_data.component_item_id,
        quantity=kit_data.quantity,
    )
    db.add(kit)
    await db.flush()
    await db.refresh(kit)
    return kit


@router.get("/{item_id}/kits", response_model=list[KitComponentResponse])
async def list_kit_components(
    item_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[ItemKit]:
    result = await db.execute(
        select(ItemKit).where(ItemKit.kit_item_id == item_id)
    )
    return list(result.scalars().all())


@router.delete("/kits/{kit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_kit_component(
    kit_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    result = await db.execute(select(ItemKit).where(ItemKit.id == kit_id))
    kit = result.scalar_one_or_none()

    if kit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kit component not found")

    await db.delete(kit)
    await db.flush()