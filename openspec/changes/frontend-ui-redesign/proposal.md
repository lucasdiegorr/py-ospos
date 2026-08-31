## Why

The current frontend (`frontend/src/`) is a hand-rolled React 18 + Vite SPA with a single 218-line plain CSS file (`index.css`), no design tokens, no component library, and a utilitarian look built around sticky horizontal tabs. Although the underlying business behavior (offline-first outbox, multi-page capability set, role-based access) is solid, the surface area is not presentation-ready: there are no cards, no proper tables, no sidebar, no dark mode, and the visual identity is reduced to a single accent color (`#2f81f7`) with no semantic structure. Users testing the system have flagged the UI as visually weak and harmful to perceived quality.

We need a redesigned UI for the user-facing core surfaces (login, app shell, point-of-sale, cash register) that:

1. Looks like a professional product, not a prototype.
2. Is fully accessible (keyboard nav, focus rings, ARIA-correct components).
3. Is theme-able (light + dark mode in this PR, with tokenized colors so future themes are cheap).
4. Adds zero new backend dependencies and does not change any business behavior.
5. Leaves non-core pages (Customers, Products, Reports) for a follow-up PR so this PR stays reviewable.

## What Changes

- Add **Tailwind CSS**, **PostCSS**, **Autoprefixer**, and **shadcn/ui** (Radix primitives + Tailwind component recipes) to the frontend toolchain.
- Introduce a tokenized design system (CSS variables for colors, radius, spacing) bound to Tailwind's theme; preserve the existing brand blue (`#2f81f7`) as the primary accent.
- Replace the global stylesheet `frontend/src/index.css` with a Tailwind base file plus token definitions.
- Rebuild the **AppShell**: convert the horizontal `<nav class="tabs">` into a left **sidebar** (collapsible drawer on mobile) plus a **topbar** containing the brand wordmark, offline-sync badge, and user/role/sair controls.
- Migrate three **core pages** to shadcn/ui primitives (Card, Button, Input, Label, Select, Table, Dialog, DropdownMenu, Separator):
  - `pages/Login.tsx` — centered card with form, error banner, and loading state.
  - `pages/Pos.tsx` — catalog grid (product cards), right-hand cart panel, payment-method selector, receipt card, offline queue indicator.
  - `pages/Shift.tsx` — open-shift summary table, supply/withdraw forms, close-shift panel with counted-money fields and difference visualization.
- Implement **dark mode** via a `.dark` class on `<html>` toggled from a button in the topbar; theme state persists in `localStorage`.
- Keep Customers, Products, Reports pages untouched in this PR (their plain-CSS look remains) — no compatibility risk.

No business logic changes:

- Authentication flow, JWT handling, role-based gating: unchanged.
- Outbox/sync semantics (`outbox.ts`, `outbox-changed` event, online/offline flush): unchanged.
- API contracts: unchanged.
- Portuguese (pt-BR) UI copy: preserved across all migrated surfaces.

## Capabilities

### New Capabilities

_None._ This change does not introduce new product capabilities; it only restructures how existing surfaces are rendered.

### Modified Capabilities

- `auth`: Login form must be presented as an accessible, centered card with explicit error/feedback states and keyboard-navigable inputs (current text-only inline form has no focus ring, no error region).
- `sales`: PDV must present the product catalog as a searchable grid of cards, the cart as a persistent right-hand panel with line-item controls, and the payment/payment-split UI as a dedicated card with method selection and amount input. The receipt output remains a monospaced preformatted block. (Current implementation is a stacked single-column layout with no card surfaces.)
- `cash-register`: Caixa must present open-shift status, supply (suprimento) / withdraw (sangria) forms, and close-shift panels as distinct cards with explicit tables for movements; counted-money input and the resulting difference must be visually distinct (green when zero/positive, red when negative).

## Impact

**Affected code:**

- `frontend/package.json` — add Tailwind, PostCSS, Autoprefixer, shadcn/ui components, Radix primitives; add `cn` utility.
- `frontend/vite.config.ts` — wire Tailwind/PostCSS plugin.
- `frontend/postcss.config.cjs` (new) — PostCSS pipeline.
- `frontend/tailwind.config.cjs` (new) — theme tokens, content globs, dark-mode strategy.
- `frontend/src/index.css` — replaced with Tailwind directives + CSS variable definitions for `:root` and `.dark`.
- `frontend/src/lib/utils.ts` (new) — `cn()` helper from shadcn.
- `frontend/src/components/ui/*` (new) — generated shadcn primitives.
- `frontend/src/App.tsx` — new `AppShell` with sidebar + topbar + theme toggle.
- `frontend/src/pages/Login.tsx` — migrated to shadcn Card/Input/Button/Label/Alert.
- `frontend/src/pages/Pos.tsx` — migrated to shadcn Card/Input/Button/Select/Tabs/Separator.
- `frontend/src/pages/Shift.tsx` — migrated to shadcn Card/Button/Input/Label/Table/Badge.
- `frontend/src/auth.tsx` — no behavior change; only consumer update if necessary.
- `frontend/src/App.test.tsx` — may need updates if selectors/queries change; behavior coverage preserved.

**Affected specs:** `auth`, `sales`, `cash-register` (deltas).

**Affected APIs:** none.

**New dependencies (devDependencies):**

- `tailwindcss`, `postcss`, `autoprefixer`
- `tailwindcss-animate` (for shadcn animations)
- `class-variance-authority`, `clsx`, `tailwind-merge` (shadcn helpers)
- Radix primitives consumed by shadcn components (`@radix-ui/react-*` as needed)

**Build/dev impact:** `npm run build` and `npm run dev` continue to work; bundle size increases due to Tailwind classes + Radix primitives (~tens of kB gzipped). Docker build is unaffected (`Dockerfile` already runs `npm run build` and Nginx serves the static `dist/`).

**Out of scope:** Customers, Products, Reports pages; backend changes; internationalization beyond preserving pt-BR; mobile-app-style gesture polish; accessibility audit beyond Radix's built-in semantics.
