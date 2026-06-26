## ADDED Requirements

### Requirement: Create quotation
The system SHALL allow creating price quotations for customers.

#### Scenario: Create quotation with line items
- **WHEN** user creates quotation with items, quantities, and prices
- **THEN** quotation is created with status=draft and expiration date

#### Scenario: Email quotation to customer
- **WHEN** user sends quotation via email
- **THEN** quotation is emailed to customer with PDF attachment

### Requirement: Quotation validity
The system SHALL enforce quotation expiration.

#### Scenario: Expired quotation warning
- **WHEN** user attempts to convert expired quotation
- **THEN** system warns user and requires confirmation

#### Scenario: Automatic expiration
- **WHEN** quotation exceeds validity period
- **THEN** quotation status changes to expired

### Requirement: Convert quotation to sale
The system SHALL allow converting quotations to sales.

#### Scenario: Convert to sale
- **WHEN** user converts quotation to sale
- **THEN** sale is created with quotation items and prices locked

#### Scenario: Convert to invoice
- **WHEN** user converts quotation to invoice
- **THEN** invoice is created with quotation line items

### Requirement: Quotation pricing
The system SHALL allow custom pricing on quotations.

#### Scenario: Override item price on quotation
- **WHEN** user sets custom price on quotation line item
- **THEN** custom price is used instead of item default price

#### Scenario: Apply discount to quotation
- **WHEN** user applies discount to entire quotation
- **THEN** discount is calculated on subtotal