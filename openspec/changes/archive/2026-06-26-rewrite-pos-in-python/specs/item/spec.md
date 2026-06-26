## ADDED Requirements

### Requirement: Item creation
The system SHALL allow creation of items with name, sku, price, and cost.

#### Scenario: Create item with all fields
- **WHEN** user submits item data with name, sku, price, cost, and category
- **THEN** item record is created and returned with generated ID

#### Scenario: Create item with auto-generated SKU
- **WHEN** user creates item without specifying SKU
- **THEN** system generates unique SKU automatically

#### Scenario: Duplicate SKU rejection
- **WHEN** user attempts to create item with existing SKU
- **THEN** system returns validation error

### Requirement: Item stock tracking
The system SHALL track inventory quantity for each item.

#### Scenario: Check item quantity
- **WHEN** user queries item stock level
- **THEN** system returns current quantity and reorder threshold

#### Scenario: Low stock alert
- **WHEN** item quantity falls below reorder threshold
- **THEN** item is flagged for reorder

### Requirement: Item categories
The system SHALL support hierarchical item categories.

#### Scenario: Create category hierarchy
- **WHEN** user creates category with parent category
- **THEN** category is linked and retrievable as nested structure

#### Scenario: Items in category
- **WHEN** user queries items in category
- **THEN** items from subcategories are optionally included based on parameter

### Requirement: Item attributes
The system SHALL support extensible attributes for items.

#### Scenario: Add custom attribute to item
- **WHEN** user adds custom attribute (e.g., size, color) to item
- **THEN** attribute is stored and returned with item data

#### Scenario: Filter items by attribute
- **WHEN** user searches items by attribute value
- **THEN** system returns matching items

### Requirement: Item kits
The system SHALL support item kits (bundles) containing multiple items.

#### Scenario: Create item kit
- **WHEN** user creates kit with multiple items and quantities
- **THEN** kit is created with calculated total cost and price

#### Scenario: Sell item kit
- **WHEN** kit is sold
- **THEN** component item quantities are decremented accordingly

### Requirement: Item barcode association
The system SHALL associate barcodes with items for scanning.

#### Scenario: Assign barcode to item
- **WHEN** user assigns barcode to item
- **THEN** barcode is stored and item is searchable by barcode

#### Scenario: Multiple barcodes per item
- **WHEN** item has multiple barcode types (UPC, EAN, internal)
- **THEN** all barcodes are associated with the same item