# PATCH.md — patch-my-apps-status-display

## Source Issues

- [`UX-004`](../../issues/UX-004.md) — "My Submissions" heading is misleading post-approval; no status grouping
- [`UX-006`](../../issues/UX-006.md) — No direct link to the public app page once an app is accepted

---

## 1. Problem Statement

### Reproduction Steps

1. Log in as a developer who has at least one accepted app.
2. Navigate to **My Submissions** (`/submit/apps/` → `catalog:my-apps`).
3. Observe: the page heading reads **"My submissions"** even though the app is live and
   publicly listed — semantically incorrect.
4. Observe: all apps (regardless of status) appear in a flat insertion-order list with no
   grouping. It is not immediately clear which apps are live, which are pending, and which
   need changes.
5. Observe: there is no link from the approved app card to the public app page (`pages:app-page`)
   — the only CTA is "Manage Submission", which leads to the developer management page.

### Root Cause Analysis

All three gaps are **presentation-layer only** — no model, selector, or API is involved:

1. **Heading (`UX-004`)** — [`catalog/my_apps.html:8`](../../apps/catalog/templates/catalog/my_apps.html#L8)
   hardcodes the string `My submissions` as the H1. It never changes regardless of app lifecycle state.

2. **Flat ordering, no grouping (`UX-004`)** — [`selectors.list_owned_apps`](../../apps/catalog/selectors.py#L85)
   returns apps ordered by PK (insertion order). [`my_apps_page`](../../apps/catalog/views.py#L307)
   does not sort before decorating; the template has no grouping structure — apps are
   rendered in a single flat `{% for app in apps %}` loop with no section headers.
   
   *Note: Status badges already exist in the template (lines 38–46) — that part of UX-004
   is already satisfied. Only the heading, ordering, and grouping are missing.*

3. **No live-page link (`UX-006`)** — The template renders one CTA per card:
   `"Manage Submission"` → `catalog:app-detail`. There is no conditional branch that adds
   a `pages:app-page` link for apps with `status == 'accepted'`.

---

## 2. Proposed Fix / Change

### Code-Level Design

**T-02 — Rename heading + subtitle (`catalog/my_apps.html`)**

- `L8`: `My submissions` → `My Apps`
- Subtitle line: `"Submit apps to the catalog and track their review status."` →
  `"Submit and manage your apps and track their review status."`

**T-03 — Sort decorated apps by status priority (`apps/catalog/views.py`)**

Add a module-level sort-order constant immediately after `_decorate_apps`:

```python
_MY_APPS_STATUS_ORDER = {'accepted': 0, 'pending': 1, 'rejected': 2, 'withdrawn': 3}
```

In `my_apps_page`, sort the decorated list before rendering:

```python
decorated = sorted(_decorate_apps(apps), key=lambda a: _MY_APPS_STATUS_ORDER.get(a['status'], 99))
return render(request, "catalog/my_apps.html", {"apps": decorated})
```

Sorting is purely a presentation concern, local to the server-rendered template path. The
API endpoint `MyAppsView` (which calls `selectors.list_owned_apps` independently) is not
touched — its ordering is unchanged.

**T-04 — Status group section headers (`catalog/my_apps.html`)**

Replace the bare `{% for app in apps %}` loop (inside the non-empty branch) with Django's
`{% regroup %}` tag (already available in the standard template library):

```html
{% regroup apps by status as status_groups %}
{% for group in status_groups %}
  <div class="stack" style="--gap: var(--space-2);">
    <h2 class="..." style="...">
      {% if group.grouper == 'accepted' %}Active
      {% elif group.grouper == 'pending' %}Awaiting Review
      {% elif group.grouper == 'rejected' %}Needs Changes
      {% else %}Withdrawn{% endif %}
    </h2>
    <div class="stack" style="--gap: var(--space-4);">
      {% for app in group.list %}
        ...existing card HTML...
      {% endfor %}
    </div>
  </div>
{% endfor %}
```

Because the list is sorted by priority (T-03), `{% regroup %}` produces groups in the
correct order: Active → Awaiting Review → Needs Changes → Withdrawn. Only groups that
actually contain apps are emitted.

**T-05 — "View live page" link for accepted apps (`catalog/my_apps.html`)**

Inside each card's CTA section (the existing `{% else %}` branch of the rejection block,
currently containing only the "Manage Submission" link), add a conditional live-page link
when `app.status == 'accepted'`:

```html
{% if app.status == 'accepted' %}
  <a href="{% url 'pages:app-page' app_id=app.id %}"
     class="btn btn--primary btn--sm"
     target="_blank" rel="noopener noreferrer"
     style="text-decoration: none;">View live page</a>
{% endif %}
```

The "Manage Submission" link remains for all statuses; the live-page link appears only
when the public page is actually accessible (`accepted`).

### No-Schema Assertion

*This patch contains no schema changes, no new public API endpoints, and no global ADR
updates.* Changes: one view function (sort only), one template (heading + grouping + link).
The selector `list_owned_apps` and all API views are untouched.

---

## 3. Task List

**T-01** (S) — **Red-first regression tests** in
[`apps/catalog/tests/test_pages_developer.py`](../../apps/catalog/tests/test_pages_developer.py)

Write four new test methods in the existing `DeveloperPagesTests` class (or a new class
if needed):

1. `test_my_apps_heading_says_my_apps` — GET `catalog:my-apps`, assert response contains
   `"My Apps"` and does NOT contain `"My submissions"`.
2. `test_my_apps_status_grouping_shows_group_headers` — seed one accepted + one pending
   app; GET `catalog:my-apps`; assert both group labels `"Active"` and
   `"Awaiting Review"` appear in the response.
3. `test_my_apps_accepted_app_has_live_page_link` — seed one accepted app; GET
   `catalog:my-apps`; assert the `pages:app-page` URL for that app appears in the response.
4. `test_my_apps_pending_app_has_no_live_page_link` — seed one pending app; GET
   `catalog:my-apps`; assert the `pages:app-page` URL does NOT appear.

DoD: all four tests fail on the unpatched code before any template/view change.  
Files touched: `apps/catalog/tests/test_pages_developer.py`

---

**T-02** (S) — **Rename heading + subtitle** in the template

- `catalog/my_apps.html:8`: `My submissions` → `My Apps`
- `catalog/my_apps.html:9` (subtitle): update to `"Submit and manage your apps and track their review status."`

DoD: `test_my_apps_heading_says_my_apps` passes; `assertContains(response, "My Apps")`
passes; `assertNotContains(response, "My submissions")` passes.  
Files touched: `apps/catalog/templates/catalog/my_apps.html`

---

**T-03** (S) — **Sort by status priority** in `my_apps_page` view

- Add `_MY_APPS_STATUS_ORDER = {'accepted': 0, 'pending': 1, 'rejected': 2, 'withdrawn': 3}`
  as a module-level constant in `apps/catalog/views.py` (place after `_decorate_apps`).
- Update `my_apps_page` to sort the decorated list by this key before rendering.

DoD: group ordering in the rendered page matches: Active → Awaiting Review → Needs Changes
→ Withdrawn.  
Files touched: `apps/catalog/views.py`

---

**T-04** (S) — **Status group headers** in the template

- Replace the `{% for app in apps %}` loop in `my_apps.html` with a `{% regroup %}`-based
  structure as designed in §2 above.
- Output a section `<h2>` label per status group.

DoD: `test_my_apps_status_grouping_shows_group_headers` passes; group headers render only
for statuses that have at least one app.  
Files touched: `apps/catalog/templates/catalog/my_apps.html`

---

**T-05** (S) — **"View live page" link for accepted apps**

- Add the conditional `pages:app-page` anchor inside the card's CTA section, shown only
  when `app.status == 'accepted'`.
- `target="_blank" rel="noopener noreferrer"` (opens in new tab without referrer leak).

DoD: `test_my_apps_accepted_app_has_live_page_link` passes;
`test_my_apps_pending_app_has_no_live_page_link` passes.  
Files touched: `apps/catalog/templates/catalog/my_apps.html`

---

**T-06** (S) — **Verify + write TEST_PLAN.md + RELEASE_NOTES.md**

- Run the full test suite; confirm ≥ 1 004 tests green (current 1 000 + 4 new).
- Run `ruff check` — no new errors.
- Run `manage.py check` — clean.
- Run `manage.py makemigrations --check` — no drift (No-Schema Assertion).
- Rehearse rollback (DU-REL-1): `git stash` → check + no-drift + catalog tests green on
  reverted tree → `git stash pop` intact.
- Write `TEST_PLAN.md` and `RELEASE_NOTES.md`.
- Close UX-004 + UX-006 as `RESOLVED` in `issues/README.md`, `issues/UX-004.md`,
  `issues/UX-006.md`, and `features/INDEX.md`.
- Update `CONTROL.md` (closed-out → `0-coordinator`).

DoD: all checks pass; all four new tests green; TEST_PLAN.md + RELEASE_NOTES.md written.  
Files touched: `features/patch-my-apps-status-display/TEST_PLAN.md`,
`features/patch-my-apps-status-display/RELEASE_NOTES.md`, `features/INDEX.md`,
`issues/README.md`, `issues/UX-004.md`, `issues/UX-006.md`, `CONTROL.md`
