# issues/ — Unified Issue Registry & Triage Hub

This directory acts as the central intake valve and registry for all **Bugs, UX/Design Issues, and Open Questions** in the repository. By unifying these categories under one section, we maintain a single source of truth for repository health and outstanding decisions before routing them to either the **Feature Track** or the **Patch Track** (defined in [CLAUDE.md](../CLAUDE.md) §2).

---

## 1. Issue Types & Prefixes

We categorize and track intake items using distinct prefixes to ensure they receive the correct level of detail and routing:

| Prefix | Type | Description | Target Pipeline / Route |
| :--- | :--- | :--- | :--- |
| `BUG-` | **Bug Report** | Functional defects or errors where the system behaves incorrectly. | Patch Track (if no schema/API changes) or Feature Track. |
| `UX-` | **UX/Design Issue** | Usability gaps, visual polish debt, layout flaws, or flow improvements. | Patch Track (if simple CSS/HTML tweaks) or Feature Track. |
| `Q-` | **Open Question** | Architectural ambiguities, technical questions, or unresolved product decisions. | Strategic discussion -> update `STRATEGY.md` or active feature `OPEN_QUESTIONS.md`. |

---

## 2. Issue Lifecycle & Triage

```mermaid
graph TD
    A[Log Issue: BUG / UX / Q] -->|Status: NEW| B(Triage Gate)
    B -->|Invalid / Not Actionable| C[Status: REJECTED]
    B -->|Open Question resolved| D[Status: ANSWERED]
    B -->|Valid Actionable Bug/UX| E{Patch Track Scope Gate}
    E -->|Requires Migration/API/ADR| F[Promote to Feature Track Stage 1]
    E -->|No Schema/API/ADR Changes| G[Status: TRIAGED]
    G -->|Create patches/patch-slug/| H[Status: IN-PROGRESS]
    H -->|Maintenance Planner P-plan| I[Maintenance Engineer P-build]
    I -->|Verify & Release| J[Status: RESOLVED]
```

1. **Log**: Create a new Markdown file in this directory (e.g., `BUG-002.md`, `UX-001.md`, or `Q-001.md`) using the appropriate template below. Set its status to `NEW`.
2. **Triage**: The Coordinator reviews the issue:
   - **Questions (`Q-`)** are discussed, answered, and marked `ANSWERED`. If they lead to product decisions, they are logged in `DECISIONS.md` or `STRATEGY.md`.
   - **Bugs/UX (`BUG-` / `UX-`)** are evaluated against the **Patch Track Scope Gate** (no migrations, no public API changes, no global ADR updates).
     - If it fits the Patch Track, set status to `TRIAGED`, assign a `patch-` slug, and create its patch folder. Set status to `IN-PROGRESS`.
     - If it violates the gate, promote it to the Feature Track (create `features/slug/` and set `Stage: 1-define`).
3. **Resolution**: Once released, update the issue status to `RESOLVED` (or `ANSWERED` for questions) and link the corresponding release or feature.

---

## 3. Unified Issues Registry

Every issue logged in this directory must have a corresponding row in this table.

