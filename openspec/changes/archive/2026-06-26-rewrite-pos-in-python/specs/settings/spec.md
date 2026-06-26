## ADDED Requirements

### Requirement: System configuration
The system SHALL support configurable application settings.

#### Scenario: Update company info
- **WHEN** admin updates company name, address, phone
- **THEN** settings are saved and reflected in receipts/invoices

#### Scenario: Configure tax options
- **WHEN** admin configures tax inclusive/exclusive mode
- **THEN** system calculates taxes according to setting

### Requirement: Theme selection
The system SHALL support selectable UI themes.

#### Scenario: Change UI theme
- **WHEN** admin selects different theme
- **THEN** UI updates to selected theme

#### Scenario: Theme preview
- **WHEN** admin previews theme
- **THEN** preview is shown before applying

### Requirement: MailChimp integration
The system SHALL integrate with MailChimp for email marketing.

#### Scenario: Configure MailChimp API
- **WHEN** admin enters MailChimp API key
- **THEN** system can sync customers to MailChimp

#### Scenario: Sync customer to MailChimp
- **WHEN** customer is created or updated
- **THEN** customer data is synced to MailChimp list

### Requirement: reCAPTCHA configuration
The system SHALL support Google reCAPTCHA on login.

#### Scenario: Enable reCAPTCHA
- **WHEN** admin configures reCAPTCHA site and secret keys
- **THEN** reCAPTCHA challenge is shown on login

#### Scenario: Disable reCAPTCHA
- **WHEN** admin removes reCAPTCHA keys
- **THEN** login proceeds without reCAPTCHA challenge