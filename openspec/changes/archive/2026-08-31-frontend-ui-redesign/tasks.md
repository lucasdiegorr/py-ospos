## 1. Tooling setup

- [ ] 1.1 Install Tailwind CSS, PostCSS, Autoprefixer, tailwindcss-animate, class-variance-authority, clsx, tailwind-merge as devDependencies in `frontend/package.json` and verify `npm install` succeeds with no peer warnings that block the build
- [ ] 1.2 Add `frontend/postcss.config.cjs`, `frontend/tailwind.config.cjs` (with `darkMode: 'class'`, theme tokens mapped to CSS variables, content globs covering `index.html` and `src/**/*.{ts,tsx}`) and verify `npx tailwindcss --help` resolves and `npx postcss --help` resolves
- [ ] 1.3 Initialize shadcn (`components.json` with `tsx` style, base color `slate`) and generate the components actually used: button, card, input, label, badge, separator, alert, table, select; verify each file exists under `frontend/src/components/ui/`
- [ ] 1.4 Create `frontend/src/lib/utils.ts` exporting `cn()` (clsx + tailwind-merge) and verify it compiles with `npm run typecheck`

## 2. Design tokens and global stylesheet

- [ ] 2.1 Replace `frontend/src/index.css` with Tailwind `@tailwind base/components/utilities` directives plus `:root` and `.dark` CSS-variable definitions for `--background`, `--foreground`, `--card`, `--card-foreground`, `--primary`, `--primary-foreground`, `--secondary`, `--accent`, `--destructive`, `--border`, `--input`, `--ring`, and brand-blue primary in HSL; verify the file renders without errors when running `npm run dev` against the existing Login/Pos/Shift pages (they will still use plain classes temporarily)

## 3. AppShell rebuild

- [ ] 3.1 Add a small `ThemeProvider` and `ThemeToggle` in `frontend/src/` that reads/writes `localStorage('py-ospos-theme')`, applies `.dark` on `<html>`, and renders a topbar button; verify by toggling in devtools that `<html>` gets/loses `.dark` and `localStorage` updates
- [ ] 3.2 Replace `frontend/src/App.tsx` with the new AppShell: left sidebar listing PDV / Clientes / Produtos / Caixa / Relatórios (Relatórios manager-only), topbar with brand wordmark, ThemeToggle, offline-sync badge (preserving existing `flushOutbox` and `pendingCount` logic), and user/role/sair; on mobile the sidebar collapses into a drawer; verify `npm run dev` shows the new shell, manager-only Relatórios link is hidden for attendants, and offline-sync still triggers on `online` event

## 4. Migrate Login

- [ ] 4.1 Rewrite `frontend/src/pages/Login.tsx` using shadcn Card/Input/Label/Button/Alert; preserve username/password submission via the existing `useAuth()` API, the error message displayed on failure, and the post-login redirect; verify by logging in with a valid user and by submitting invalid credentials to see the Alert render

## 5. Migrate Pos (PDV)

- [ ] 5.1 Rewrite `frontend/src/pages/Pos.tsx`: catalog rendered as a responsive grid of Card components (each with name, prices, unit/pack toggle when applicable, add-to-cart Button); search Input above the grid; right-hand Cart Card with line-item rows (qty controls, line total, remove), Total display, payments Card listing each payment (method + amount) with controls to add/remove a payment, finalize-sale Button (disabled when sum < total), Receipt Card (monospaced pre) shown after completion; preserve all existing logic (fiado with customer search, split payments, offline queueing) and `Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })` formatting
- [ ] 5.2 Verify the Pos page renders for a logged-in attendant: catalog loads from API, adding items updates cart total, fiado flow still requires a registered customer, payment split still works, completed sale shows receipt Card, and an offline completion still queues via `outbox.ts`

## 6. Migrate Shift (Caixa)

- [ ] 6.1 Rewrite `frontend/src/pages/Shift.tsx`: OpenShift Card (float Input + submit), active-shift summary Card (opening float, totals, expected cash), Movements Table (type/amount/reason/timestamp), Supply Card (amount + reason + submit), Bleed Card (amount + reason + submit), CloseShift Card (counted-money Input + difference display in green/red via destructive/primary tokens); preserve the existing shift API calls and the existing Brazilian currency formatting
- [ ] 6.2 Verify the Shift page end-to-end: open a shift, register a sale elsewhere, supply/bleed, then close with counted money; expected cash matches the formula in the spec; negative difference shows in destructive styling, zero/positive in primary/foreground

## 7. Verification

- [ ] 7.1 Run `cd frontend && npm run typecheck` and verify exit code 0
- [ ] 7.2 Run `cd frontend && npm test` and verify all existing tests pass; update `App.test.tsx` selectors if markup changed so behavior assertions still hold
- [ ] 7.3 Run `cd frontend && npm run build` and verify the production bundle builds without errors; verify the generated `dist/index.html` references hashed JS/CSS assets
- [ ] 7.4 Manually smoke-test in `npm run dev` against the docker-compose stack: login → PDV (add items + complete sale) → Caixa (open shift) → Relatórios (manager only); toggle light/dark theme and verify the migrated pages re-render with theme tokens

## 8. PR

- [ ] 8.1 Commit changes with Conventional Commits (`feat(ui): ...`, `chore(ui): ...`); do NOT add any agent co-author
- [ ] 8.2 Push branch and open PR to `master` via `gh pr create --base master --head feat/ui-redesign`; do NOT enable auto-merge; report the PR URL and stop for human review
