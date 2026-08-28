## Context

This is a greenfield rewrite of the opensourcepos (CodeIgniter/PHP monolith) for a small beverage warehouse. The domain is small (1-2 attendants), the location has unstable internet, and the owner works primarily from a mobile device. See proposal.md for the motivation; the specs define what each capability must do.

## Goals / Non-Goals

**Goals:**
- Define an architecture that supports a mobile-first POS that works offline (sales close locally, sync later).
- Keep capabilities independently implementable so agents can work in parallel worktrees.
- Preserve the decision that fiado is a first-class payment method in the MVP.
- Design for the reality of 1-2 attendants: conflicts are rare, so heavy conflict machinery is not warranted.

**Non-Goals:**
- Fiscal/legal compliance (NFC-e, XML import) — explicitly deferred.
- Delivery freight calculation and external delivery integration — deferred.
- Loyalty/fidelity program — deferred.
- Multi-tenant or franchise support — single-store scope.
- Real-time push synchronization; outbox-style eventual consistency is sufficient.

## Decisions

### Backend: FastAPI + SQLAlchemy on PostgreSQL
Monolith first, not microservices. All capabilities live in one FastAPI app with module boundaries. Rationale: the store is small; a monolith avoids distributed-systems complexity while keeping modules cleanly separated so parallel worktrees don't conflict. Alternatives considered: microservices (rejected — overhead for 1-2 users), Go backend (rejected — team is Python-centric).

### Frontend: React + TypeScript (Vite)
One SPA for both the POS terminal and management views, responsive for phone/tablet/monitor. Rationale: one codebase for PDV and reporting, mobile-first by design. The POS must be usable on a small screen with a large touch target for rapid selling. Alternatives considered: separate POS and admin apps (rejected — more duplication), server-rendered (rejected — offline-first needs a rich client).

### Offline-first: local outbox + sync-on-reconnect (not CRDT)
Writes are stored locally (indexed in the client or an embedded store), persisted in an outbox, and pushed to the server in order on reconnect with idempotency keys. Conflicts are resolved by documented rules (e.g., stock decrements apply in sync order; price-at-sale is preserved). Rationale: 1-2 attendants means simultaneous-offline conflicts are rare; a full CRDT would add complexity disproportionate to the need. Alternatives considered: CRDTs (rejected — over-engineering for the conflict rate), last-writer-wins with silent overwrite (rejected — silent data loss is unacceptable for stock/fiado).

### JWT stateless access tokens with refresh-token rotation
Short-lived access tokens encode user id and role; refresh tokens are server-side revocable. Rationale: stateless auth works across the SPA and keeps role checks cheap. Refresh rotation bounds token lifetime.

### Fiado modeled as a customer sub-aggregate
Customer holds the fiado profile (credit limit, interest, due period — at least one required) plus the outstanding balance. Sales reference the customer; fiado payments mutate the balance with a limit check. Rationale: keeps fiado rules co-located with the customer it depends on, and makes the "fiado requires customer" invariant enforceable at one place.

### Product/pack stock in base units
Stock is counted in base units; a pack is a quantity of base units. Selling a pack decrements by pack size; selling a unit from only-whole-packs stock triggers an automatic pack break (1 pack → its units added to loose stock, then unit sold). Rationale: single stock ledger avoids double-counting and makes the pack-break rule a simple, testable invariant. Alternatives considered: separate pack and unit stock lines (rejected — drift between the two is a correctness risk).

### Shift lifecycle owned by cash-register, referenced by sales
Sales belong to a shift; the shift aggregates per-method payment totals and supply/bleed movements and computes expected cash at close. Rationale: keeps the closing-reconciliation rule in one place. Sales remain independent records so offline sales created without an open shift still complete and later reconcile.

### Reports read server data, never claim real-time completeness
Reports are computed from the server's known data and always show a pending-sync notice when the outbox has entries. Rationale: honest data for the owner; avoids a false "live" report. This is a product decision, not a bug — reflected in the reporting spec.

### Role model: three fixed roles, enforced server-side
`attendant`, `manager`, `admin`. Role checks are centralized (dependency-injected into endpoints), not scattered. Attendants cannot create products, cancel sales, or open reports. Rationale: a single enforcement point keeps the parallel-implementation worktree contract simple.

## Risks / Trade-offs

- **Offline conflicts are possible even if rare** → Documented reconciliation rules (sync order for stock, price-at-sale preserved) and a manager-facing resolution queue for permanent failures. Not fully automated, but the failure surface is small for 1-2 attendants.
- **Monolith can grow unmaintainable** → Strong capability module boundaries from day one; the spec-per-capability structure maps 1:1 to module boundaries, and worktrees keep agents from crossing them.
- **Pack-break rule has edge cases (multiple packs, partial packs)** → Spec requires the invariant be expressed in base units; implementation must expose a single stock-adjustment primitive tested against those cases.
- **No fiscal compliance in MVP** → Owner operates with a non-fiscal receipt; a future change can add NFC-e/XML without restructuring the data model (deliveries already keep address data).
- **Refresh-token rotation adds a little server state** → Acceptable: keeps logouts and revocation real, which fiado and role changes need.
