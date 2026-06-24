## Why

Open Source Point of Sale (OSPOS) is a well-established PHP application with 4.3k stars. Rewriting it in Python using a modern stack (FastAPI, PostgreSQL, Docker) addresses technical debt, improves maintainability, enables better type safety, and opens the project to Python developers.

## What Changes

- Complete rewrite of OSPOS in Python 3.11+ using FastAPI
- Migration from MySQL to PostgreSQL database
- Docker-first development and deployment
- REST API architecture replacing PHP CodeIgniter
- Modern async-first design patterns

## Capabilities

### New Capabilities

- `authentication`: User login, session management, permission-based access control
- `customer`: Customer and supplier database management
- `item`: Items and kits management with extensible attributes
- `sale`: Point-of-sale register with transaction logging
- `quotation`: Quote creation and conversion
- `invoice`: Invoice generation and status tracking
- `expense`: Expense logging and categorization
- `receiving`: Stock receiving from suppliers
- `gift-card`: Gift card issuance and redemption
- `rewards`: Customer loyalty points system
- `employee`: Multiuser support with role-based permissions
- `reporting`: Sales, inventory, and expense reports
- `tax`: Multi-tier VAT/GST taxation
- `barcode`: Barcode generation and printing
- `printing`: Receipt, invoice, quotation printing
- `messaging`: SMS notification support
- `restaurant-table`: Restaurant table management
- `localization`: Multi-language support
- `settings`: System configuration

### Modified Capabilities

<!-- No existing specs - all capabilities are new -->

## Impact

- **New stack**: FastAPI + PostgreSQL + Docker replaces PHP + MySQL
- **API-first**: REST API enables future mobile apps and integrations
- **No backward compatibility**: This is a rewrite, not an upgrade