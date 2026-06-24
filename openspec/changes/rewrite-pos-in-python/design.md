## Context

Open Source Point of Sale (OSPOS) rewrite using Python 3.11+ with FastAPI.

### Tech Stack

- **Framework**: FastAPI (async-first, OpenAPI auto-docs)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Authentication**: OAuth2 with JWT tokens
- **Container**: Docker + Docker Compose

## Goals / Non-Goals

**Goals:**
- Preserve all OSPOS business logic and workflows
- Achieve feature parity with OSPOS 3.4
- Async-first architecture for better concurrency
- Docker-first development experience
- API-first design enabling future mobile/web clients

**Non-Goals:**
- Backward compatibility with OSPOS PHP
- Support for MySQL (PostgreSQL only)

## Decisions

### 1. FastAPI over Django/Flask
**Rationale**: Native async support, automatic OpenAPI documentation, Pydantic validation.

### 2. SQLAlchemy 2.0 async
**Rationale**: Mature ORM with async support, Alembic migrations.

### 3. JWT over session-based authentication
**Rationale**: Stateless, scalable, supports refresh tokens.

### 4. Docker Compose for local development
**Rationale**: Dev/prod parity, easy onboarding.

## Open Questions

1. Should we implement WebSocket for real-time POS display updates?
2. What email/SMS service provider to use?
3. Do we need offline POS capability (PWA)?