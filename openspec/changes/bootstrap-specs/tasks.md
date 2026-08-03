## 1. Foundation

- [x] 1.1 Scaffold monorepo: FastAPI backend, React+TS (Vite) frontend, PostgreSQL schema, docker-compose dev environment
- [x] 1.2 Define base domain primitives: money as integer cents, timestamps, idempotency keys
- [x] 1.3 Centralize role-based access control helper (attendant/manager/admin) used by all endpoint modules
- [x] 1.4 Set up CI: lint, type-check, and test commands for backend and frontend

## 2. auth

- [ ] 2.1 Implement login endpoint: verify credentials, issue access + refresh tokens, record failed attempts
- [ ] 2.2 Implement refresh-token rotation and logout (revoke refresh token)
- [ ] 2.3 Implement lockout after repeated failed attempts with configurable cooldown
- [ ] 2.4 Encode user id + role in access token claims; reject expired/malformed tokens
- [ ] 2.5 Test all auth scenarios from specs/auth/spec.md

## 3. users

- [ ] 3.1 Implement user CRUD (create, edit, deactivate/reactivate, list/search) restricted by role
- [ ] 3.2 Enforce role rules: only admin manages users; protect last active admin
- [ ] 3.3 Implement admin password reset and self password change requiring current password
- [ ] 3.4 Test all users scenarios from specs/users/spec.md

## 4. customers

- [ ] 4.1 Implement customer registration with minimal data and optional/partial address fields
- [ ] 4.2 Implement customer search by name/CPF/phone
- [ ] 4.3 Implement fiado profile (credit limit, interest, due period) with at-least-one-field validation
- [ ] 4.4 Implement customer purchase history and outstanding fiado balance view
- [ ] 4.5 Test all customers scenarios from specs/customers/spec.md

## 5. products

- [ ] 5.1 Implement product catalog CRUD with SKU uniqueness and categories
- [ ] 5.2 Implement packaging model: base unit + pack with quantity and separate price
- [ ] 5.3 Implement optional expiration attribute on products/stock
- [ ] 5.4 Implement product search showing price and availability
- [ ] 5.5 Test all products scenarios from specs/products/spec.md

## 6. inventory

- [ ] 6.1 Implement manual stock entry with optional expiration and movement log
- [ ] 6.2 Implement sale-driven stock outflow in base units (unit and pack)
- [ ] 6.3 Implement automatic pack break with base-unit invariant
- [ ] 6.4 Implement low-stock threshold flag and expiration alert window
- [ ] 6.5 Implement stock adjustment with reason and chronological movement history
- [ ] 6.6 Test all inventory scenarios from specs/inventory/spec.md

## 7. payments

- [ ] 7.1 Implement payment-method registry (cash/card/PIX/fiado) with enable/disable
- [ ] 7.2 Implement per-sale payment recording (split payments, card installments)
- [ ] 7.3 Implement fiado payment linkage: balance increase + credit-limit validation
- [ ] 7.4 Implement PIX manual registration without gateway integration
- [ ] 7.5 Implement per-method payment totals per shift
- [ ] 7.6 Test all payments scenarios from specs/payments/spec.md

## 8. sales

- [ ] 8.1 Implement cart building (unit/pack selection) and cart total computation
- [ ] 8.2 Implement atomic sale completion: items + payments, stock decrement, shift attribution
- [ ] 8.3 Implement fiado payment flow within sale (customer required, limit check)
- [ ] 8.4 Implement optional delivery attachment without freight
- [ ] 8.5 Implement non-fiscal receipt for Bluetooth thermal printer
- [ ] 8.6 Implement offline sale completion: local finalization + outbox queue (sync capability)
- [ ] 8.7 Implement sale search/detail and manager/admin sale cancellation with stock restore
- [ ] 8.8 Test all sales scenarios from specs/sales/spec.md

## 9. deliveries

- [ ] 9.1 Implement delivery registration on sale with partial-address optional fields
- [ ] 9.2 Implement delivery status tracking (pending → in-transit → delivered)
- [ ] 9.3 Implement delivery list filtered by status/date
- [ ] 9.4 Test all deliveries scenarios from specs/deliveries/spec.md

## 10. cash-register

- [ ] 10.1 Implement shift open with starting float and single-active-shift rule
- [ ] 10.2 Attribute sales to active shift; require shift open before sale
- [ ] 10.3 Implement cash supply (suprimento) and bleed (sangria) with reason
- [ ] 10.4 Implement expected-cash calculation (float + cash sales + supplies − bleeds)
- [ ] 10.5 Implement shift close with counted cash and difference recording
- [ ] 10.6 Implement shift summary (payment-method totals, supplies, bleeds, expected/counted/difference)
- [ ] 10.7 Test all cash-register scenarios from specs/cash-register/spec.md

## 11. reporting

- [ ] 11.1 Implement sales-by-period report (day/week/month, range)
- [ ] 11.2 Implement best-sellers report (quantity + revenue)
- [ ] 11.3 Implement low-stock/expiring report
- [ ] 11.4 Implement open-fiados report with oldest-debt
- [ ] 11.5 Implement cash-flow report (in/out, supply/bleed, balance)
- [ ] 11.6 Implement margin-per-product report (cost-aware)
- [ ] 11.7 Implement pending-sync notice reading outbox count from sync capability
- [ ] 11.8 Enforce report access to managers/admins
- [ ] 11.9 Test all reporting scenarios from specs/reporting/spec.md

## 12. sync (cross-cutting)

- [ ] 12.1 Implement durable local outbox for writes (survives restart)
- [ ] 12.2 Implement idempotency keys on outbox entries and server-side deduplication
- [ ] 12.3 Implement sync-on-reconnect push in creation order
- [ ] 12.4 Implement conflict detection with documented reconciliation rules (stock sync order, price-at-sale preserved)
- [ ] 12.5 Implement pending-sync count exposure for reporting UI
- [ ] 12.6 Implement permanent-failure resolution queue for managers
- [ ] 12.7 Test all sync scenarios from specs/sync/spec.md

## 13. Frontend integration

- [ ] 13.1 Build responsive app shell (login, role-based navigation) for phone/tablet/monitor
- [ ] 13.2 Build POS screen: product search, cart, payment split, fiado customer picker
- [ ] 13.3 Build customer and product management screens
- [ ] 13.4 Build shift open/close screen with expected-vs-counted reconciliation
- [ ] 13.5 Build reports screens with pending-sync notice
- [ ] 13.6 Wire offline handling: local outbox usage + reconnect sync trigger
- [ ] 13.7 End-to-end test of a full day: open shift, sell (online + offline), close shift, view reports
