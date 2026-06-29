# RELEASE_NOTES.md — `patch-developer-submissions-nav`

> Stage `P-build` change summary + rehearsed rollback. Source: [`UX-003`](../../issues/UX-003.md).
> Maintenance Engineer, 2026-06-28. Released local/dev (no prod target yet — D-11 staging pending).

## What changed

Resolves [`UX-003`](../../issues/UX-003.md) (High): `developer`-role users had **no UI path**
back to their pending / withdrawn / rejected submissions once they navigated away from a
freshly-submitted app. The surfaces existed (`catalog:my-apps`, `dashboard:my-apps`) but
nothing linked to them. This patch adds the missing links — **presentation-layer only**.

1. **New `is_developer` template tag** ([`apps/accounts/templatetags/account_roles.py`](../../apps/accounts/templatetags/account_roles.py)) —
   `{% is_developer user as flag %}` is the template-side read of the role gate. It
   *delegates* to the existing fail-closed [`account_has_role`](../../apps/accounts/permissions.py#L23)
   (one source of truth; no new auth logic). Indexed in [CODEMAP.md](../../CODEMAP.md).
2. **Developer-gated "My submissions" header link** ([`apps/core/templates/core/base.html`](../../apps/core/templates/core/base.html)) —
   shown only to developers (mirrors the view's `@require_role(developer)` gate), linking to
   `catalog:my-apps`, which lists **every** status with its manage/withdraw/resubmit actions.
3. **Dashboard reachability** ([`apps/dashboard/templates/dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html)) —
   a no-JS sub-nav (Analytics ⇄ Submissions) and a secondary **"View my submissions"** CTA in
   the empty state, so a developer with only non-accepted apps is guided to where they live
   instead of dead-ending at "Submit".
4. **Reciprocal "View analytics" link** ([`apps/catalog/templates/catalog/my_apps.html`](../../apps/catalog/templates/catalog/my_apps.html)) —
   the submissions list now links back to the dashboard, so both developer surfaces are
   mutually reachable from the single header entry point.

Styling reuses existing design-system classes (`btn`, `btn--ghost`/`btn--secondary`,
`site-nav-links`, `cluster`) — **no new CSS, no new tokens**.

## Who is affected

- **Developers:** gain a persistent header link to their submissions and two-way navigation
  between the submissions list and the analytics dashboard. The dashboard empty state no
  longer dead-ends.
- **Plain users & anonymous visitors:** **no change** — the developer link is gated, and
  regression tests assert it never renders for them. The rest of the header is byte-unchanged.

## Scope / safety

- **No schema, no migration, no new API endpoint, no global ADR** — `makemigrations --check`
  reports no drift. The [PATCH.md](PATCH.md) §2 No-Schema Assertion holds; stayed on the Patch Track.
- One added `groups.filter(...).exists()` query per authenticated page render (the gated
  header link) — bounded, identical to the cost every gated view already pays.

## Verification

- **988 tests green** (980 baseline + 8 new), 0 skipped · `ruff` clean · `manage.py check`
  clean · `makemigrations --check` = no drift. Mapping in [TEST_PLAN.md](TEST_PLAN.md).

## Rehearsed rollback (DU-REL-1)

The patch is purely additive presentation-layer code + tests with **no migration**, so
rollback is a plain code revert with nothing irreversible to undo.

- **Procedure:** `git revert <build-commit>` (or remove the working-tree changes). The new
  template tag package, the 3 template edits, the CODEMAP line, and the 4 test additions all
  revert together; deleting the `apps/accounts/templatetags/` package removes the
  `account_roles` library cleanly (no other surface depends on it).
- **Rehearsed 2026-06-28:** the full patch was stashed to simulate the revert; on the
  restored pre-patch tree `manage.py check` was clean, `makemigrations --check` reported no
  drift, and the 391 tests across the four touched apps passed. The working tree was then
  restored intact. Codebase returns to a clean, compile-safe, passing state — DU-REL-1 holds.
