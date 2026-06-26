# OPEN_QUESTIONS — embeddable-update-widget

_Ambiguities, deferrals, and escalations. Any persona may add; resolutions are logged in
[DECISIONS.md](DECISIONS.md)._

| ID | Question | Raised by / stage | Status |
|----|----------|-------------------|--------|
| OQ-EUW-1 | Embedding mechanism — script-tag/iframe widget, a JSON/HTML endpoint the developer renders, or both? (Cross-origin + caching + zero-build-friction for the vibecoded-webapp niche.) | Coordinator seed / pre-1 | open |
| OQ-EUW-2 | Does a widget→platform click-through emit a (non-curated) D-7 signal at MVP, and does it need a new `Surface` value (e.g. `WIDGET`)? Must stay **outside** `ratings.gate.CURATED_SURFACES` (D-8). | Coordinator seed / pre-1 | open |
| OQ-EUW-3 | Anonymous serving — the widget renders to a developer's end users who are not platform accounts; what is read publicly, and what are the rate/abuse limits on an unauthenticated read surface? | Coordinator seed / pre-1 | open |
