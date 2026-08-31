## MODIFIED Requirements

### Requirement: Open cash shift with starting float
The system SHALL allow an attendant to open a cash shift by recording the starting cash float (fundo de troco). The open-shift form MUST be presented in a clearly delimited card with labeled float-amount input and a primary submit action.

#### Scenario: Open shift
- **WHEN** an attendant opens a shift with a starting float of R$ 100.00 via the open-shift card
- **THEN** the shift is active and subsequent sales are associated with it

#### Scenario: Cannot open while shift active
- **WHEN** an attendant already has an active shift and attempts to open another
- **THEN** the system refuses to open a second shift

### Requirement: Cash supply (suprimento)
The system SHALL allow adding cash to the shift drawer during the shift, recording the amount and reason. The supply form MUST be presented in a dedicated card with labeled amount and reason inputs.

#### Scenario: Supply adds cash
- **WHEN** an attendant records a supply of R$ 50.00 to cover change via the supply card
- **THEN** the shift's cash-in increases by R$ 50.00 and the movement appears in the movements table

### Requirement: Cash bleed (sangria)
The system SHALL allow removing cash from the shift drawer during the shift, recording the amount and reason. The bleed form MUST be presented in a dedicated card with labeled amount and reason inputs.

#### Scenario: Bleed removes cash
- **WHEN** an attendant records a bleed of R$ 80.00 for a cash expense via the bleed card
- **THEN** the shift's cash-out increases by R$ 80.00 and the movement appears in the movements table

### Requirement: Close shift with reconciliation
The system SHALL allow closing a shift by recording the counted cash; the system SHALL compute and record the difference between counted and expected cash. The close-shift panel MUST display the expected cash, the counted-cash input, and the resulting difference. The difference MUST be visually distinguished: green/neutral when zero or positive, red/destructive when negative.

#### Scenario: Balanced close
- **WHEN** an attendant counts R$ 370.00 against an expected R$ 370.00
- **THEN** the shift closes with zero difference shown in neutral styling

#### Scenario: Difference recorded
- **WHEN** an attendant counts R$ 365.00 against an expected R$ 370.00
- **THEN** the shift closes with a recorded difference of R$ -5.00 displayed in destructive/red styling

#### Scenario: Cannot sell after close
- **WHEN** a shift is closed
- **THEN** no further sales can be attributed to it

## ADDED Requirements

### Requirement: Shift movements table
The Caixa screen MUST present supply and bleed movements in a table within the active-shift view, showing timestamp, type, amount, and reason for each movement.

#### Scenario: Movements table populated
- **WHEN** the active shift has at least one supply or bleed recorded
- **THEN** the movements table shows one row per movement with type, amount, reason, and timestamp

### Requirement: Caixa theming
The Caixa screen MUST render correctly in both light and dark themes, using the same theme tokens as the rest of the application.

#### Scenario: Theme parity
- **WHEN** the active theme is light or dark
- **THEN** the open-shift card, supply card, bleed card, close-shift panel, and movements table all use the theme's foreground, background, primary, and destructive tokens with sufficient contrast
