## Purpose

Defines the product catalog for the beverage warehouse: product identity, categories, pricing, packaging (unit and pack), optional expiration, and how products are composed so the point of sale and stock can consume a single source of truth.

## ADDED Requirements

### Requirement: Product catalog entry
The system SHALL allow creating products with a name, an internal code (SKU), a category, a unit price, and a packaging definition.

#### Scenario: Create simple product
- **WHEN** a manager creates a product named "Água 500ml" with a price and category
- **THEN** the product is saved and becomes searchable in the point of sale

#### Scenario: Duplicate SKU rejected
- **WHEN** a manager attempts to create a product with a SKU already in use
- **THEN** the system rejects the creation with a duplicate-code error

### Requirement: Product categories
The system SHALL allow creating and managing product categories (e.g., beer, soft drink, water, groceries) and SHALL allow assigning a product to one category.

#### Scenario: Filter by category
- **WHEN** a user filters the catalog by the "cerveja" category
- **THEN** the system lists only products assigned to that category

### Requirement: Unit pricing
Every product SHALL have a base selling price for one base unit.

#### Scenario: Price set at creation
- **WHEN** a product is created with a base unit price
- **THEN** that price is used when the product is sold by unit

### Requirement: Packaging with unit and pack
The system SHALL support products sold either as a single base unit or as a pack containing a fixed quantity of base units (e.g., a 12-pack), each with its own selling price. Sales may reference either representation.

#### Scenario: Product with pack definition
- **WHEN** a manager defines a product with a base unit "Cerveja 600ml" priced at R$ 8.00 and a 12-pack priced at R$ 88.00
- **THEN** the point of sale offers both the unit and the pack as selectable items

#### Scenario: Pack quantity must be integer and positive
- **WHEN** a manager defines a pack with zero or fractional unit quantity
- **THEN** the system rejects the pack definition

### Requirement: Optional expiration
Products SHALL optionally carry an expiration date. Products without an expiration date are allowed, and only dated products participate in expiration tracking.

#### Scenario: Product with expiration
- **WHEN** a product is created or restocked with an expiration date
- **THEN** the system stores it and includes it in expiration alerts

#### Scenario: Product without expiration
- **WHEN** a product is created without an expiration date
- **THEN** the product is saved normally and excluded from expiration tracking

### Requirement: Edit product
The system SHALL allow managers and admins to edit a product's name, price, category, packaging, and expiration attributes. Changes apply to future sales.

#### Scenario: Price update
- **WHEN** a manager changes a product's unit price
- **THEN** new sales use the updated price while past sales keep their recorded price

### Requirement: Product search and list
The system SHALL allow searching products by name or SKU, with the result showing current stock availability and price.

#### Scenario: Search by name
- **WHEN** an attendant searches for "cerveja" in the point of sale
- **THEN** the system shows matching products with price and available quantity
