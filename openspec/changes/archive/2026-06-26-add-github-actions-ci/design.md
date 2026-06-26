## Context

The project uses pytest with `pytest-asyncio` and `pytest-cov` for testing. All tests run against a fully mocked in-memory data store (`MockDbSession`), requiring no external services (PostgreSQL, Redis, etc.). Tests are configured via `pyproject.toml` with `asyncio_mode = "auto"` and `testpaths = ["tests"]`.

GitHub Actions is the CI platform, already available since the repo is hosted on GitHub. The workflow only needs to check out the code, install Python and dependencies, and run tests with coverage enforcement.

## Goals / Non-Goals

**Goals:**
- Run `pytest --cov --cov-fail-under=90` on every push and PR to master
- Fail the workflow if coverage drops below 90%
- Use a minimal, fast workflow (install only what's needed, no services)
- Provide clear CI status visible in PR checks

**Non-Goals:**
- Deploying artifacts or running lint/format checks (separate change)
- Running database integration tests (would require PostgreSQL service)
- Cross-platform testing (Linux only — current dev environment)
- Caching dependencies (fast enough without; can be added later)

## Decisions

1. **Single job, single OS (ubuntu-latest)**
   - Tests don't need Docker or multiple platforms; keeping it simple reduces maintenance.

2. **Install via pip instead of Docker**
   - Tests don't need the Docker app image (no PostgreSQL, no Redis). Pip install is faster and simpler.

3. **`pytest --cov --cov-fail-under=90` as the single check**
   - The project already requires 90% coverage. Running the exact command developers use locally avoids confusion.

4. **Run on `push` and `pull_request` to `master`**
   - Push ensures master is always green. PR trigger gives visibility during review, even before branch protection rules apply.

5. **No dependency caching**
   - With few dependencies and fast install, caching adds complexity for marginal speed gain. Can be added later if needed.

## Risks / Trade-offs

- **Outdated dependencies in CI**: `pip install` always gets latest compatible versions per `requirements.txt` constraints. If a new release breaks tests, it fails in CI before merge — acceptable trade-off for simplicity.
- **No matrix testing**: Only Python 3.12 on Linux. If the project later needs multi-version or multi-OS testing, the matrix can be added then.
- **Coverage threshold drift**: 90% today, but if new code is harder to test, the threshold may need adjustment. That requires changing `pyproject.toml` and workflow — intentional friction to ensure the team discusses it.
