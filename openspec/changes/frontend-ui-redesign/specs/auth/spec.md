## MODIFIED Requirements

### Requirement: User can log in with credentials
The system SHALL authenticate a user by their username/email and password, and on success issue a JWT access token plus a refresh token. The login screen SHALL present a centered, accessible card containing a labeled username field, a labeled password field, a primary submit button, and a dedicated error region. All form controls MUST be keyboard-navigable and have visible focus rings.

#### Scenario: Successful login
- **WHEN** a registered, active user submits valid credentials
- **THEN** the system returns an access token, a refresh token, and the user's profile (name, role), and the user is redirected to the default landing page (PDV)

#### Scenario: Invalid credentials
- **WHEN** a user submits an incorrect password
- **THEN** the system returns an authentication error, the error region in the login card displays a user-visible message, and the failed attempt is recorded for that account

#### Scenario: Disabled account
- **WHEN** an admin has deactivated the user's account and the user attempts to log in with valid credentials
- **THEN** the system refuses login and the error region in the login card displays an account-disabled message

#### Scenario: Login form accessibility
- **WHEN** the login screen is rendered
- **THEN** every input has an associated label, the submit button can be activated by Enter while focus is in any field, and focused controls display a visible focus ring

## ADDED Requirements

### Requirement: Login supports light and dark themes
The login screen MUST render correctly in both light and dark themes and MUST inherit theme tokens from the application shell when present.

#### Scenario: Theme parity
- **WHEN** the application shell applies a theme (light or dark)
- **THEN** the login card, inputs, button, and error region use the theme's foreground, background, primary, and destructive colors with sufficient contrast

### Requirement: Login communicates submission state
The login screen MUST indicate when a submission is in progress (e.g., button disabled, loading label) to prevent duplicate submissions.

#### Scenario: Submitting state
- **WHEN** the user submits the form and the credentials are being verified
- **THEN** the submit button is disabled and shows a "submitting" label until the response is received