| ID | Type | Date Reported | Reporter | Summary | Severity / Priority | Status | Issue File | Associated Path / Link |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BUG-000` | Bug | 2026-06-28 | QA Team | App detail page profile link broken when anonymous | Medium | `RESOLVED` | [`BUG-000.md`](BUG-000.md) | [`patches/patch-anonymous-profile-link/`](../patches/patch-anonymous-profile-link/) |
| `BUG-001` | Bug | 2026-06-28 | Developer / QA Team | Interest picker duplicate subcategories label click highlights previous occurrence | Medium | `RESOLVED` | [`BUG-001.md`](BUG-001.md) | [`patches/patch-interest-picker-duplicates/`](../patches/patch-interest-picker-duplicates/) — closed-out (released local/dev): unique cluster ID-prefixed HTML IDs + client-side sync JS |
| `BUG-002` | Bug | 2026-06-28 | User / Developer | Profile display name update fails with 405 Method Not Allowed and idles | High | `RESOLVED` | [`BUG-002.md`](BUG-002.md) | [`patches/patch-profile-form-actions/`](../patches/patch-profile-form-actions/) — closed-out (released local/dev): both forms repointed to server-rendered §9 handlers; `/me` contract untouched |
| `BUG-003` | Bug | 2026-06-28 | User | Selected reporting period shows literal `{{ w.label }}` in the developer dashboard | Medium | `RESOLVED` | [`BUG-003.md`](BUG-003.md) | [`patches/patch-dashboard-window-label/`](../patches/patch-dashboard-window-label/) — closed-out (released local/dev): joined both multiline tags onto one line (`{{ w.label }}` + a sibling `{{ summary.curated_impressions }}` found by a repo-wide sweep); template + 1 red-first test, no schema; 999 tests |
| `UX-002` | UX | 2026-06-28 | Developer / User | App registration tags selection is overwhelming and niche selection is difficult | Medium | `TRIAGED` | [`UX-002.md`](UX-002.md) | Patch Track (queued) — scope = **(a) minimal** per `DN-UX002-SCOPE`: client-side search/filter + light grouping over the existing list (no schema/API); the full (b) overhaul logged as a future Feature-Track bet |
| `UX-003` | UX | 2026-06-28 | User | No navigation path to view and manage pending/withdrawn app submissions | High | `RESOLVED` | [`UX-003.md`](UX-003.md) | [`patches/patch-developer-submissions-nav/`](../patches/patch-developer-submissions-nav/) |
| `Q-001` | Question | 2026-06-28 | Developer / QA Team | Duplicate vs. Unique Interest Subcategories Design Choice | Medium | `ANSWERED` | [`Q-001.md`](Q-001.md) | **Option 1 — keep duplicate** (`DN-Q001-TAXONOMY`): schema unchanged; a tag may sit under multiple clusters. `BUG-001`'s core fix (unique per-cluster HTML IDs) is the path; optional cross-cluster JS sync only if wanted. A better model can come later as a Feature-Track bet. |
| `UX-004` | UX | 2026-06-29 | User | "My Submissions" label is misleading after approval; no status-based grouping or tags | Medium | `RESOLVED` | [`UX-004.md`](UX-004.md) | [`patches/patch-my-apps-status-display/`](../patches/patch-my-apps-status-display/) — closed-out (released local/dev): H1 + nav renamed "My Apps"; status-grouped sections (Active/Awaiting Review/Needs Changes/Withdrawn); 1004 tests |
| `Q-002` | Question | 2026-06-29 | User | Should a user be able to submit a review for their own app? | Medium | `IN-PROGRESS` | [`Q-002.md`](Q-002.md) | **Answered Option A — block self-review** (DN-Q002) → [`patches/patch-block-self-interaction/`](../patches/patch-block-self-interaction/) (bundled with `Q-003`; owner guard + template hide, no schema) |
| `Q-003` | Question | 2026-06-29 | User | Should a user be able to follow their own app? | Low | `IN-PROGRESS` | [`Q-003.md`](Q-003.md) | **Answered Option A — block self-follow** (DN-Q003) → [`patches/patch-block-self-interaction/`](../patches/patch-block-self-interaction/) (bundled with `Q-002`; owner guard + template hide, no schema) |
| `Q-004` | Question | 2026-06-29 | User | Should apps display an aggregate review score; should curated ratings be shown separately? | Medium | `NEW` | [`Q-004.md`](Q-004.md) | TBD |
| `BUG-004` | Bug | 2026-06-29 | User | "Try App" button links to platform URL instead of the app's own external URL | High | `RESOLVED` | [`BUG-004.md`](BUG-004.md) | [`patches/patch-try-app-redirect/`](../patches/patch-try-app-redirect/) — closed-out (released local/dev): added `hx-boost="false" target="_blank" rel="noopener noreferrer"` to the Try App anchor; browser follows the 302 natively to the external URL. 1 red-first test; 1 000 tests green; no migration drift; rollback rehearsed |
| `BUG-005` | Bug | 2026-06-29 | User | "Share" button does not work on localhost; fallback behaviour unclear | Low–Medium | `TRIAGED` | [`BUG-005.md`](BUG-005.md) | `patch-share-button-fallback` (queued, JS fallback only — Patch Track) |
| `UX-005` | UX | 2026-06-29 | User | No way for developers to preview their app page before approval | Medium | `TRIAGED` | [`UX-005.md`](UX-005.md) | `patch-developer-app-preview` (queued, view-logic bypass for owner — Patch Track) |
| `UX-006` | UX | 2026-06-29 | User | No direct link from "My Submissions" to the public app page post-approval | Medium | `RESOLVED` | [`UX-006.md`](UX-006.md) | [`patches/patch-my-apps-status-display/`](../patches/patch-my-apps-status-display/) — closed-out (released local/dev): "View live page" link added to accepted app cards; 1004 tests |


---

## 4. Templates

### Bug Report Template (`BUG-XXX.md`)
```markdown
### `BUG-XXX`: [Short Summary of the Defect]

- **Reporter:** [Your Name / Team]
- **Date Reported:** YYYY-MM-DD
- **Severity:** [Critical (Blocker) / High / Medium / Low]
- **Status:** `NEW`
- **Patch/Feature Slug:** `TBD`

#### Description & Impact
[Provide a clear description of what is happening and the impact on the user or system.]

#### Steps to Reproduce
1. [Go to...]
2. [Click on...]
3. [Observe...]

#### Expected Behavior
[What should have happened instead.]

#### Actual Behavior & Details
[What actually happened. Paste traceback, error codes, logs, console output, or screenshots here.]
```

### UX/Design Issue Template (`UX-XXX.md`)
```markdown
### `UX-XXX`: [Short Summary of the Usability/Visual Issue]

- **Reporter:** [Your Name / Team]
- **Date Reported:** YYYY-MM-DD
- **Priority:** [High / Medium / Low]
- **Status:** `NEW`
- **Patch/Feature Slug:** `TBD`

#### UX Observation
[Describe the usability gap, visual polish debt, layout inconsistency, or flow friction.]

#### Impact & User Friction
[How does this affect the user experience? E.g., cognitive load, visual confusion, missed calls to action.]

#### Suggested Improvement
[Describe the recommended visual design change, layout adjustment, or interactive refinement.]

#### Visual References / Markup
[Paste CSS selectors, HTML snippets, class names, or wireframe references if applicable.]
```

### Open Question Template (`Q-XXX.md`)
```markdown
### `Q-XXX`: [Short Summary of the Question]

- **Reporter:** [Your Name / Team]
- **Date Reported:** YYYY-MM-DD
- **Category:** [Architecture / Product / Strategy / Tech Stack]
- **Status:** `NEW`

#### The Question / Ambiguity
[State the clear question or ambiguity that needs to be addressed.]

#### Context & Alternatives
[Provide background context on why this question arises and the different alternatives/options under consideration.]

#### Proposed Resolution / Answer (To be filled during triage)
[Once discussed and resolved, record the final answer, decision rationale, and link to any global ADR or STRATEGY.md updates.]
```
