# tax Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Tax configuration
The system SHALL support configurable tax rates and types.

#### Scenario: Create tax rate
- **WHEN** admin creates tax rate with name and percentage
- **THEN** tax rate is available for item and sale assignment

#### Scenario: Multiple tax rates per item
- **WHEN** item has multiple taxes applied
- **THEN** each tax is calculated and shown separately

### Requirement: Tax categories
The system SHALL support tax categories with different rate assignments.

#### Scenario: Assign tax category to item
- **WHEN** user assigns tax category to item
- **THEN** item inherits tax rates from category

### Requirement: Tax inclusive pricing
The system SHALL support tax-inclusive pricing mode.

#### Scenario: Tax included in price
- **WHEN** item price is set as tax-inclusive
- **THEN** tax is calculated by reversing from the listed price

### Requirement: Multi-tier taxation
The system SHALL support VAT, GST, and other multi-tier tax structures.

#### Scenario: Configure tax tiers
- **WHEN** admin configures tax tiers with different rates per bracket
- **THEN** correct tier rate is applied based on amount

#### Scenario: Compound taxes
- **WHEN** multiple taxes are marked as compound
- **THEN** second tax is calculated on subtotal plus first tax

