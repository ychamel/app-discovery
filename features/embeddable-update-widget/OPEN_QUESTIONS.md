# OPEN_QUESTIONS — embeddable-update-widget

_Ambiguities, deferrals, and escalations. Any persona may add; resolutions are logged in
[DECISIONS.md](DECISIONS.md)._

| ID | Question | Raised by / stage | Status |
|----|----------|-------------------|--------|
| OQ-EUW-1 | Embedding mechanism — script-tag/iframe widget, a JSON/HTML endpoint the developer renders, or both? (Cross-origin + caching + zero-build-friction for the vibecoded-webapp niche.) | Coordinator seed / pre-1 | **open — Stage 2 (design)**; brief AC7 sets the friction bar (drop-in, no build toolchain). |
| OQ-EUW-2 | **How** does a widget impression / click-through emit the non-curated D-7 **source** signal that AC9/EUW-6 now require — the exact `Surface` value (e.g. `WIDGET`), the emit shape, and how `developer-dashboard` reads it to show widget-attributed reach (M2/M3/M4)? Must stay **outside** `ratings.gate.CURATED_SURFACES` (D-8). | Coordinator seed / pre-1 | **open — Stage 2 (design)**. **Product direction now fixed (DN-EUW-BRIEF / EUW-6):** attribution IS required and tracked by source for all users (anonymous incl.); only the *mechanism* is design. The non-curated boundary is fixed by EUW-4/AC6 regardless. |
| OQ-EUW-3 | Anonymous serving — the widget renders to a developer's end users who are not platform accounts; what is read publicly, and what are the rate/abuse limits on an unauthenticated read surface? | Coordinator seed / pre-1 | **open — Stage 2 (design)**; brief AC5/AC8 + EUW-5 fix *what* is public (the app's own published notices + link, nothing private); the *limits* are design. |
| OQ-EUW-4 | Is exposing a developer's published notices as a **public anonymous read** the intended product expansion (today they are follower-feed-only)? | Product Analyst / Stage 1 | **RESOLVED = yes (EUW-5, DN-EUW-BRIEF approved 2026-06-26)** — with the refinement that the view source is tracked for all users (EUW-6 / AC9). |
