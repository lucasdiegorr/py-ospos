## Context

The py-ospos backend exposes a REST API at `/api/v1/` with 62 endpoints covering auth, customers, employees, expenses, invoices, items, quotations, and sales. There is no frontend — this project builds one from scratch as a Next.js application in a `frontend/` directory.

The frontend targets cashiers, managers, and administrators who need a fast, responsive POS interface that works on desktop tablets and mobile devices.

## Goals / Non-Goals

**Goals:**
- Full-featured POS interface: cart management, item lookup (by name and barcode), checkout, suspend/recall sales
- Management CRUD screens for all domain entities
- JWT-based authentication with token persistence
- Light/dark theme via CSS custom properties, persisted in localStorage
- Responsive layout: sidebar navigation on desktop, bottom nav on mobile
- SVG icons only (lucide-react), no raster images
- Type scale as the primary visual hierarchy tool

**Non-Goals:**
- Offline support or PWA (future concern)
- Real-time updates via WebSocket (API is request-response only)
- Multi-language i18n (can be added later)
- End-to-end or visual regression tests (first pass focuses on functionality)

## Decisions

1. **Next.js App Router with client components** — The POS cart is highly interactive (add/remove items, real-time totals). Using `"use client"` for interactive pages keeps the code simple. Server components used for static layout shell.

2. **Tailwind CSS for styling** — Utility-first approach pairs well with the design system token approach. CSS custom properties for theme colors enable seamless light/dark switching without a build step.

3. **`next-themes` for theme toggle** — Wraps Tailwind's dark mode (`class` strategy). Persists preference in localStorage, respects system preference on first visit, avoids flash on reload.

4. **`lucide-react` for icons** — Consistent, tree-shakeable, MIT-licensed SVG icon set. No icon font or image assets needed.

5. **Fetch-based API client (no Axios)** — A thin wrapper around the native `fetch` API with JWT token injection, refresh logic, and error handling. Keeps bundle small.

6. **Directory structure** — App Router with route groups:
   - `(auth)/` — login page
   - `(dashboard)/` — sidebar layout with management pages
   - `pos/` — full-screen POS interface (no sidebar chrome)

7. **TypeScript** — Strict mode. Shared types mirror backend schemas for customers, items, sales, etc.

8. **Auth guard via middleware + context** — A `useAuth` context provides the current user and login/logout methods. A Next.js middleware checks for the token on every request and redirects to `/login` if missing. After login, the app redirects to `/`.

9. **Role-based feature gating** — The auth context exposes `user.isAdmin` (mapped from `is_admin`). A `<RequireAuth>` wrapper component accepts an optional `permissions` prop. For now, only `isAdmin` is checked; the permission system is designed as a lookup (`user.can('sales_create')`) so granular backend permissions can be wired in later without refactoring the UI.

## Token System (from frontend-design skill)

**Palette:**
- Background (light): `#FAFAF9` (warm off-white)
- Background (dark): `#0C0C0C` (near-black, not pure #000)
- Surface light: `#FFFFFF`, Surface dark: `#1A1A1A`
- Accent: `#2563EB` (blue-600) — accessible, calm, appropriate for retail
- Accent hover: `#1D4ED8` (blue-700)
- Success: `#059669` (emerald-600)
- Danger: `#DC2626` (red-600)
- Text light: `#18181B`, Text dark: `#FAFAFA`

**Typography:**
- Display/Headings: **Inter** (variable weight, geometric, excellent legibility at small sizes — critical for POS)
- Body/Mono: **JetBrains Mono** for prices, quantities, codes (tabular figures align perfectly in columns)
- Hierarchy: 3-step scale (title, body, caption) with font-weight doing the heavy lifting instead of size jumps

**Layout:**
- Desktop: fixed left sidebar (240px), main content area, optional right panel for cart
- Mobile: bottom navigation bar, stacked full-width pages
- POS mode: full-screen, three-column (item grid | cart | totals) on wide screens, single-column on mobile

**Signature element:**
- The price display uses JetBrains Mono with a distinctive green `#059669` color and a subtle `font-variant-numeric: tabular-nums` — this makes the POS feel precise and trustworthy, like a real register.

## Risks / Trade-offs

- **Client-side rendering for POS**: Without SSR, the initial load of the POS page depends on JS execution. Mitigation: critical pages (login, dashboard) use RSC where possible so the shell renders instantly.
- **No API caching layer**: Every request hits the backend directly. If the API is slow, the UI feels sluggish. Mitigation: add client-side SWR/React Query in a follow-up if needed.
- **Theme flash on reload**: `next-themes` handles this, but only if configured correctly with the `suppressHydrationWarning` attribute.

## Testing Strategy

- **Framework**: Vitest + React Testing Library (fast, native TypeScript, compatible with Next.js)
- **Unit tests**: API client wrapper, auth context, utility functions
- **Component tests**: Each reusable component (Button, Input, Modal, DataTable) rendered in isolation with props, covering states (empty, loading, error, edge cases)
- **Integration tests**: Full-page flows like login → redirect, CRUD create → table refresh, POS add item → cart update
- **No E2E in first pass**: Playwright can be added later; component/integration tests cover the critical paths
- **CI**: Reuse existing GitHub Actions workflow, adding a job for `cd frontend && npm test -- --coverage`
