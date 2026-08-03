## Purpose

Manages customer records for the beverage warehouse: registering customers with minimal data, searching them during a sale, and storing the fiado (credit) profile that sales on credit depend on.

## ADDED Requirements

### Requirement: Register customer with minimal data
The system SHALL allow registering a customer with at least a display name. Other identifiers (CPF, phone) are optional.

#### Scenario: Register by name only
- **WHEN** an attendant or manager registers a customer providing only a name
- **THEN** the customer is saved and can be selected in a sale

#### Scenario: Register with identifiers
- **WHEN** a customer is registered with name plus CPF and phone
- **THEN** those fields are stored and shown in the customer's record

### Requirement: Customer address is optional and partial
The system SHALL store customer address fields (street, number, district, complement, reference) where every field is optional, because customers may only know references rather than a full address.

#### Scenario: Partial address accepted
- **WHEN** a customer is saved with only a reference note and no street or number
- **THEN** the record is accepted without validation errors

### Requirement: Anonymous sale without customer
The system SHALL allow a sale to be completed without selecting a customer, for walk-in (balcão) sales.

#### Scenario: Walk-in sale
- **WHEN** an attendant completes a sale paid by cash, card, or PIX without choosing a customer
- **THEN** the sale is finalized and no customer is required

#### Scenario: Fiado requires customer
- **WHEN** a sale is paid using the `fiado` method
- **THEN** the system requires a registered customer and refuses the sale without one

### Requirement: Search customers
The system SHALL allow searching customers by name, CPF, or phone during a sale and in the customer list.

#### Scenario: Search by name fragment
- **WHEN** an attendant types a name fragment in the customer search
- **THEN** the system shows matching customers in order of best match

### Requirement: Customer fiado profile
The system SHALL store on each customer an optional fiado profile with three fields: credit limit, interest rate (%), and default due period. At least one of these three fields MUST be set when a fiado profile is created.

#### Scenario: Create fiado profile with one mandatory field
- **WHEN** an attendant or manager creates a fiado profile for a customer setting only the credit limit
- **THEN** the profile is accepted because at least one field is present

#### Scenario: Fiado profile with no fields rejected
- **WHEN** an attendant attempts to create a fiado profile leaving limit, interest, and due period all empty
- **THEN** the system rejects the profile with a validation error

#### Scenario: Sales on fiado without limit allowed
- **WHEN** a customer has a fiado profile with only an interest rate or only a due period and no credit limit
- **THEN** the customer may still make fiado sales and the system does not enforce a limit

### Requirement: Edit customer and fiado profile
The system SHALL allow editing a customer's basic data and fiado profile.

#### Scenario: Manager adjusts credit limit
- **WHEN** a manager raises a customer's credit limit
- **THEN** the new limit is applied to subsequent fiado sales and any future fiado sale is validated against it

### Requirement: Customer purchase history
The system SHALL expose a customer's purchase history, including their open fiado balance and recent sales.

#### Scenario: View history and balance
- **WHEN** a manager opens a customer's record
- **THEN** the system shows recent sales and the current outstanding fiado balance
