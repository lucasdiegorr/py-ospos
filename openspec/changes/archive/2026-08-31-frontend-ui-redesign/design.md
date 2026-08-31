## Context

The frontend is a Vite + React 18 + TypeScript SPA. All styling is a single plain-CSS file (`src/index.css`, 218 lines) with hardcoded hex colors, no design tokens, no component library, and a horizontal-tab layout. See `proposal.md` - Why for the motivation. The stack constraints are: only React + React Router as runtime deps; the project is committed to a minimal dependency footprint; UI language is pt-BR; behavior (auth, offline outbox, sales, cash shift) must not change.

## Goals / Non-Goals

**Goals:**
- Introduce a tokenized, theme-able design system (CSS variables bound to Tailwind) with light + dark support.
- Rebuild the app shell (sidebar + topbar) and migrate Login, PDV (Pos), and Caixa (Shift) to accessible shadcn/ui primitives.
- Keep the change reviewable and behavior-preserving.

**Non-Goals:**
- Migrating Customers, Products, Reports pages (follow-up PR).
- Backend/API changes.
- Re-architecturing the auth/outbox state management (only its presentation changes).
- Introducing runtime UI state libraries (React Context/AuthProvider stays as-is).

## Decisions

### 1. Use Tailwind CSS + shadcn/ui (Radix) rather than a CSS framework like Bootstrap or a component library like MUI/Ant
shadcn/ui is built on Radix primitives (accessible, unstyled) + Tailwind utility recipes that are copied into the repo (no runtime dep, full ownership of styles). This matches the project's preference for minimal, auditable dependencies: Tailwind/PostCSS/Radix are dev/build deps; component source lives in the repo and can be trimmed. Alternatives considered: MUI/Ant add a large runtime + theme system we can't easily reskin; a pure-CSS rewrite (option A) gives less accessibility and less consistency for a POS that operators use all day.

### 2. Tokenize palette via CSS variables, keeping the brand blue as primary
Define `:root` (light) and `.dark` blocks of CSS variables (background, foreground, card, primary, destructive, border, ring, etc.), mapped into `tailwind.config.cjs` via `hsl(var(--...))`. Primary stays `#2f81f7`-family (converted to HSL). This gives one source of truth and makes future themes (e.g., green) a token swap.

### 3. Dark mode via `.dark` class + `localStorage`, toggled from the topbar
Tailwind darkMode strategy `class`. A `ThemeProvider` (small, in `App.tsx`) applies/removes `.dark` on `<html>` and persists preference. Chosen over `media` strategy so the toggle is explicit and matches the requirement "user can toggle"; defaults to system preference on first load via `prefers-color-scheme`, falling back to `light`.

### 4. AppShell: sidebar (desktop) + collapsible drawer (mobile) + topbar
Replace `nav.tabs` with a left sidebar listing PDV / Clientes / Produtos / Caixa / Relatórios (manager-only), and a topbar with brand wordmark, offline-sync badge, and user/role/sair. On narrow screens the sidebar collapses into a drawer toggled by a hamburger. The offline `outbox` pending-count badge and `syncNow` flow from `App.tsx` are preserved unchanged.

### 5. Component scope: generate only the shadcn primitives actually used
Install via `npx shadcn@latest add` only: button, card, input, label, table, badge, separator, alert, and select (PDV payment method), dialog (if Caixa confirm needed). Avoid pulling unused components to keep the bundle lean.

### 6. `cn()` utility and component location
`src/lib/utils.ts` (clsx + tailwind-merge) and generated components under `src/components/ui/`. Add `tailwindcss-animate` for Radix enter/exit animations used by dropdown/dialog.

### 7. Keep `money(cents)` formatting consistent
The duplicated `money()` helper across pages is out of scope for refactor here; Pos.tsx and Shift.tsx will keep their existing local format calls so behavior is pixel-identical in formatting. (Noted as a candidate future consolidation, not this PR.)

## Risks / Trade-offs

- [Bundle size grows] → Tailwind tree-shakes unused utilities; Radix primitives are small; limiting to used components keeps gzip impact to tens of kB. Docker build path unchanged.
- [Visual diff for untested pages (Customers/Products/Reports)] → Out of scope this PR; they keep the plain-CSS classes that are still defined in `index.css`. Mitigated by keeping a minimal residual stylesheet for non-migrated outside-shell pages and by covering `App.test.tsx`.
- [Tailwind + PostCSS config wiring pitfalls] → Verified against current Vite 5 setup; PostCSS 8 config via `postcss.config.cjs`; the existing `index.html`/`main.tsx` entry is unchanged.
- [Selectors in `App.test.tsx` break if markup changes] → Review/update the test to stable, behavior-level queries (role-based), preserving its assertions on what actually matters.
- [Dark-mode contrast errors in the POS (color-critical)] → Use shadcn theme tokens consistently; spot-check contrast on the PDV catalog grid and cart panel.

## Migration Plan

1. Install dev/build tooling (tailwindcss, postcss, autoprefixer, tailwindcss-animate, cva, clsx, tailwind-merge) and init shadcn (components.json).
2. Replace `src/index.css` with Tailwind directives + token definitions (`:root`, `.dark`).
3. Create `src/lib/utils.ts` and generate needed `src/components/ui/*` primitives.
4. Rebuild `App.tsx` shell (sidebar + topbar + theme provider + drawer).
5. Migrate Login → Pos → Shift to shadcn primitives.
6. Update `App.test.tsx` for any changed queries; run `npm run typecheck`, `npm test`, `npm run build`.

Deployment is the existing static-Nginx frontend; rollback is reverting the merge commit (HTML/CSS/JS only, no DB/API migration).

## Open Questions

None - resolved via the brainstorming session (palette stays brand blue; dark mode implemented this PR; core pages only).
