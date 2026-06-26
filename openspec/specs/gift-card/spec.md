# gift-card Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Issue gift card
The system SHALL allow issuing gift cards with balance.

#### Scenario: Issue new gift card
- **WHEN** user issues gift card with initial balance
- **THEN** gift card is created with unique card number and balance

#### Scenario: Gift card with custom number
- **WHEN** user specifies custom gift card number
- **THEN** card is created with specified number if available

### Requirement: Gift card redemption
The system SHALL allow using gift card balance during sale.

#### Scenario: Apply gift card to sale
- **WHEN** user applies gift card to sale
- **THEN** gift card balance is decremented by sale total (or up to balance)

#### Scenario: Partial gift card payment
- **WHEN** gift card balance is less than sale total
- **THEN** remaining balance is used and customer pays difference

#### Scenario: Gift card balance check
- **WHEN** user checks gift card balance
- **THEN** current balance and transaction history are returned

### Requirement: Gift card reload
The system SHALL allow adding funds to existing gift card.

#### Scenario: Reload gift card
- **WHEN** user adds funds to gift card
- **THEN** balance is incremented by reload amount

### Requirement: Gift card expiration
The system SHALL optionally expire gift cards after set period.

#### Scenario: Expired gift card
- **WHEN** gift card is used after expiration date
- **THEN** system rejects with expiration error

