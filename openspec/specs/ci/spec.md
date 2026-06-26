# ci Specification

## Purpose
TBD - created by archiving change add-github-actions-ci. Update Purpose after archive.
## Requirements
### Requirement: Automated test execution on PR
The system SHALL automatically run the full test suite when a pull request is opened or updated against the master branch.

#### Scenario: PR triggers test run
- **WHEN** a pull request is opened or updated targeting the `master` branch
- **THEN** the CI workflow SHALL execute `pytest --cov --cov-fail-under=90`

#### Scenario: Push to master triggers test run
- **WHEN** commits are pushed directly to the `master` branch
- **THEN** the CI workflow SHALL execute `pytest --cov --cov-fail-under=90`

### Requirement: Coverage enforcement
The CI workflow SHALL enforce the minimum code coverage threshold of 90%.

#### Scenario: Coverage below threshold fails workflow
- **WHEN** test coverage drops below 90%
- **THEN** the CI workflow SHALL fail and report the coverage percentage

#### Scenario: Coverage meets threshold passes workflow
- **WHEN** test coverage is 90% or above
- **THEN** the CI workflow SHALL pass and report the coverage percentage

### Requirement: CI status visible in PR checks
The CI workflow SHALL report its status as a check on pull requests.

#### Scenario: Check appears in PR
- **WHEN** a pull request is open
- **THEN** the CI workflow check SHALL be visible in the PR checks section with status (pending, passing, or failing)

