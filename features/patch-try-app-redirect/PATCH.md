# PATCH.md — patch-try-app-redirect

**Source issue:** [`BUG-004`](../../issues/BUG-004.md) — "Try App" button links to the platform URL instead of the app's own external URL. Severity: **High**.

---

## 1. Problem Statement

### Reproduction Steps

1. Submit and approve an app with an external URL (e.g. `https://my-vibe-app.com`).
2. Navigate to the app's detail page (e.g. `/apps/<id>/`).
3. Click the **"Try \<AppName\>"** button.
4. Observe: the browser either stays on the current page or navigates to the platform root — it does **not** navigate to the external app URL.

### Root Cause Analysis (confirmed — Maintenance Planner, 2026-06-29)

**`hx-boost="true"` is set on `<main id="main">` in [`core/base.html:50`](../../apps/core/templates/core/base.html#L50).** This instructs HTMX to intercept every anchor click and form submit inside `<main>` and replace them with AJAX requests.

The "Try App" anchor in [`app_page.html:72`](../../apps/pages/templates/pages/app_page.html#L72) is:

```html
<a href="{% url 'pages:try' app_id=app.id %}{% if imp %}?imp={{ imp }}{% endif %}"
   class="btn btn--primary btn--lg" style="display: flex;">
  Try {{ app.name }}
</a>
```

When the user clicks it:

1. HTMX intercepts the click and makes an AJAX `GET /apps/<id>/try`.
2. The `try_redirect` view ([`pages/views.py:55–66`](../../apps/pages/views.py#L55)) correctly records the click-through signal and then returns `redirect(app.url)` — a **302** to the developer's external URL (e.g. `https://my-vibe-app.com`).
3. The browser's `fetch` API (used by HTMX under the hood) automatically follows the 302. The `Location` header points to a **cross-origin** URL.
4. The cross-origin server has no `Access-Control-Allow-Origin` headers for the platform origin → the fetch fails with a CORS / opaque-response error.
5. HTMX cannot read the response body → it either swaps nothing or reverts to the current URL.
6. **The user never leaves the platform page.** The conversion is lost.

The `try_redirect` view itself is **correct**; it correctly stores and redirects to `app.url`. The defect is entirely in the template: the anchor is inside the HTMX-boosted `<main>` with no opt-out.

---

## 2. Proposed Fix

### Code-level Design

Two attributes are added to the "Try App" anchor in [`app_page.html:72`](../../apps/pages/templates/pages/app_page.html#L72):

| Attribute | Purpose |
|-----------|---------|
| `hx-boost="false"` | Tells HTMX to exclude this element from boost-interception; the browser handles the click normally. The 302 from `try_redirect` is then followed natively and the user lands on the external app. |
| `target="_blank" rel="noopener noreferrer"` | Opens the external app in a new tab. Correct UX (users should not lose their place on the platform) and a security best practice for links to third-party origins. |

Result after the fix:

```html
<a href="{% url 'pages:try' app_id=app.id %}{% if imp %}?imp={{ imp }}{% endif %}"
   class="btn btn--primary btn--lg" style="display: flex;"
   hx-boost="false" target="_blank" rel="noopener noreferrer">
  Try {{ app.name }}
</a>
```

The click-through signal is still recorded in `try_redirect` — nothing changes in the view layer. The widget firewall (M5=0), no-JS path (the anchor is a real `<a>` with an `href`), and SEO are unaffected. The change is purely presentational.

### No-Schema Assertion

This patch contains **no schema changes, no new public API endpoints, and no global ADR updates.** Template-only change. Patch Track scope confirmed.

---

## 3. Task List

### T-01 — Red-first regression test (S) — **write before touching the template**

**Goal:** A test that fails on the unpatched template (confirming the attributes are absent) and passes after the fix.

**Test:** Add `test_try_app_anchor_bypasses_htmx_boost` to [`apps/pages/tests/test_template.py`](../../apps/pages/tests/test_template.py) (inside the existing `FullyPopulatedTests` class, which already uses `_render` + `_app` helpers):

```python
def test_try_app_anchor_bypasses_htmx_boost(self):
    """BUG-004: the Try App anchor must not be HTMX-boosted (hx-boost="false") and
    must open in a new tab (target="_blank") so the browser follows the redirect
    natively to the external app URL instead of via AJAX."""
    html = _render(_app())
    self.assertIn('hx-boost="false"', html)
    self.assertIn('target="_blank"', html)
    self.assertIn('rel="noopener noreferrer"', html)
```

**DoD:** Test file updated; `python manage.py test apps.pages.tests.test_template.FullyPopulatedTests.test_try_app_anchor_bypasses_htmx_boost` **fails** (attributes absent on the unpatched template).

**Files touched:** `apps/pages/tests/test_template.py`

---

### T-02 — Fix the "Try App" anchor (S)

**Goal:** Add `hx-boost="false"`, `target="_blank"`, and `rel="noopener noreferrer"` to the anchor.

**Change:** In [`apps/pages/templates/pages/app_page.html:72`](../../apps/pages/templates/pages/app_page.html#L72), replace:

```html
<a href="{% url 'pages:try' app_id=app.id %}{% if imp %}?imp={{ imp }}{% endif %}" class="btn btn--primary btn--lg" style="display: flex;">
```

with:

```html
<a href="{% url 'pages:try' app_id=app.id %}{% if imp %}?imp={{ imp }}{% endif %}" class="btn btn--primary btn--lg" style="display: flex;" hx-boost="false" target="_blank" rel="noopener noreferrer">
```

**DoD:** T-01 test now **passes**; the anchor line in the template contains all three new attributes.

**Files touched:** `apps/pages/templates/pages/app_page.html`

---

### T-03 — Verify and close out (S)

Run all checks:

1. `python manage.py test` — full suite ≥ 999 tests green (+1).
2. `ruff check .` — clean.
3. `python manage.py check` — clean.
4. `python manage.py makemigrations --check` — no drift (No-Schema Assertion).
5. **Rollback rehearsal (DU-REL-1):** `git stash` the two changed files → re-run `python manage.py check` + the pages template tests → confirm clean on the reverted tree → `git stash pop` → restore intact.

Write `TEST_PLAN.md` + `RELEASE_NOTES.md`. Close BUG-004 in [`issues/README.md`](../../issues/README.md), [`INDEX.md`](../INDEX.md), and [`BUG-004.md`](../../issues/BUG-004.md).

**DoD:** All checks green; rollback confirmed; artifacts written; BUG-004 marked RESOLVED.

**Files touched:** `features/patch-try-app-redirect/TEST_PLAN.md`, `features/patch-try-app-redirect/RELEASE_NOTES.md`, `issues/README.md`, `features/INDEX.md`, `issues/BUG-004.md`, `CONTROL.md`.
