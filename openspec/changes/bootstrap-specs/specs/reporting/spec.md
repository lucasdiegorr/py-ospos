## Purpose

Provides the store owner with management reports: sales by period, best sellers, critical/expiring stock, open fiados, cash flow, and margin per product. Reports are generated from server data and SHALL indicate when some local (offline) sales have not yet been synchronized.

## ADDED Requirements

### Requirement: Sales report by period
The system SHALL produce a report of sales totals and counts grouped by day, week, or month, over a configurable date range.

#### Scenario: Daily sales summary
- **WHEN** a manager requests sales for a given day
- **THEN** the report shows total revenue, number of sales, and average ticket for that day

### Requirement: Best sellers report
The system SHALL report the top-selling products by quantity and revenue over a configurable period.

#### Scenario: Top products ranked
- **WHEN** a manager requests the best-sellers report for the last 30 days
- **THEN** the report lists products ordered by quantity sold, showing quantity and revenue each

### Requirement: Low-stock and expiring report
The system SHALL report products at or below minimum stock and products with stock expiring within a configurable window or already expired.

#### Scenario: Combined critical report
- **WHEN** a manager requests the critical-stock report
- **THEN** it shows low-stock products and dated products nearing or past expiration, with quantities

### Requirement: Open fiados report
The system SHALL report customers with outstanding fiado balances, including their balances and days since the oldest outstanding debt.

#### Scenario: Open fiado listing
- **WHEN** a manager requests the open fiados report
- **THEN** it lists customers with balances, oldest outstanding debt, and total owed

### Requirement: Cash flow report
The system SHALL report cash inflow and outflow across shifts or days, including sales revenue, supply and bleed (sangria/suprimento), and the resulting balance.

#### Scenario: Daily cash flow
- **WHEN** a manager requests the cash-flow report for a day
- **THEN** it shows money in (sales, supply) and money out (bleed, expenses) with a net balance

### Requirement: Margin per product report
The system SHALL report per-product revenue and, when a cost price is recorded, the margin.

#### Scenario: Products with and without cost
- **WHEN** a manager requests the margin report
- **THEN** products with a recorded cost price show margin; those without show revenue only

### Requirement: Pending-sync indication
Reports SHALL be computed from server data and SHALL display a notice when local sales exist that have not yet been synchronized, including the count of pending sales.

#### Scenario: Pending sales notice
- **WHEN** a report is generated while N local sales are still pending synchronization
- **THEN** the report displays a notice stating that data may be incomplete and that N sales have not yet been synchronized

#### Scenario: Fully synced report
- **WHEN** a report is generated with no pending local sales
- **THEN** no pending-sync notice is shown

### Requirement: Role access to reports
The system SHALL restrict report access to managers and admins; attendants SHALL NOT open reports.

#### Scenario: Attendant denied
- **WHEN** a user with role `attendant` requests a report
- **THEN** the system denies access
