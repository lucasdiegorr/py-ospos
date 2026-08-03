## Why

A new POS/ERP system for a small beverage warehouse needs to start from a clean, well-scoped specification foundation. The reference project (opensourcepos) is a CodeIgniter/PHP monolith; this rewrite targets FastAPI + React/TypeScript + PostgreSQL with offline-first behavior. Before any implementation begins, we need complete, validated specifications so each capability can be implemented independently in parallel worktrees without conflicts and with clear acceptance criteria.

## What Changes

- Define **11 new capabilities** covering the full domain (auth, users, customers, products, inventory, sales, payments, deliveries, reporting, sync, cash-register).
- Establish spec-level contracts that serve as the contract for parallel implementation worktrees.
- Set the architectural baseline: JWT stateless auth, offline-first via outbox + reconciliation, PostgreSQL persistence, mobile-friendly React UI.
- No code changes yet — this change produces the specification artifacts only; implementation will follow in separate changes.

## Capabilities

### New Capabilities

- `auth`: Authentication and JWT lifecycle (login, refresh, logout, lockout).
- `users`: User accounts with three roles (attendant, manager, admin) and profile management.
- `customers`: Customer registration with minimum required data, anonymous sales support, fiado linkage.
- `products`: Product catalog with packaging (unit/pack), optional expiration, categories, pricing.
- `inventory`: Stock movements (manual entry, sale-driven outflow), low-stock and expiration alerts, automatic pack break.
- `sales`: Point-of-sale flow — cart, payment methods, optional delivery, fiado registration, offline-capable.
- `payments`: Payment methods registry (cash, card, PIX, fiado) and per-sale payment recording.
- `deliveries`: Delivery registration (own delivery) with optional partial address, no freight calculation.
- `reporting`: Seven reports (sales by period, top sellers, low/expiring stock, open fiados, cash flow, commission, margin) with sync-pending indicator.
- `sync`: Cross-cutting outbox + reconciliation for offline-first behavior, referenced by other capabilities.
- `cash-register`: Cash shift lifecycle — open with float, register sales, supply/bleed, close with reconciliation.

### Modified Capabilities

None — this is the initial spec set; no existing specs to modify.

## Impact

- No code yet — specification artifacts only.
- Future implementation changes will be scoped per capability so multiple agents can work in separate worktrees.
- Establishes naming, domain language, and behavioral contracts that all subsequent changes must respect.
- The `sync` capability is cross-cutting; other capabilities reference it rather than duplicating offline behavior.
