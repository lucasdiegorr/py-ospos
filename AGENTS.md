# Agents

This document provides guidance for agents working on this repository.

## Project Overview

py-ospos is a Python rewrite of [Open Source Point of Sale (OSPOS)](https://github.com/opensourcepos/opensourcepos), written in PHP using CodeIgniter. This project re-implements all OSPOS functionality using a modern Python stack.

## Tech Stack

- **Framework**: FastAPI (async-first, OpenAPI auto-docs)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Authentication**: OAuth2 with JWT tokens
- **Container**: Docker + Docker Compose

### Important: Use Official FastAPI Skill

When working with FastAPI, load the skill: `fastapi`

Key conventions from the FastAPI skill:

- Use `Annotated` for parameter and dependency declarations
- Do NOT use `...` (Ellipsis) as default value for required parameters
- Include return types or `response_model` on endpoints
- Use `async def` only when code inside is truly async-compatible; otherwise use `def`
- Prefer router-level prefix/tags over `include_router()` parameters
- Do NOT use `ORJSONResponse` or `UJSONResponse` (deprecated)
- Do NOT use Pydantic `RootModel`; use regular type annotations with `Annotated`

## Workflow

### Branching Strategy

- **NEVER commit directly to `master`**
- All changes go through branches and pull requests
- Create a branch for each feature, fix, or task: `git checkout -b <type>/<description>`

### Commit Convention

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Commit Message Format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks
- `revert`: Reverting changes

**Examples:**
```
feat(auth): add JWT token refresh endpoint
fix(sale): correct change calculation for partial payments
docs(api): add authentication endpoint documentation
refactor(item): use SQLAlchemy async session
chore: update PostgreSQL base image
```

**Rules:**
- Description uses imperative mood (e.g., "add", not "added")
- Scope is optional but recommended (e.g., `feat(auth)`, `fix(sale)`)
- Include body for additional context
- Use footer for breaking changes or issue references: `BREAKING CHANGE: ...`

### Pull Request Process

1. Create feature branch from `master`: `git checkout -b <type>/<description>`
2. Make focused, small commits (baby steps)
3. Open PR with clear description
4. Ensure all checks pass
5. Request review
6. Squash and merge after approval
7. **After PR is merged:**
   - Delete the feature branch: `git branch -d <branch> && git push origin --delete <branch>`
   - Return to master: `git checkout master`
   - Update local repo: `git pull upstream master`

## Project Structure

```
py-ospos/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── core/             # Config, security, exceptions
│   ├── db/               # Database connection, session
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic layer
│   └── main.py           # FastAPI application entry
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docker/               # Docker configuration
├── docker-compose.yml    # Development environment
├── openspec/             # Change specifications
│   ├── changes/          # Change artifacts (proposals, specs, tasks)
│   └── specs/            # Capability specifications
└── .agents/              # Agent skills and instructions
    └── skills/
        ├── fastapi/          # FastAPI best practices
        ├── frontend-design/   # UI design patterns
        └── conventional-commit/  # Commit conventions
```

## Available Skills

Load these skills when relevant:

- `fastapi` - FastAPI best practices and patterns
- `frontend-design` - Frontend UI development
- `conventional-commit` - Commit message conventions

## Development Setup

### Docker Compose (recommended)

```bash
docker-compose up -d
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
fastapi dev
```

### Running Tests

```bash
pytest
```

## Documentation Standards

All documentation MUST be written in **English**, including:
- Code comments
- README files
- API documentation
- Commit messages
- PR descriptions

## Reference Documents

- OSPOS original project: https://github.com/opensourcepos/opensourcepos
- FastAPI skill: `.agents/skills/fastapi/SKILL.md`
- Conventional Commits: https://www.conventionalcommits.org/