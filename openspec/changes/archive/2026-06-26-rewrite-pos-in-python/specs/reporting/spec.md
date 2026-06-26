## ADDED Requirements

### Requirement: Sales reports
The system SHALL generate sales performance reports.

#### Scenario: Sales by date range
- **WHEN** user requests sales report for date range
- **THEN** report shows total sales, items sold, and average transaction value

#### Scenario: Sales by employee
- **WHEN** user requests sales report by employee
- **THEN** each employee's sales total and count are displayed

#### Scenario: Sales by payment type
- **WHEN** user requests sales by payment type
- **THEN** totals are broken down by cash, card, and other methods

### Requirement: Inventory reports
The system SHALL generate inventory status reports.

#### Scenario: Stock level report
- **WHEN** user requests stock level report
- **THEN** all items shown with current quantity and status (in stock, low, out)

#### Scenario: Inventory valuation
- **WHEN** user requests inventory valuation
- **THEN** total inventory value calculated using average cost

#### Scenario: Items below reorder point
- **WHEN** user requests reorder report
- **THEN** items below reorder threshold are listed with recommended order quantity

### Requirement: Expense reports
The system SHALL generate expense reports.

#### Scenario: Expense summary by period
- **WHEN** user requests expense report for period
- **THEN** total expenses shown with breakdown by category

### Requirement: Customer reports
The system SHALL generate customer activity reports.

#### Scenario: Customer sales summary
- **WHEN** user requests customer sales summary
- **THEN** customers listed with total purchases and last purchase date

#### Scenario: Customer balance report
- **WHEN** user requests outstanding balances
- **THEN** customers with receivable balances are shown