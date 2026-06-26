# DECISIONS — embeddable-update-widget

_Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide decisions
go in the top-level [DECISIONS.md](../../DECISIONS.md). This feature is activated by global
**[D-10](../../DECISIONS.md)** (developer-wedge pivot)._

## Stage 1 — Product Analyst (2026-06-26) — RESOLVED (DN-EUW-BRIEF approved — all 5 as recommended, with a source-attribution refinement on EUW-5 → EUW-6)

- **EUW-1 (RESOLVED) — The widget is display-only; it never authors notices.** It renders the
  app's existing published notices (the AS-3 `PublishedNotice` source of truth) + a link back to
  the app page. *Rejected:* a second authoring path inside the widget — would split the
  single-source-of-truth `developer-updates` owns and duplicate state.
- **EUW-2 (RESOLVED) — Capture happens by click-through, not in-widget auth.** The widget links to
  the existing app page; account creation / follow / sign-up use the platform's existing paths. The
  widget itself does no auth UI. *Rejected:* embedding follow/login in a third-party host app —
  large cross-origin auth surface for no MVP gain; the app page already does this.
- **EUW-3 (RESOLVED) — The widget is a FREE single-player tool, not a paid promotion placement.**
  It surfaces a developer's **own** notices; paid promotion placements ([D-9](../../DECISIONS.md))
  are a separate future monetization surface, out of scope here. *Rejected:* folding promo
  placements into this feature — conflates a free tool with the paid surface and bloats scope.
- **EUW-4 (RESOLVED) — Widget interactions are a non-curated surface (the hard firewall).** No
  widget impression or click-through may enter `ratings.gate.CURATED_SURFACES` or confer D-8
  eligibility (brief AC6 / M5 = 0). Binding on Stage 2 regardless of OQ-EUW-2's resolution.
- **EUW-5 (RESOLVED) — Published notices become a public read via the widget.** Today notices show
  only in the follower feed; the widget exposes a developer's **own** app's notices to anonymous
  end users. The developer authors them (implicit consent), and a changelog is public by nature.
  Approved as a deliberate product expansion. **User refinement:** end users are **anonymous when
  not logged in**, but in **all** cases the **source of the view is tracked** — see EUW-6.
- **EUW-6 (RESOLVED) — Widget interactions are tracked by source for developer-dashboard
  attribution.** Per the user's DN-EUW-BRIEF refinement: every widget impression / click-through —
  anonymous or signed-in — is **attributed to the widget as its source**, so the developer can see
  on their dashboard **how many people reached the platform from the widget** (brief **AC9**;
  firms M2/M3/M4). This is a required MVP capability and is **orthogonal to EUW-4/AC6**: tracking a
  source neither confers D-8 eligibility nor moves the Quality Score (the firewall is
  per-impression, not per-user). *Rejected:* leaving attribution unspecified / dashboard-only-later
  — the user explicitly wants widget-sourced reach visible to the developer at MVP. **Mechanism
  (the `Surface` value, the D-7 emit shape, and the `developer-dashboard` read) is Stage-2 design —
  OQ-EUW-2.**

> **Stage-2 design questions (NOT decided here):** the embedding mechanism (OQ-EUW-1); *how* the
> non-curated widget-source signal is emitted / whether a new `Surface` (e.g. `WIDGET`) is added
> and how `developer-dashboard` reads it for AC9/M2-M4 attribution (OQ-EUW-2); and the rate/abuse
> limits on the public read (OQ-EUW-3). See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
