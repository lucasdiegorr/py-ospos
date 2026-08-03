## Purpose

Handles authentication for the POS system: verifying user credentials, issuing stateless JWT access tokens, refreshing sessions, logging out, and protecting against brute-force login attempts.

## ADDED Requirements

### Requirement: User can log in with credentials
The system SHALL authenticate a user by their username/email and password, and on success issue a JWT access token plus a refresh token.

#### Scenario: Successful login
- **WHEN** a registered, active user submits valid credentials
- **THEN** the system returns an access token, a refresh token, and the user's profile (name, role)

#### Scenario: Invalid credentials
- **WHEN** a user submits an incorrect password
- **THEN** the system returns an authentication error and records a failed attempt for that account

#### Scenario: Disabled account
- **WHEN** an admin has deactivated the user's account and the user attempts to log in with valid credentials
- **THEN** the system refuses login with an account-disabled error

### Requirement: Access tokens expire
Access tokens SHALL be short-lived and stateless; the system SHALL reject requests carrying an expired or malformed token.

#### Scenario: Expired access token
- **WHEN** a request is made with an access token past its expiration
- **THEN** the system rejects the request with an unauthorized error

#### Scenario: Valid token allows access
- **WHEN** a request is made with a valid, non-expired access token
- **THEN** the system authorizes the request and identifies the requesting user

### Requirement: Refresh token rotates sessions
The system SHALL accept a valid refresh token to issue a new access token, and SHALL invalidate the used refresh token (rotation).

#### Scenario: Refresh with valid token
- **WHEN** a user presents a valid, unexpired refresh token
- **THEN** the system issues a new access token and a new refresh token, invalidating the previous refresh token

#### Scenario: Refresh with revoked token
- **WHEN** a user presents a refresh token that was already used or revoked
- **THEN** the system rejects the refresh and does not issue a new token

### Requirement: User can log out
The system SHALL allow a logged-in user to revoke their current refresh token, terminating the session.

#### Scenario: Logout revokes session
- **WHEN** a logged-in user requests logout with their refresh token
- **THEN** the system revokes that refresh token and further refresh attempts with it fail

### Requirement: Login lockout after repeated failures
The system SHALL lock an account temporarily after a configurable number of consecutive failed login attempts, and SHALL unlock it after a configurable cooldown.

#### Scenario: Lockout threshold reached
- **WHEN** a user exceeds the maximum allowed consecutive failed login attempts
- **THEN** the system blocks further login attempts for that account until the cooldown expires

#### Scenario: Lockout clears after cooldown
- **WHEN** the cooldown period for a locked account has elapsed
- **THEN** the user can attempt to log in again

### Requirement: Token carries user role
The access token SHALL encode the user's role so authorization decisions can be made without a server round-trip, while profile details remain retrievable from the users capability.

#### Scenario: Role available from token
- **WHEN** the backend decodes a valid access token
- **THEN** it can read the user id and role from the token claims
