## Purpose

Manages the cash shift lifecycle: opening a shift with a starting float, registering sales within it, recording supply (suprimento) and bleed (sangria) of cash, and closing the shift with an expected-vs-counted reconciliation.

## ADDED Requirements

### Requirement: Open cash shift with starting float
The system SHALL allow an attendant to open a cash shift by recording the starting cash float (fundo de troco).

#### Scenario: Open shift
- **WHEN** an attendant opens a shift with a starting float of R$ 100.00
- **THEN** the shift is active and subsequent sales are associated with it

#### Scenario: Cannot open while shift active
- **WHEN** an attendant already has an active shift and attempts to open another
- **THEN** the system refuses to open a second shift

### Requirement: Sales belong to a shift
Every sale SHALL be associated with the shift that was active when it was created, and SHALL appear in that shift's totals.

#### Scenario: Sale attributed to active shift
- **WHEN** a sale is completed while a shift is active
- **THEN** the sale is recorded under that shift and counts toward its totals

#### Scenario: Sale without active shift
- **WHEN** a sale is attempted with no active shift
- **THEN** the system prompts the attendant to open a shift before completing the sale

### Requirement: Cash supply (suprimento)
The system SHALL allow adding cash to the shift drawer during the shift, recording the amount and reason.

#### Scenario: Supply adds cash
- **WHEN** an attendant records a supply of R$ 50.00 to cover change
- **THEN** the shift's cash-in increases by R$ 50.00 and the movement is logged

### Requirement: Cash bleed (sangria)
The system SHALL allow removing cash from the shift drawer during the shift, recording the amount and reason.

#### Scenario: Bleed removes cash
- **WHEN** an attendant records a bleed of R$ 80.00 for a cash expense
- **THEN** the shift's cash-out increases by R$ 80.00 and the movement is logged

### Requirement: Expected cash calculation
At any point the system SHALL compute the expected cash in the drawer as the starting float plus cash sales and supplies minus bleeds.

#### Scenario: Expected total computed
- **WHEN** a shift has float R$ 100.00, cash sales R$ 300.00, supplies R$ 50.00, and bleeds R$ 80.00
- **THEN** the expected cash is R$ 370.00

### Requirement: Close shift with reconciliation
The system SHALL allow closing a shift by recording the counted cash; the system SHALL compute and record the difference between counted and expected cash.

#### Scenario: Balanced close
- **WHEN** an attendant counts R$ 370.00 against an expected R$ 370.00
- **THEN** the shift closes with zero difference

#### Scenario: Difference recorded
- **WHEN** an attendant counts R$ 365.00 against an expected R$ 370.00
- **THEN** the shift closes with a recorded difference of R$ -5.00

#### Scenario: Cannot sell after close
- **WHEN** a shift is closed
- **THEN** no further sales can be attributed to it

### Requirement: Shift summary
The system SHALL produce a closing summary for a shift showing per-method payment totals, supplies, bleeds, expected cash, counted cash, and difference.

#### Scenario: Closing report
- **WHEN** a shift is closed
- **THEN** the closing summary shows payment-method totals, float, supplies, bleeds, expected, counted, and difference

### Requirement: Role access to shift operations
The system SHALL restrict opening/closing shifts and supply/bleed to attendants, managers, and admins, with the shift tied to the acting user.

#### Scenario: Shift tied to attendant
- **WHEN** an attendant opens a shift
- **THEN** that shift records the attendant as responsible and only they can close it unless a manager intervenes
