# restaurant-table Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Table management
The system SHALL support restaurant table configuration and status.

#### Scenario: Configure tables
- **WHEN** admin creates table with number and capacity
- **THEN** table is available for assignment

#### Scenario: Table status tracking
- **WHEN** table status changes (available, occupied, reserved)
- **THEN** status is updated and reflected in table layout

### Requirement: Table assignments
The system SHALL allow assigning sales to tables.

#### Scenario: Start sale at table
- **WHEN** user starts sale and assigns to table
- **THEN** table status changes to occupied

#### Scenario: Transfer table
- **WHEN** customer moves to different table
- **THEN** sale is transferred and table statuses updated

#### Scenario: Close table
- **WHEN** table is closed (payment complete)
- **THEN** table status returns to available

### Requirement: Table reservations
The system SHALL support table reservations.

#### Scenario: Create reservation
- **WHEN** user creates reservation with date, time, and party size
- **THEN** reservation is recorded and table is tentatively held

#### Scenario: Reservation reminder
- **WHEN** configured time before reservation
- **THEN** reminder is sent to customer (if messaging enabled)

