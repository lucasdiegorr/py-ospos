# messaging Specification

## Purpose
TBD - created by archiving change rewrite-pos-in-python. Update Purpose after archive.
## Requirements
### Requirement: SMS notifications
The system SHALL send SMS notifications for configured events.

#### Scenario: Send SMS on sale
- **WHEN** sale is completed and customer SMS is available
- **THEN** optional SMS confirmation is sent to customer

#### Scenario: SMS appointment reminder
- **WHEN** configured time before appointment
- **THEN** SMS reminder is sent to customer

### Requirement: SMS configuration
The system SHALL support configurable SMS provider.

#### Scenario: Configure SMS provider
- **WHEN** admin configures SMS provider credentials
- **THEN** system can send SMS messages through provider

#### Scenario: Test SMS
- **WHEN** admin sends test SMS
- **THEN** SMS is sent to verify configuration

### Requirement: SMS templates
The system SHALL support configurable SMS message templates.

#### Scenario: Custom SMS template
- **WHEN** admin creates SMS template with variables
- **THEN** template is used for corresponding event type

#### Scenario: Template variable substitution
- **WHEN** SMS is sent with template
- **THEN** variables like {customer_name} and {sale_total} are replaced

