## Purpose

Manages user accounts and their access roles within the system. Defines the three roles — attendant, manager, and admin — and the operations each role may perform across the capabilities.

## ADDED Requirements

### Requirement: User accounts have a role
Every user account SHALL have exactly one of three roles: `attendant`, `manager`, or `admin`. The role determines which operations the user may perform.

#### Scenario: Attendant limited scope
- **WHEN** a user with role `attendant` is authenticated
- **THEN** they can operate the point of sale, view customers, and consult stock, but cannot create products, manage users, or open reports beyond their own shift

#### Scenario: Manager full operational scope
- **WHEN** a user with role `manager` is authenticated
- **THEN** they can perform all operational tasks including product catalog management, stock entries, deliveries, fiado adjustments, and all reports

#### Scenario: Admin adds administrative scope
- **WHEN** a user with role `admin` is authenticated
- **THEN** they can additionally manage user accounts and system configuration

### Requirement: Create user account
The system SHALL allow a manager or admin to create a user account with name, username, password, and role.

#### Scenario: Admin creates attendant
- **WHEN** an admin creates a user with role `attendant` and valid fields
- **THEN** the account is active and the new user can log in with the chosen credentials

#### Scenario: Attendant cannot create users
- **WHEN** a user with role `attendant` attempts to create a user account
- **THEN** the system denies the operation

### Requirement: Edit user account
The system SHALL allow a manager or admin to update a user's name, username, role, and password.

#### Scenario: Role change takes effect on next token
- **WHEN** an admin changes a user's role from `attendant` to `manager`
- **THEN** the change applies to new access tokens issued after the change; existing tokens retain the previous role until they expire

### Requirement: Deactivate and reactivate user
The system SHALL allow an admin to deactivate a user account, which prevents login, and to reactivate it later.

#### Scenario: Deactivated user cannot log in
- **WHEN** an admin deactivates a user's account
- **THEN** that user's future login attempts are refused until the account is reactivated

### Requirement: Admin cannot deactivate their own last admin
The system SHALL prevent deactivating the last active admin account.

#### Scenario: Last admin protected
- **WHEN** an admin attempts to deactivate the only active account with role `admin`
- **THEN** the system refuses the operation

### Requirement: Password reset
The system SHALL allow an admin to reset another user's password, and SHALL allow a user to change their own password given the current one.

#### Scenario: Admin resets password
- **WHEN** an admin resets a user's password
- **THEN** the user's old password no longer works and the new one is required for login

#### Scenario: Self password change requires current password
- **WHEN** a user changes their own password with an incorrect current password
- **THEN** the system rejects the change

### Requirement: List and search users
The system SHALL allow a manager or admin to list and search user accounts by name or username.

#### Scenario: Search by name
- **WHEN** a manager searches users with a name fragment
- **THEN** the system returns all accounts whose name matches the fragment, including active and inactive ones
