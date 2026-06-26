## ADDED Requirements

### Requirement: Create receiving
The system SHALL allow recording stock received from suppliers.

#### Scenario: Create receiving with items
- **WHEN** user creates receiving with supplier, items, and quantities
- **THEN** receiving record is created and inventory increased

#### Scenario: Associate purchase order
- **WHEN** user creates receiving linked to purchase order
- **THEN** items are matched against PO and variance tracked

### Requirement: Receiving costs
The system SHALL track cost of received inventory.

#### Scenario: Record item cost on receiving
- **WHEN** user receives items
- **THEN** item cost is updated to reflect new receiving cost

#### Scenario: Average cost calculation
- **WHEN** item received at different cost
- **THEN** average cost is recalculated across all inventory

### Requirement: Receiving status
The system SHALL track receiving status from pending to completed.

#### Scenario: Partial receiving
- **WHEN** only some items of a shipment arrive
- **THEN** receiving shows partial status and remaining items pending

#### Scenario: Complete receiving
- **WHEN** all items received
- **THEN** receiving status changes to completed