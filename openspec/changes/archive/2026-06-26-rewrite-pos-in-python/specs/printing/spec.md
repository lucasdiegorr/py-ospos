## ADDED Requirements

### Requirement: Receipt printing
The system SHALL generate and print receipts for sales.

#### Scenario: Print receipt after sale
- **WHEN** sale is completed
- **THEN** receipt is generated with store info, items, totals, and payment info

#### Scenario: Reprint receipt
- **WHEN** user requests reprint of past receipt
- **THEN** receipt is regenerated from transaction data

### Requirement: Invoice printing
The system SHALL generate and print invoices.

#### Scenario: Print invoice
- **WHEN** user prints invoice
- **THEN** formatted invoice is generated with invoice number, items, and payment terms

#### Scenario: Email invoice
- **WHEN** user emails invoice to customer
- **THEN** invoice PDF is attached and sent to customer email

### Requirement: Quotation printing
The system SHALL generate and print quotations.

#### Scenario: Print quotation
- **WHEN** user prints quotation
- **THEN** formatted quotation is generated with validity period

### Requirement: Print formatting
The system SHALL support configurable print templates.

#### Scenario: Custom receipt header
- **WHEN** admin configures custom receipt header
- **THEN** receipt includes configured store name, logo, and contact info

#### Scenario: Thermal printer support
- **WHEN** receipt is printed to thermal printer
- **THEN** formatting is adjusted for 80mm paper width