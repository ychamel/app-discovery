# DECISIONS.md — interface-cleanup

Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide decisions live in the
global [../../DECISIONS.md](../../DECISIONS.md).

---

## IC-D-1 — Scope = cleanup layer only; the distinctive rebrand stays `ui-modernization`

**Date:** 2026-06-30 · **Decided by:** user (Coordinator-surfaced via AskUserQuestion) · **Status:** ratified

**Decision.** `interface-cleanup` covers the **consistency / silent-defect / experiential-fix** layer
(walkthrough findings A1, A2, A5, the active-state part of A6, and the B-level per-surface fixes). The
**distinctive rebrand** — new brand palette, stylized/animated navigation, and premium motion language
(findings A3/A4) — is **explicitly excluded** and remains the separate, held **`ui-modernization`**
Feature-Track bet, activated by a future user decision.

**Why.** The held `ui-modernization` bet (recorded at premium-frontend close-out and in standing
memory) is a deliberate, separately-decided strategic feature needing its own Stage-1→2 design.
Folding it into a cleanup pass would (a) balloon scope, (b) blur a clean strategic boundary, and
(c) couple low-risk presentation fixes to a high-judgment redesign. Keeping cleanup boring and
shippable is the higher-value sequencing.

**Rejected:** "Absorb the rebrand too" (one mega-feature superseding `ui-modernization`) — rejected by
the user in favour of the clean boundary.

---

## IC-D-2 — Runs on the Feature Track (not a single patch), within the patch *envelope*

**Date:** 2026-06-30 · **Decided by:** user + Coordinator · **Status:** ratified

**Decision.** This work runs on the **Feature Track** (Stages 1→5), even though, taken individually,
it introduces **no schema/migration, no public-API change, and no global-ADR change** — i.e. it stays
inside what the Patch Track *scope gate* ([../../CLAUDE.md](../../CLAUDE.md) §2) would permit.

**Why.** It is a **large, cross-cutting, coordinated** change (a design-system consolidation touching
~30 templates plus a connected set of experiential fixes) that the user chose to "address in one go."
That benefits from explicit **Design** (consolidation depth, icon mechanism, mobile-reflow technique)
and **Plan** stages and a per-surface sign-off — more than a single patch can carry. The patch
*envelope* (no schema/API/ADR — brief C2) is retained as a **constraint** so the feature stays
low-risk and reversible; any finding that breaks that envelope is pulled out and re-routed, not forced
through.

**Rejected:** splitting into many independent patches — rejected as inefficient and because it
wouldn't address the shared root cause (the design system not being the single source of truth), which
needs one coordinated design.

---

## IC-D-3 — Preserve the app-page-redesign invariants while moving the mobile CTA

**Date:** 2026-06-30 · **Decided by:** Product Analyst · **Status:** ratified (brief constraint C1/AC-4)

**Decision.** The app-page mobile **Try**-reachability fix is delivered as a **purely presentational,
uniform responsive reflow** that keeps the DOM **slot order/fingerprint unchanged**, so the
[app-page-redesign](../app-page-redesign/) **uniform-slot-order** and **M5=0 firewall** invariants
continue to pass as the gate.

**Why.** app-page-redesign's uniformity guarantee (vision §4 integrity) is load-bearing and tested; a
cleanup must not erode it. Reordering layout for small viewports is fairness-neutral (applied
identically to every app) as long as the structural slot order is untouched.
