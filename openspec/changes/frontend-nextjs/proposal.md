## Why

The project currently has no user interface — only a REST API. A responsive Next.js frontend is needed to make the POS system usable by real cashiers, managers, and administrators.

## What Changes

- Create a new Next.js application in a `frontend/` directory at the project root
- Implement authentication pages (login, session management)
- Build a Point of Sale interface (cart, item lookup, checkout)
- Build management screens (customers, items, employees, expenses, invoices, quotations)
- Responsive layout with light/dark theme support
- Use SVG icons and typography-based design (no raster images)
- Consume all existing API endpoints under `/api/v1/`

## Capabilities

### New Capabilities

- `ui-kit`: Design system with reusable components, theme (light/dark), responsive layout, and typography scale
- `auth-ui`: Login page, token management, and session persistence
- `pos-ui`: Interactive POS cart with item search, barcode scan, quantity management, checkout, and receipt view
- `management-ui`: CRUD pages for customers, items, employees, expenses, invoices, and quotations with search, pagination, and forms

### Modified Capabilities

<!-- No existing capabilities are modified -->

## Impact

- New directory: `frontend/` with Next.js App Router project
- New dependencies: Node.js, React, Next.js, Tailwind CSS, lucide-react (icons), next-themes (dark mode)
- No changes to existing backend code or API
- Development requires Node.js 20+ and package manager (pnpm/npm)
