## Purpose

Tracks stock for the beverage warehouse: manual product entries, outflow driven by sales, low-stock and expiration alerts, and automatic breaking of packs into units when a unit is sold but only whole packs are available.

## ADDED Requirements

### Requirement: Manual stock entry
The system SHALL allow a manager or admin to record a manual stock entry for a product, specifying quantity and optionally an expiration date, with no fiscal document required.

#### Scenario: Manual entry adds units
- **WHEN** a manager records an entry of 24 units of a product
- **THEN** the product's available quantity increases by 24 and the movement is logged

#### Scenario: Entry with expiration
- **WHEN** a manager records an entry specifying an expiration date
- **THEN** the received units carry that expiration date and participate in expiration tracking

### Requirement: Stock outflow on sale
The system SHALL decrement stock by the base-unit quantity whenever a sale item is completed, whether sold as unit or pack.

#### Scenario: Selling a unit
- **WHEN** a sale containing 1 unit of a product is completed
- **THEN** the product's available quantity decreases by 1

#### Scenario: Selling a pack
- **WHEN** a sale containing 1 pack of a 12-unit product is completed
- **THEN** the product's available quantity decreases by 12

### Requirement: Automatic pack break
When a sale requires more units than are available as loose units but whole packs are in stock, the system SHALL automatically break one or more packs: converting a pack into its constituent units so the requested units can be sold.

#### Scenario: Break a pack to sell a unit
- **WHEN** stock holds 10 whole packs and 0 loose units, and a sale of 1 unit is completed
- **THEN** the system breaks 1 pack (reducing pack count by 1 and adding its unit quantity to loose stock) and then sells 1 unit

#### Scenario: Insufficient total stock
- **WHEN** the sum of loose units plus pack units is below the requested quantity
- **THEN** the system refuses to complete the sale with an insufficient-stock error

### Requirement: Low-stock alert
The system SHALL flag products whose available quantity is at or below a configurable minimum threshold.

#### Scenario: Product below threshold
- **WHEN** a product's available quantity drops to or below its configured minimum
- **THEN** the product is flagged as low stock and appears in the low-stock report

### Requirement: Expiration alert
The system SHALL flag products with dated stock whose expiration is within a configurable window or already past.

#### Scenario: Expiring soon
- **WHEN** a product has units expiring within the configured alert window
- **THEN** the product appears in the expiring-stock report with the quantity and expiration date

#### Scenario: Expired stock
- **WHEN** a product has units whose expiration date has passed
- **THEN** the system marks those units as expired and flags the product

### Requirement: Stock adjustment
The system SHALL allow a manager or admin to perform a manual adjustment (correction) of stock quantity, recorded with a reason.

#### Scenario: Correction with reason
- **WHEN** a manager adjusts a product's quantity down by 2 citing a breakage
- **THEN** the stock is updated and the adjustment is logged with the reason

### Requirement: Inventory movement log
The system SHALL keep a chronological log of every stock movement (entry, sale outflow, break, adjustment) with product, quantity delta, timestamp, and actor.

#### Scenario: Movement history visible
- **WHEN** a manager views a product's movement history
- **THEN** the system shows all movements in chronological order with quantity deltas and actors

### Requirement: Stock query
The system SHALL report a product's current available quantity as the sum of loose units and pack units, expressed in base units.

#### Scenario: Stock shown in base units
- **WHEN** a user views stock for a product with 5 loose units and 2 packs of 12
- **THEN** the system shows total available quantity of 29 base units
