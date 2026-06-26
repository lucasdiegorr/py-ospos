# rewards Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Customer rewards enrollment
The system SHALL allow enrolling customers in rewards program.

#### Scenario: Enroll in rewards
- **WHEN** user enrolls customer in rewards program
- **THEN** customer is marked as rewards member with zero points

#### Scenario: Rewards tier assignment
- **WHEN** customer reaches point threshold
- **THEN** customer is assigned to appropriate rewards tier

### Requirement: Earn rewards points
The system SHALL award points based on purchases.

#### Scenario: Earn points on sale
- **WHEN** sale is completed for rewards customer
- **THEN** points are awarded based on configurable points-per-currency rule

#### Scenario: Points multiplier by tier
- **WHEN** higher tier customer makes purchase
- **THEN** points multiplier is applied (e.g., 2x for gold tier)

### Requirement: Redeem rewards points
The system SHALL allow redeeming points for discounts.

#### Scenario: Redeem points
- **WHEN** user redeems points during sale
- **THEN** discount is applied and points deducted

#### Scenario: Points value conversion
- **WHEN** points are redeemed
- **THEN** points are converted to currency at configured rate

### Requirement: Rewards expiration
The system SHALL expire unused points after set period.

#### Scenario: Points expiration
- **WHEN** points are older than expiration period
- **THEN** points are marked as expired and removed

