## MODIFIED Requirements

### Requirement: Build a sale cart
The system SHALL allow an attendant to add products to a cart, selecting quantity and, for products with a pack definition, choosing between unit and pack representation. The PDV screen SHALL present the product catalog as a searchable grid of product cards (each card showing name, current price, and unit/pack toggle when applicable) alongside a persistent cart panel showing line items, line totals, and cart-level controls.

#### Scenario: Add unit to cart
- **WHEN** an attendant selects 2 units of "Cerveja 600ml" from a product card
- **THEN** the cart panel shows 2 units with a line total of 2 × unit price

#### Scenario: Add pack to cart
- **WHEN** an attendant selects 1 pack of "Cerveja 600ml 12-pack" from a product card
- **THEN** the cart shows the pack with its pack price and a line total equal to the pack price

### Requirement: Complete sale with payment
The system SHALL complete a sale only when the sum of recorded payments equals the cart total, and SHALL record the sale with its items and payments atomically. The payment flow SHALL be presented in a dedicated panel listing each recorded payment (method + amount) and offering controls to add a new payment, remove a payment, and finalize the sale. The remaining-amount indicator MUST be visible at all times.

#### Scenario: Full payment completes sale
- **WHEN** the attendant records payments summing to the cart total via the payment panel
- **THEN** the sale is completed, stock is decremented, and a sale record is created; a receipt card is displayed with the completed sale details

#### Scenario: Partial payment blocked
- **WHEN** the recorded payments sum to less than the cart total
- **THEN** the finalize button is disabled and the remaining-amount indicator shows the outstanding value

## ADDED Requirements

### Requirement: PDV product catalog grid
The PDV screen MUST present the product catalog as a responsive grid of product cards, each with a name, the unit price (and pack price when a pack is defined), and an "add to cart" affordance. The grid MUST be searchable by product name and MUST reflect the active theme (light/dark).

#### Scenario: Catalog search filters grid
- **WHEN** the attendant types in the catalog search field
- **THEN** the grid shows only products whose name contains the search term (case-insensitive)

### Requirement: PDV cart panel layout
The PDV screen MUST present the cart as a dedicated panel distinct from the catalog grid, showing each line with quantity controls, line total, and a remove control. The cart panel MUST show the running total at all times.

#### Scenario: Remove line from cart
- **WHEN** the attendant removes a line from the cart
- **THEN** the cart total recalculates and the line no longer appears

### Requirement: PDV receipt card
After a sale is completed, the PDV screen MUST display a receipt card containing items, totals, payment method(s), and timestamp. The receipt content MUST remain in monospaced text suitable for a Bluetooth thermal printer.

#### Scenario: Receipt displayed after completion
- **WHEN** a sale is completed
- **THEN** the PDV screen displays a receipt card with the printed content and offers a "print" action
