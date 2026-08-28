## Purpose

Defines the payment methods available in the system — cash, card, PIX, and fiado — how methods are registered and enabled, and how a sale records one or more payments against those methods.

## ADDED Requirements

### Requirement: Supported payment methods
The system SHALL support the payment methods cash, card, PIX, and fiado. All four SHALL be available in the point of sale by default.

#### Scenario: Methods offered at checkout
- **WHEN** an attendant finalizes a sale
- **THEN** the system offers cash, card, PIX, and fiado as selectable payment methods

#### Scenario: Fiado requires customer
- **WHEN** fiado is selected as the payment method without a customer chosen
- **THEN** the system prompts for a customer and blocks completion until one is selected

### Requirement: Payment method registry
The system SHALL maintain a registry of enabled payment methods where an admin can enable, disable, and configure each method.

#### Scenario: Disable a method
- **WHEN** an admin disables the fiado method
- **THEN** fiado is no longer offered at checkout until re-enabled

### Requirement: Record payment on a sale
A sale SHALL record each payment with method, amount, and for card payments, the card operator and number of installments.

#### Scenario: Single cash payment
- **WHEN** a sale of R$ 50.00 is paid fully in cash
- **THEN** the system records a single payment of R$ 50.00 with method cash

#### Scenario: Split payment
- **WHEN** a sale of R$ 50.00 is paid with R$ 30.00 cash and R$ 20.00 PIX
- **THEN** the system records two payments whose sum equals the sale total

#### Scenario: Card installment
- **WHEN** a sale is paid by card in 3 installments
- **THEN** the system records the operator and the installment count

### Requirement: Fiado payment linkage
A fiado payment SHALL be linked to a customer and increase that customer's outstanding balance by the fiado amount, subject to the customer's fiado profile.

#### Scenario: Fiado adds to balance
- **WHEN** a customer with a credit limit buys R$ 100.00 on fiado
- **THEN** the customer's outstanding balance increases by R$ 100.00, validated against the credit limit

#### Scenario: Limit exceeded
- **WHEN** a fiado payment would push the customer's outstanding balance above the configured credit limit
- **THEN** the system refuses the payment with a limit-exceeded error

### Requirement: PIX without integration
The system SHALL record PIX as a payment method without requiring a payment gateway integration; the attendant registers the transaction and confirms it as paid.

#### Scenario: PIX registered manually
- **WHEN** an attendant selects PIX and confirms receipt of a PIX payment
- **THEN** the payment is recorded as received and the sale completes

### Requirement: Payment totals per shift
The system SHALL report the total amount collected per payment method within a cash shift, to support shift closing.

#### Scenario: Shift totals by method
- **WHEN** a shift closes
- **THEN** the closing summary shows totals per payment method for sales in that shift
