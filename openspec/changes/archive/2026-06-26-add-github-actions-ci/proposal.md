## Why

The project lacks automated CI — every change must be manually tested and reviewed without guaranteed test coverage verification. A GitHub Actions workflow will run all tests on every PR, enforcing the 90% coverage threshold before merge.

## What Changes

- Add `.github/workflows/ci.yml` with a GitHub Actions workflow
- Run `pytest --cov --cov-fail-under=90` on push and PR to master
- Use Python 3.12 with project dependencies installed
- No external services needed (tests use fully mocked in-memory data store)
- Required check for PR approval (branch protection rule)

## Capabilities

### New Capabilities

- `ci`: Automated test execution and coverage enforcement via GitHub Actions

### Modified Capabilities

<!-- No existing capabilities are modified -->

## Impact

- New file: `.github/workflows/ci.yml`
- Requires branch protection rule on master: require CI status check to pass
- No changes to application code, dependencies, or configuration
