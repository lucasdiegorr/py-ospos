## Purpose

Defines the point-of-sale (PDV) flow for the beverage warehouse: building a cart of unit or pack items, applying a payment method (cash, card, PIX, or fiado), optionally attaching a delivery, and completing the sale — including when the device is offline.

## ADDED Requirements

### Requirement: Build a sale cart
The system SHALL allow an attendant to add products to a cart, selecting quantity and, for products with a pack definition, choosing between unit and pack representation.

#### Scenario: Add unit to cart
- **WHEN** an attendant selects 2 units of "Cerveja 600ml"
- **THEN** the cart shows 2 units with a line total of 2 × unit price

#### Scenario: Add pack to cart
- **WHEN** an attendant selects 1 pack of "Cerveja 600ml 12-pack"
- **THEN** the cart shows the pack with its pack price and a line total equal to the pack price

### Requirement: Cart total
The system SHALL compute the cart total as the sum of line totals before payment.

#### Scenario: Total reflects lines
- **WHEN** a cart contains two lines totaling R$ 20.00 and R$ 30.00
- **THEN** the cart total is R$ 50.00

### Requirement: Complete sale with payment
The system SHALL complete a sale only when the sum of recorded payments equals the cart total, and SHALL record the sale with its items and payments atomically.

#### Scenario: Full payment completes sale
- **WHEN** the attendant records payments summing to the cart total
- **THEN** the sale is completed, stock is decremented, and a sale record is created

#### Scenario: Partial payment blocked
- **WHEN** the attendant records payments summing to less than the cart total
- **THEN** the system blocks completion and indicates the remaining amount

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
