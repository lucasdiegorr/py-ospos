# sales Specification

## Purpose
Defines the point-of-sale (PDV) flow for the beverage warehouse: building a cart of unit or pack items, applying a payment method (cash, card, PIX, or fiado), optionally attaching a delivery, and completing the sale — including when the device is offline.

## Requirements

### Requirement: Build a sale cart
The system SHALL allow an attendant to add products to a cart, selecting quantity and, for products with a pack definition, choosing between unit and pack representation. The PDV screen SHALL present the product catalog as a searchable grid of product cards (each card showing name, current price, and unit/pack toggle when applicable) alongside a persistent cart panel showing line items, line totals, and cart-level controls.

#### Scenario: Add unit to cart
- **WHEN** an attendant selects 2 units of "Cerveja 600ml" from a product card
- **THEN** the cart panel shows 2 units with a line total of 2 × unit price

#### Scenario: Add pack to cart
- **WHEN** an attendant selects 1 pack of "Cerveja 600ml 12-pack" from a product card
- **THEN** the cart shows the pack with its pack price and a line total equal to the pack price

### Requirement: Cart total
The system SHALL compute the cart total as the sum of line totals before payment.

#### Scenario: Total reflects lines
- **WHEN** a cart contains two lines totaling R$ 20.00 and R$ 30.00
- **THEN** the cart total is R$ 50.00

### Requirement: Complete sale with payment
The system SHALL complete a sale only when the sum of recorded payments equals the cart total, and SHALL record the sale with its items and payments atomically. The payment flow SHALL be presented in a dedicated panel listing each recorded payment (method + amount) and offering controls to add a new payment, remove a payment, and finalize the sale. The remaining-amount indicator MUST be visible at all times.

#### Scenario: Full payment completes sale
- **WHEN** the attendant records payments summing to the cart total via the payment panel
- **THEN** the sale is completed, stock is decremented, and a sale record is created; a receipt card is displayed with the completed sale details

#### Scenario: Partial payment blocked
- **WHEN** the recorded payments sum to less than the cart total
- **THEN** the finalize button is disabled and the remaining-amount indicator shows the outstanding value

### Requirement: Fiado payment flow
When a sale is paid by fiado, the system SHALL require a registered customer and SHALL validate the outstanding balance against the customer's credit limit.

#### Scenario: Fiado within limit
- **WHEN** a customer's balance plus the sale amount stays within their credit limit
- **THEN** the sale completes on fiado and the balance increases accordingly

#### Scenario: Fiado over limit
- **WHEN** a customer's balance plus the sale amount would exceed their credit limit
- **THEN** the system blocks the sale with a limit-exceeded error

### Requirement: Optional delivery on sale
The system SHALL allow attaching a delivery to a sale without charging freight, storing a possibly-partial address.

#### Scenario: Sale marked for delivery
- **WHEN** an attendant finalizes a sale and marks it for delivery with a partial address
- **THEN** the sale completes and a pending delivery record is created

### Requirement: Sale receipt
The system SHALL produce a printable/non-fiscal receipt for a completed sale with items, totals, payment method, and timestamp, printable on a Bluetooth thermal printer.

#### Scenario: Print receipt
- **WHEN** an attendant prints the receipt for a completed sale
- **THEN** a non-fiscal receipt with items, totals, payments, and timestamp is sent to the printer

### Requirement: Offline sale completion
When the device is offline, the system SHALL allow sale completion to proceed and SHALL queue the sale for synchronization according to the sync capability.

#### Scenario: Offline sale queued
- **WHEN** the device is offline and an attendant completes a sale
- **THEN** the sale is finalized locally, stock is decremented locally, and the sale is queued with pending-sync status

#### Scenario: Offline sale syncs later
- **WHEN** connectivity returns
- **THEN** the queued sale is synchronized to the server as defined by the sync capability

### Requirement: Sale search and detail
The system SHALL allow searching completed sales by date, customer, or id, and viewing sale details including items, payments, delivery, and shift.

#### Scenario: View sale detail
- **WHEN** a user opens a completed sale
- **THEN** the system shows its items, payments, delivery (if any), shift, and timestamps

### Requirement: Cancel sale
The system SHALL allow a manager or admin to cancel a completed sale, restoring the items' stock and requiring a reason.

#### Scenario: Cancel restores stock
- **WHEN** a manager cancels a sale with a reason
- **THEN** the sale is marked cancelled, stock is restored, and fiado balances are reversed

#### Scenario: Attendant cannot cancel
- **WHEN** a user with role `attendant` attempts to cancel a sale
- **THEN** the system denies the operation

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
