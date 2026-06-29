# RELEASE_NOTES.md — patch-try-app-redirect

**Date:** 2026-06-29
**Track:** Patch Track
**Severity of fix:** High (BUG-004)
**Schema change:** None
**Test count:** 1 000 (+1)

---

## Summary

Fixes the "Try App" button on app detail pages: it previously stayed on the platform because
HTMX's boost intercepted the click and followed the `302 → external URL` redirect via AJAX,
which fails at the browser's CORS boundary. The user never navigated to the developer's app.

**Two attributes added to the "Try App" anchor in `app_page.html:72`:**

- `hx-boost="false"` — excludes this anchor from HTMX boost interception; the browser
  handles the click natively and follows the `302` to the developer's external URL.
- `target="_blank" rel="noopener noreferrer"` — opens the external URL in a new tab,
  keeping the user's place on the platform and following standard security practice for
  third-party links.

The `try_redirect` view is unchanged; it still records the click-through signal before
redirecting. The widget firewall (M5=0), no-JS path (real `<a href>`), and SEO are
unaffected.

## Files changed

| File | Change |
|------|--------|
| `apps/pages/templates/pages/app_page.html` | Added `hx-boost="false" target="_blank" rel="noopener noreferrer"` to the Try App anchor (line 72). |
| `apps/pages/tests/test_template.py` | Added `test_try_app_anchor_bypasses_htmx_boost` regression test to `FullyPopulatedTests`. |

## Rollback

No migration → nothing irreversible. Rollback = `git revert <build-commit>`.
Rehearsed: stashed patch → pages tests clean on reverted tree → restored intact.
