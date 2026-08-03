## Purpose

Records deliveries made by the store's own drivers for internal control. In the MVP there is no freight calculation and no external delivery integration; the address is stored partially because customers may only provide references.

## ADDED Requirements

### Requirement: Delivery registration on sale
The system SHALL allow attaching a delivery to a sale, indicating that the goods will be delivered by the store, without calculating any freight or fee.

#### Scenario: Sale with delivery
- **WHEN** an attendant finalizes a sale and marks it for delivery
- **THEN** the sale is recorded with delivery status and no additional fee is charged

### Requirement: Partial address with optional fields
Delivery address fields — street, number, district, complement, and reference — SHALL all be optional, since customers may only know partial references.

#### Scenario: Reference-only address
- **WHEN** a delivery is saved providing only a reference such as "casa amarela, perto da padaria"
- **THEN** the delivery is accepted without requiring any address field

#### Scenario: Full address
- **WHEN** a delivery is saved with full street, number, and district
- **THEN** all provided fields are stored and shown on the delivery record

### Requirement: Delivery status tracking
The system SHALL track delivery status through at least the states pending, in-transit, and delivered.

#### Scenario: Delivery lifecycle
- **WHEN** a sale with delivery is created it starts as pending; an attendant then marks it in-transit and later delivered
- **THEN** the delivery transitions through pending to in-transit to delivered and each change is recorded

### Requirement: Delivery list
The system SHALL allow listing deliveries by status and date, including the customer, destination summary, and sale reference.

#### Scenario: Filter pending deliveries
- **WHEN** a user filters deliveries by status pending
- **THEN** the system shows only not-yet-delivered orders with their destination and sale reference

### Requirement: Future integration hooks
The system SHALL record delivery data (address, customer, items, status) in a way that supports future freight calculation and external delivery integrations, without implementing them in the MVP.

#### Scenario: Data retained for future use
- **WHEN** a delivery is recorded
- **THEN** all relevant data is persisted so a future change can add freight calculation or third-party delivery without data loss
