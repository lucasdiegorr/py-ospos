# sale Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Start POS sale
The system SHALL allow starting a new sale session with cart.

#### Scenario: Create new sale
- **WHEN** user starts new sale
- **THEN** sale record is created with status=open and empty cart

#### Scenario: Add item to cart
- **WHEN** user adds item to cart with quantity
- **THEN** cart line item is added and total updated

#### Scenario: Scan barcode to add item
- **WHEN** user scans item barcode
- **THEN** item is found and added to cart

### Requirement: Cart management
The system SHALL support modifying cart line items.

#### Scenario: Update line item quantity
- **WHEN** user changes quantity of cart item
- **THEN** line total and cart total are recalculated

#### Scenario: Remove item from cart
- **WHEN** user removes item from cart
- **THEN** item is removed and total updated

#### Scenario: Apply discount to line item
- **WHEN** user applies percentage or fixed discount to line item
- **THEN** discount is applied and reflected in line total

### Requirement: Complete sale
The system SHALL allow completing sales with payment.

#### Scenario: Complete sale with cash payment
- **WHEN** user completes sale with cash payment equal to total
- **THEN** sale status changes to completed, inventory decremented, receipt generated

#### Scenario: Complete sale with change
- **WHEN** customer pays more than total with cash
- **THEN** change amount is calculated and displayed

#### Scenario: Complete sale with mixed payment
- **WHEN** customer pays part cash, part card
- **THEN** both payment amounts recorded and sale completed when total reached

### Requirement: Sale transactions
The system SHALL log all sale transactions for audit.

#### Scenario: Transaction history for sale
- **WHEN** user views sale details
- **THEN** transaction log shows all payment attempts and status changes

#### Scenario: Void sale
- **WHEN** user voids a completed sale
- **THEN** sale status changes to voided and inventory restored

### Requirement: Suspend and recall sales
The system SHALL allow suspending incomplete sales and recalling them.

#### Scenario: Suspend sale
- **WHEN** user suspends an open sale
- **THEN** sale is saved with status=suspended for later recall

#### Scenario: Recall suspended sale
- **WHEN** user recalls suspended sale
- **THEN** sale cart is restored and user can continue

### Requirement: Customer association
The system SHALL allow associating customer with sale.

#### Scenario: Add customer to sale
- **WHEN** user associates customer with sale
- **THEN** customer info is linked and can earn rewards points

#### Scenario: Remove customer from sale
- **WHEN** user removes customer from sale
- **THEN** customer link is removed but sale continues

