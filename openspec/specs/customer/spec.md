# customer Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: Customer creation
The system SHALL allow creation of customer records with name, email, phone, and address.

#### Scenario: Create customer with all fields
- **WHEN** user submits customer data with name, email, phone, and address
- **THEN** customer record is created and returned with generated ID

#### Scenario: Create customer with minimal fields
- **WHEN** user submits customer data with only required name field
- **THEN** customer record is created with default values for optional fields

#### Scenario: Duplicate email warning
- **WHEN** user creates customer with email that already exists
- **THEN** system returns warning but allows creation

### Requirement: Customer search
The system SHALL allow searching customers by name, email, or phone.

#### Scenario: Search by partial name
- **WHEN** user searches for customers with partial name match
- **THEN** system returns all customers whose name contains the search term

#### Scenario: Search by email exact match
- **WHEN** user searches by exact email
- **THEN** system returns matching customer if found

### Requirement: Customer update
The system SHALL allow updating customer information.

#### Scenario: Update customer fields
- **WHEN** user updates customer phone and address
- **THEN** customer record reflects new values

#### Scenario: Update non-existent customer
- **WHEN** user attempts to update customer with invalid ID
- **THEN** system returns 404 Not Found

### Requirement: Customer delete
The system SHALL allow soft-deleting customers.

#### Scenario: Soft delete customer
- **WHEN** user deletes a customer
- **THEN** customer is marked as inactive but not removed from database

#### Scenario: Deleted customer not searchable
- **WHEN** user searches for deleted customer by name
- **THEN** customer does not appear in results

### Requirement: Supplier management
The system SHALL support both customers and suppliers in the same entity model with type classification.

#### Scenario: Create supplier
- **WHEN** user creates entity with type=supplier
- **THEN** entity is created as supplier and searchable in supplier list

#### Scenario: Filter entities by type
- **WHEN** user requests only suppliers
- **THEN** results include only entities with type=supplier

