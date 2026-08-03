## Purpose

Provides the cross-cutting offline-first mechanism for the system: sales and other writes made while disconnected are recorded locally, stored in an outbox, and later synchronized to the server with conflict reconciliation. Other capabilities reference this behavior rather than redefining it.

## ADDED Requirements

### Requirement: Local writes while offline
When the device is offline, the system SHALL allow supported write operations (notably sale completion) to be finalized locally and queued for later synchronization, instead of failing.

#### Scenario: Sale finalized offline
- **WHEN** a device is offline and an attendant completes a sale
- **THEN** the sale is stored locally with status pending-sync and is available in local reports

### Requirement: Outbox persistence
Pending writes SHALL be persisted durably in an outbox on the device so they survive application restarts and are not lost.

#### Scenario: Restart preserves outbox
- **WHEN** the application is restarted with unsynchronized sales in the outbox
- **THEN** the pending sales remain queued and are synchronized when connectivity returns

### Requirement: Automatic synchronization on reconnect
The system SHALL detect restored connectivity and SHALL push pending outbox entries to the server in order, without requiring the user to act.

#### Scenario: Sync on reconnect
- **WHEN** connectivity returns and the application is online
- **THEN** queued sales are sent to the server in creation order and their status changes to synced

### Requirement: Idempotent synchronization
Each outbox entry SHALL carry a client-generated idempotency key so re-delivery of the same entry does not create duplicates on the server.

#### Scenario: Duplicate delivery ignored
- **WHEN** the server receives a sync payload with an idempotency key it has already processed
- **THEN** the server acknowledges it without creating a second record

### Requirement: Conflict detection and reconciliation
When a sync entry conflicts with the current server state, the system SHALL detect the conflict and resolve it by a documented reconciliation rule rather than silently overwriting.

#### Scenario: Stock quantity conflict
- **WHEN** two offline devices each sell units of the same product and both sync after the fact
- **THEN** the server applies both movements in sync order and the stock total reflects both sales

#### Scenario: Concurrent price edit conflict
- **WHEN** a product's price is edited on the server while an offline device still holds a sale using the old price
- **THEN** the offline sale is accepted as recorded (price at time of sale) and flagged for review rather than rejected

### Requirement: Pending-sync status exposure
The system SHALL expose the count of pending-sync entries so user interfaces and reports can warn about incomplete data.

#### Scenario: Count available to reporting
- **WHEN** a report is generated while the outbox has N entries
- **THEN** the reporting capability can read and display that N in its pending-sync notice

### Requirement: Fail-safe on permanent conflict
If an outbox entry cannot be synchronized after retries and reconciliation, the system SHALL surface it to a manager for manual resolution instead of dropping it silently.

#### Scenario: Manual resolution queue
- **WHEN** an outbox entry fails permanently after configured retries
- **THEN** it is placed in a visible resolution queue and is not counted as synced
