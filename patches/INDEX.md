# patches/INDEX.md — Patch Registry

**Every patch ever started is listed here, once.** [CONTROL.md](../CONTROL.md) tracks
*where we are now* (the active patch/feature); this file is the answer to *"have we
already patched X, and where is it?"*

Patches run the **Patch Track** (Maintenance Pipeline) for bug fixes, refactors,
dependency bumps, and chores. They are kept here, separate from the
[feature registry](../features/INDEX.md), so feature tracking stays uncongested. See the
Patch Track routing table in [../CLAUDE.md](../CLAUDE.md) §2.2 and the folder convention
in [README.md](README.md).

Maintained by the **Coordinator** (adds a row when a patch folder is created) and the
**Maintenance Engineer** (fills in the outcome on close-out).

## Registry

| Slug | Source issue | Stage | Started | One-line outcome |
|------|--------------|-------|---------|------------------|
| [patch-block-self-interaction](patch-block-self-interaction/) | [`Q-002`](../issues/Q-002.md) (Medium) + [`Q-003`](../issues/Q-003.md) (Low) | `done` | 2026-06-29 | **Closed-out (released local/dev, 2026-06-29)** — `catalog.is_app_owner` selector + `SelfRatingError`/`SelfFollowError` service guards + view mappings + slot UX (notice/hide); 1013 tests / no schema / rollback rehearsed. Q-002 + Q-003 **RESOLVED**. |
| [patch-dashboard-window-label](patch-dashboard-window-label/) | [`BUG-003`](../issues/BUG-003.md) (Medium) | closed-out (released local/dev) | 2026-06-28 | **RESOLVED** (999 tests) — multiline `{{ … }}` tags weren't tokenized (Django `tag_re` lacks `re.DOTALL`). Joined both offenders onto one line: the selected window's `{{ w.label }}` (reported) **and** a sibling `{{ summary.curated_impressions }}` surfaced by a repo-wide sweep (sweep now returns zero). Template + 1 red-first test only; ruff/check clean, no migration drift; rollback rehearsed. Patch Track scope held. |
| [patch-developer-submissions-nav](patch-developer-submissions-nav/) | [`UX-003`](../issues/UX-003.md) (High) | closed-out (released local/dev) | 2026-06-28 | **RESOLVED** — developers now reach their submissions: a developer-gated "My submissions" header link (new `is_developer` tag delegating to the one role gate) + a dashboard Analytics⇄Submissions sub-nav & empty-state "View my submissions" CTA + a reciprocal "View analytics" link. **988 tests** (8 new, red-first), ruff/check clean, no migration drift; rollback rehearsed. Presentation-only — Patch Track scope held. |
| [patch-profile-form-actions](patch-profile-form-actions/) | [`BUG-002`](../issues/BUG-002.md) (High) | closed-out (released local/dev) | 2026-06-28 | **RESOLVED** — the profile **Edit display name** + **Delete account** forms no longer plain-POST to the JSON `/me` API (the 405 source). Each now posts to a dedicated server-rendered §9 handler (PRG + Django messages): `update_display_name` (reuses `DisplayNameForm`) + `delete_my_account` (reuses the `delete_account` service); dead `data-method` markup removed. `MeView` left byte-unchanged → `/me` contract intact. **997 tests** (9 new, red-first), ruff/check clean, no migration drift; rollback rehearsed. Patch Track scope held. |
| [patch-interest-picker-duplicates](patch-interest-picker-duplicates/) | [`BUG-001`](../issues/BUG-001.md) (Medium) | closed-out (released local/dev) | 2026-06-28 | **RESOLVED** — resolved checkbox and label click targets for tags that appear in multiple active clusters by prefixing HTML IDs with the cluster ID. Added client-side visual sync so duplicate checkboxes check/uncheck each other. **998 tests** (1 new, red-first), ruff/check clean, no migration drift; rollback rehearsed. Patch Track scope held. |
| [patch-try-app-redirect](patch-try-app-redirect/) | [`BUG-004`](../issues/BUG-004.md) (High) | closed-out (released local/dev) | 2026-06-29 | **RESOLVED** (1 000 tests) — `hx-boost` on `<main>` intercepted the Try App anchor; AJAX 302 to cross-origin URL failed. Added `hx-boost="false" target="_blank" rel="noopener noreferrer"` to the anchor; browser now follows the redirect natively. 1 red-first test; ruff/check clean; no migration drift; rollback rehearsed. Patch Track scope held. |
| [patch-my-apps-status-display](patch-my-apps-status-display/) | [`UX-004`](../issues/UX-004.md) + [`UX-006`](../issues/UX-006.md) (Medium) | closed-out (released local/dev) | 2026-06-29 | **RESOLVED** (1 004 tests) — H1 + nav link renamed "My Apps"; flat list replaced with `{% regroup %}`-based sections (Active / Awaiting Review / Needs Changes / Withdrawn); sort by status priority in view; "View live page" link for accepted apps. 4 red-first tests; ruff/check clean; no migration drift; rollback rehearsed. Patch Track scope held. |

> Stage values: see the Patch Track routing table in [../CLAUDE.md](../CLAUDE.md) §2.2
> (`P-plan` · `P-build` · `closed-out`).
