## ADDED Requirements

### Requirement: Create invoice
The system SHALL allow creating invoices from sales or quotations.

#### Scenario: Create invoice from sale
- **WHEN** user converts completed sale to invoice
- **THEN** invoice is created with invoice number, items, and totals

#### Scenario: Create invoice from quotation
- **WHEN** user converts quotation to invoice
- **THEN** invoice inherits line items from quotation

### Requirement: Invoice numbering
The system SHALL support configurable invoice numbering schemes.

#### Scenario: Auto-increment invoice number
- **WHEN** invoice is created
- **THEN** next sequential invoice number is assigned

#### Scenario: Custom invoice number prefix
- **WHEN** invoice sequence is configured with prefix
- **THEN** invoice numbers include prefix (e.g., INV-2024-0001)

### Requirement: Invoice status tracking
The system SHALL track invoice lifecycle status.

#### Scenario: Invoice status workflow
- **WHEN** invoice is created
- **THEN** status is set to draft, then sent, then paid (or overdue)

#### Scenario: Mark invoice as paid
- **WHEN** user marks invoice as paid with payment date and method
- **THEN** invoice status changes to paid and payment is recorded

#### Scenario: Overdue invoice
- **WHEN** invoice due date passes without full payment
- **THEN** invoice status changes to overdue

### Requirement: Invoice payments
The system SHALL record partial and full payments against invoices.

#### Scenario: Partial payment
- **WHEN** customer makes partial payment on invoice
- **THEN** payment is recorded and balance due is updated

#### Scenario: Multiple payments
- **WHEN** invoice receives multiple payments over time
- **THEN** all payments are tracked and invoice shows payment history

### Requirement: Invoice adjustments
The system SHALL allow credit notes and invoice adjustments.

#### Scenario: Create credit note
- **WHEN** user creates credit note for returned items
- **THEN** credit note is linked to original invoice and balance adjusted

#### Scenario: Void invoice
- **WHEN** user voids invoice
- **THEN** invoice status changes to voided and original items restored to inventory