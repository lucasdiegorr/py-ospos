## 1. Project Setup

- [x] 1.1 Initialize Next.js project with App Router, TypeScript, and Tailwind CSS
- [x] 1.2 Install dependencies: lucide-react, next-themes
- [x] 1.3 Configure Tailwind with dark mode class strategy and custom theme tokens
- [x] 1.4 Set up project folder structure (route groups, components, lib, types)

## 2. Design System (UI Kit)

- [x] 2.1 Create theme provider with next-themes and CSS custom properties for light/dark
- [x] 2.2 Implement base layout shell (sidebar desktop, bottom nav mobile)
- [x] 2.3 Build reusable components: Button, Input, Select, Modal, Table, Card
- [x] 2.4 Build global navigation (sidebar with links, bottom nav, theme toggle)
- [x] 2.5 Create API client wrapper with fetch, JWT injection, and error handling

## 3. Authentication

- [x] 3.1 Build login page with form validation and error display
- [x] 3.2 Implement JWT token storage and auth context provider
- [x] 3.3 Implement auth context (useAuth hook with user, login, logout, isAuthenticated)
- [x] 3.4 Add client-side redirect in dashboard layout (middleware not viable: edge can't read localStorage)
- [x] 3.5 Add token refresh logic on 401 responses
- [x] 3.6 Build post-login redirect to home/dashboard
- [x] 3.7 Implement role-based navigation: admin sees all links, non-admin sees limited set

## 4. Management CRUD Pages

- [x] 4.1 Build reusable DataTable component with pagination and search
- [x] 4.2 Build reusable EntityForm component with validation
- [x] 4.3 Implement Customer management page (list, create, edit, delete)
- [x] 4.4 Implement Item management page (list, create, edit, delete)
- [x] 4.5 Implement Employee profile page (no backend list endpoint; shows current user info)
- [x] 4.6 Implement Expense management page (list, create, edit, delete)
- [x] 4.7 Implement Invoice management page (list, view details)
- [x] 4.8 Implement Quotation management page (list, create, edit, delete)

## 5. POS Interface

- [x] 5.1 Build full-screen POS layout with three-column grid
- [x] 5.2 Implement item search component (by name and barcode)
- [x] 5.3 Implement cart component (items list, quantities, remove, totals)
- [x] 5.4 Implement checkout flow (complete sale, receipt display)
- [x] 5.5 Implement suspend/recall sale functionality

## 6. Testing

- [x] 6.1 Set up Vitest and React Testing Library with Next.js compatibility
- [x] 6.2 Write unit tests for API client (token injection, refresh, error handling)
- [x] 6.3 Write component tests for reusable UI components (Button, Input, Modal, Table)
- [x] 6.4 Write component tests for login page (validation, success, error states)
- [x] 6.5 Write component tests for DataTable (pagination, search, empty state)
- [ ] 6.6 Write integration tests for management CRUD flows
- [ ] 6.7 Write integration tests for POS cart (add, remove, quantity, totals)
- [x] 6.8 Configure CI to run frontend tests on the existing GitHub Actions workflow
