# PATCH.md — `patch-developer-submissions-nav`

> Patch Track artifact (Stages `P-plan` → `P-build`). Source issue:
> [`UX-003`](../../issues/UX-003.md) (High) — *No navigation path to view and manage
> pending/withdrawn app submissions.*
>
> Maintenance Planner (Stage `P-plan`), 2026-06-28. Scope: **template + one read-only
> template tag only.** No schema, no API, no ADR (see §2 No-Schema Assertion).

---

## 1. Problem Statement

A `developer`-role user who submits an app is redirected to its detail page
(`catalog:app-detail`). Once they navigate away, the UI offers **no way back** to that
submission or to any of their pending / withdrawn / rejected apps. The surfaces that do
expose them — the submissions list [`catalog:my-apps`](../../apps/catalog/urls.py#L49)
(`/apps`, all statuses) and the developer dashboard
[`dashboard:my-apps`](../../apps/dashboard/urls.py) (`/dashboard/`, accepted only) — are
reachable only by typing the URL.

### Reproduction Steps

1. Sign in as a user holding the `developer` role.
2. Submit an app (`/apps/submit`) → you are redirected to `/apps/{id}` showing `pending`.
3. Click any header link (Discover / Following / Profile) to navigate away.
4. **Observed:** the global header
   ([`core/base.html`](../../apps/core/templates/core/base.html#L17-L33)) shows only
   *Discover · Following · Profile · Sign out*. There is **no** link to `/apps`
   (`catalog:my-apps`) or `/dashboard/` (`dashboard:my-apps`). The pending submission is
   now unreachable through the UI.
5. Navigate directly to `/dashboard/` with **no accepted apps**.
   **Observed:** the empty state
   ([`dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html#L60-L67))
   reads *"No accepted apps yet"* and offers only *"Submit your first app"* — a dead end
   that never points to the developer's actual pending/rejected submissions at `/apps`.

### Root Cause Analysis

Two independent gaps, both presentation-layer:

1. **No developer entry point in the header.** The authenticated branch of
   [`core/base.html:19-32`](../../apps/core/templates/core/base.html#L19-L33) renders a
   fixed link set (Following / Profile / Sign out) identical for every authenticated
   account. A developer-only link to `catalog:my-apps` was never added. There is also no
   template-facing way to *detect* the developer role to gate such a link: roles are
   Django `Group` rows, and the single authorization gate
   [`account_has_role`](../../apps/accounts/permissions.py#L23) is only wired into views
   ([`HasRole`](../../apps/accounts/permissions.py#L51) /
   [`require_role`](../../apps/accounts/permissions.py#L64)) — there is **no** template
   tag or context processor exposing it. So even a correctly-gated link cannot be written
   today without a small, reusable helper.

2. **The dashboard empty state is a dead end.** The dashboard view
   [`dashboard.views.my_apps`](../../apps/dashboard/views.py#L33) builds reception
   summaries for **accepted** apps only; a developer with solely pending/rejected/
   withdrawn apps falls into the `{% else %}` empty state
   ([`dashboard/my_apps.html:60-67`](../../apps/dashboard/templates/dashboard/my_apps.html#L60-L67)),
   whose only call to action is *Submit*. It never links to `catalog:my-apps`, where
   those non-accepted submissions actually live. The two developer surfaces are also not
   cross-linked, so reaching one never reveals the other.

> **Why this is the whole root cause (not guesswork):** the target surfaces exist and
> work — `catalog:my-apps` ([`my_apps_page`](../../apps/catalog/views.py#L305), template
> [`catalog/my_apps.html`](../../apps/catalog/templates/catalog/my_apps.html) renders
> every status with manage/withdraw/resubmit affordances) and `dashboard:my-apps`. The
> defect is purely **reachability**: nothing renders a link to them. No view, route, model,
> or service is wrong; only templates (and the missing template-side role check).

---

## 2. Proposed Fix / Change

Add a developer-gated header link to the submissions list, give the dashboard empty state
a path to submissions, and cross-link the two developer surfaces — all presentation-layer.

### Code-level Design

**(A) Reusable developer-role template tag — single source of truth preserved.**
Add `apps/accounts/templatetags/account_roles.py` (with an `__init__.py` so the directory
is a package, matching `apps/ratings/templatetags/` et al.) exposing one `simple_tag`:

```python
# apps/accounts/templatetags/account_roles.py
from django import template
from apps.accounts import roles
from apps.accounts.permissions import account_has_role

register = template.Library()

@register.simple_tag
def is_developer(user) -> bool:
    """True if `user` holds the developer role — the template-side read of the one gate."""
    return account_has_role(user, roles.DEVELOPER)
```

- **Reuse, no duplication:** it delegates to the existing fail-closed gate
  [`account_has_role`](../../apps/accounts/permissions.py#L23) and the
  [`roles.DEVELOPER`](../../apps/accounts/roles.py#L11) constant — the role decision stays
  in one place (CLAUDE.md §5.4 "one source of truth per fact"). The gate already swallows
  lookup errors and returns `False`, so the tag is fail-soft by construction.
- **Cost:** one `groups.filter(...).exists()` query per authenticated page render (the
  link lives in the shared header). This is bounded and identical to the per-request cost
  every gated view already pays; acceptable and documented here.
- Register it in [CODEMAP.md](../../CODEMAP.md) next to the other inclusion/role tags.

**(B) Header link — [`core/base.html`](../../apps/core/templates/core/base.html).**
`{% load account_roles %}` at the top, and inside the `{% if user.is_authenticated %}`
branch (alongside *Following* / *Profile*) add a developer-gated item:

```django
{% is_developer user as user_is_developer %}
...
{% if user_is_developer %}
  <li><a href="{% url 'catalog:my-apps' %}">My submissions</a></li>
{% endif %}
```

Gating the link to developers mirrors the view's own `@require_role(DEVELOPER)` gate, so
the link is never shown to an account that would receive a 403 on click. This single link
resolves the High-priority dead end — `catalog:my-apps` lists **every** status with its
manage/withdraw/resubmit actions. (Issue suggestion 1.)

**(C) Dashboard reachability — [`dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html).**
- Add a small sub-nav at the top of the page (a "Submissions" link to `catalog:my-apps`
  beside the current "Analytics" view) so a developer on the dashboard can reach their
  full submission list. (Issue suggestion 2 — a lightweight tabbed/sub-nav, no JS.)
- In the empty-state block (lines 60-67), add a secondary link **"View my submissions"** →
  `catalog:my-apps` next to the existing "Submit your first app" button, so a developer
  with only pending/rejected apps is guided to where those live instead of a dead end.
  (Issue suggestion 3.)

**(D) Reciprocal link — [`catalog/my_apps.html`](../../apps/catalog/templates/catalog/my_apps.html).**
Add a "View analytics" link to `dashboard:my-apps` in the page header cluster (beside
"Submit an App"), so the dashboard is reachable from the submissions list. Combined with
(B), a single header entry point now makes **both** developer surfaces mutually reachable.

> Styling reuses existing classes already in the shared design system
> (`btn`, `btn--ghost`/`btn--secondary`, `site-nav-links`, `cluster`) — no new CSS rules,
> no new tokens. Anonymous and non-developer users see the header exactly as today.

### No-Schema Assertion

**This patch contains no schema changes, no new public API endpoints, and no global ADR
updates.** It adds one read-only template tag that reuses the existing role gate and edits
three templates. No migration, no URL/route, no model, no service, no `DECISIONS.md` ADR.
Scope gate (CLAUDE.md §2) confirmed — stays on the Patch Track.

---

## 3. Task List

Ordered, independently verifiable, all sized **S**. `T-01` writes the failing regression
test first, before any fix code.

### T-01 (S) — Regression tests reproducing the gap *(must be written first; red before T-02–T-05)*
- **Traces:** §1 Reproduction (the whole defect).
- **What:** Add tests that assert the navigation paths are present for developers and
  absent for everyone else. Use the Django test client + `force_login` and the existing
  `make_account(..., role=roles.DEVELOPER)` helper (pattern:
  [`dashboard/tests/test_views.py:25-27`](../../apps/dashboard/tests/test_views.py#L25-L27)).
  Cover:
  1. **Header link present for developers** — render any authenticated page (e.g.
     `discovery:browse` or `dashboard:my-apps`) as a developer; assert the response HTML
     contains a link to `reverse("catalog:my-apps")`.
  2. **Header link absent for a plain `user`** — same render as a non-developer
     authenticated account; assert the `catalog:my-apps` link is **not** present.
  3. **Header link absent for anonymous** — assert it is not present when logged out.
  4. **Dashboard empty state links to submissions** — log in a developer with **no
     accepted apps**, GET `dashboard:my-apps`, assert the response contains a link to
     `reverse("catalog:my-apps")`.
  5. **`is_developer` tag** — a focused unit test: `True` for a developer account, `False`
     for a plain user and for `AnonymousUser`.
- **DoD:** all five assertions are written and **fail** against current `main` for the
  reachability cases (1, 4) [proving the gap]; the negative cases (2, 3) pass. No fix code
  is added in this task.
- **Files touched:** `apps/accounts/tests/test_role_tags.py` (new — tag unit test);
  `apps/core/tests/test_header_nav.py` (new — header render cases 1-3);
  `apps/dashboard/tests/test_views.py` (add the empty-state link case 4).

### T-02 (S) — `is_developer` template tag (reuses the one role gate)
- **Traces:** §2(A); unblocks the gated link in T-03.
- **What:** Create `apps/accounts/templatetags/__init__.py` (empty) and
  `apps/accounts/templatetags/account_roles.py` with the `is_developer` `simple_tag` from
  §2(A). Register it in [CODEMAP.md](../../CODEMAP.md) alongside the other template tags.
- **DoD:** the T-01 case 5 tag unit test passes; `ruff` clean; the tag imports and
  delegates to `account_has_role` (no reimplementation of the role lookup).
- **Files touched:** `apps/accounts/templatetags/__init__.py` (new),
  `apps/accounts/templatetags/account_roles.py` (new), `CODEMAP.md`.

### T-03 (S) — Developer-gated "My submissions" header link
- **Traces:** §2(B), issue suggestion 1; the keystone fix for the High dead end.
- **What:** `{% load account_roles %}` in
  [`core/base.html`](../../apps/core/templates/core/base.html) and add the
  developer-gated `<li>` link to `catalog:my-apps` inside the authenticated branch, per
  §2(B). Reuse the existing `site-nav-links` markup/classes.
- **DoD:** T-01 header cases 1-3 pass (present for developer, absent for plain user and
  anonymous); anonymous/non-developer header byte-unchanged otherwise; full suite green.
- **Files touched:** `apps/core/templates/core/base.html`.

### T-04 (S) — Dashboard: submissions sub-nav + empty-state CTA
- **Traces:** §2(C), issue suggestions 2 & 3.
- **What:** In
  [`dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html) add
  (a) a no-JS sub-nav linking to `catalog:my-apps` ("Submissions") beside the current
  Analytics view, and (b) a secondary "View my submissions" link to `catalog:my-apps` in
  the empty-state block (lines 60-67). Reuse existing `btn`/`cluster` classes.
- **DoD:** T-01 case 4 passes (empty state links to submissions); the populated-dashboard
  path still renders unchanged; full suite green.
- **Files touched:** `apps/dashboard/templates/dashboard/my_apps.html`.

### T-05 (S) — Reciprocal "View analytics" link on the submissions list
- **Traces:** §2(D); makes the dashboard reachable so both developer surfaces are
  mutually discoverable from the single header entry point.
- **What:** In
  [`catalog/my_apps.html`](../../apps/catalog/templates/catalog/my_apps.html) add a "View
  analytics" link to `dashboard:my-apps` in the header cluster beside "Submit an App".
  Reuse existing `btn--secondary`/`cluster` classes.
- **DoD:** the submissions page renders a link to `reverse("dashboard:my-apps")` (add a
  short assertion to an existing `catalog/tests/test_pages_developer.py` case or a new
  one); full suite green; `ruff`/`manage.py check`/`makemigrations --check` (no drift)
  all clean.
- **Files touched:** `apps/catalog/templates/catalog/my_apps.html`,
  `apps/catalog/tests/test_pages_developer.py`.

---

### Verification summary (for `P-build` exit)
- Full test suite green (no skips) with the new cases included.
- `ruff` clean · `manage.py check` clean · `makemigrations --check` = **no drift**
  (presentation-only — proves the No-Schema Assertion holds).
- Manual: as a developer, header → "My submissions" reaches all statuses; dashboard empty
  state and sub-nav reach submissions; submissions list reaches the dashboard. Anonymous
  and plain-`user` headers are unchanged.
