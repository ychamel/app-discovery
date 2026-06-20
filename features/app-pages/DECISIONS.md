# DECISIONS — app-pages

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

> Stage-1 scoping calls below are **provisional pending brief approval** (CONTROL.md
> DN-9). They reuse the global contracts D-1/D-5/D-6/D-7 as-is — no new global decision
> is proposed by this feature at Stage 1.

### AP-1: Reviews are a slot, not content, at the app-pages MVP
- **Date:** 2026-06-19
- **Stage / feature:** `1-define` / app-pages (Product Analyst)
- **Decision:** The uniform template includes a **reviews section slot rendered as an
  empty state**; app-pages does **not** capture, store, weight, or display ratings/reviews,
  nor implement the curated-rating gate. All review content is owned by `ratings-reviews`.
- **Why:** `ratings-reviews` depends on app-pages and does not exist at app-pages' build
  time, so there is no review source to render; the breakdown §4.2 "reviews block" is
  satisfied at MVP by reserving the slot, keeping the boundary clean (CLAUDE.md §5.4
  one-source-of-truth, §6.4 stay-in-scope). Avoids R4 scope bleed.
- **Alternatives rejected:** (a) Build minimal rating capture in app-pages now — duplicates
  what `ratings-reviews` owns and forecloses the gate design that feature must make. (b)
  Omit the slot entirely — would force a template change (non-uniform churn) when reviews
  land. → tracked as OQ-1; confirmed by DN-9.

### AP-5: Public page URL is keyed on `App.id` and indexable
- **Date:** 2026-06-20
- **Stage / feature:** `2-design` / app-pages (Software Architect)
- **Decision:** The public page lives at `apps/<App.id (UUID)>/` — keyed on the **stable D-6
  UUID handle**, never on a name/slug — and is **indexable** (no `noindex`; canonical `<link>`
  = the same URL). Resolves OQ-4. **Built at Stage 4 — routes in `apps/pages/urls.py` use the
  `<uuid:app_id>` converter; `app_page.html` emits a canonical `<link>` + copyable URL.**
- **Why:** AC4 requires a link that **survives metadata edits**; only the immutable `App.id`
  does (a name/slug mutates when the developer edits it). Indexability serves the open-access
  discovery premise (A1, vision §4.1) — nothing on the page is secret.
- **Alternatives rejected:** A human-readable slug URL — breaks AC4 the moment the name is
  edited, and a slug→id redirect table is owned content app-pages otherwise has none of (no
  speculative scope). `noindex` — contradicts the open-discovery premise.

### AP-4: Signal capture is authenticated-only; rendering is fully anonymous
- **Date:** 2026-06-20
- **Stage / feature:** `2-design` / app-pages (Software Architect)
- **Decision:** Any visitor — signed-in or **anonymous** — gets the **full page** (AC5).
  Behavioral capture (page-view impression, try-it click-through, share) happens **only for
  authenticated visitors**; an anonymous try-it/share still works but writes **no** event.
  Resolves the AC5 ∩ AC6 tension. **Confirmed: DN-10 → approved (2026-06-20); built in
  `apps/pages/emission.py` (the `request.user.is_authenticated` gate) at Stage 4.**
- **Why:** The D-7 corpus is keyed `user × App.id` and `signals.capture.*` requires a real
  authenticated `user`; an anonymous actor has no identity the corpus can attribute returns/
  rings to. Rendering needs no capture, so AC5 (open render) and AC6 (capture for the
  representable case) are both honored. Side benefit: crawlers are anonymous → zero impression
  inflation / write-amplification (bounds R5).
- **Alternatives rejected:** (a) Extend D-7 with an anonymous/sessionless actor id now — a
  change to an approved global schema for marginal MVP signal; named as a deferred growth path,
  not built (§5.5 no speculative abstraction). (b) Gate the page behind login to capture
  everyone — violates AC5 open access outright.

### AP-3: A page view is an `app_page`-surface impression; try-it/share link to it
- **Date:** 2026-06-20
- **Stage / feature:** `2-design` / app-pages (Software Architect)
- **Decision:** When an authenticated visitor loads an app page, app-pages records a D-7
  `Impression` with **`surface = app_page`** (the app *was* shown). A try-it click is a
  `click_through` **linked to that impression**; a share links to it (optional). This requires
  adding **`Surface.APP_PAGE`** to `apps/signals/kinds.py` — the **additive extension D-7
  pre-authorizes** (kinds.py names `app_page` explicitly). Resolves OQ-2. *Raised for
  confirmation as part of DN-10 because it reinterprets the brief's "impression generation is
  out of scope" bullet (see Why).* **Confirmed: DN-10 → approved (2026-06-20); built at Stage 4
  — `Surface.APP_PAGE` added (`apps/signals/kinds.py` + reversible migration `0002`), page-view
  impression + linked try-it/share wired through `apps/pages/emission.py`.**
- **Why:** `signals.capture.record_click_through` **requires** an originating impression, but a
  direct/search visit has no *digest* impression. Treating the page view as the impression (a)
  satisfies that requirement with **no contract change**, (b) is **additive-only** (one enum
  value), and (c) is the **only** way the brief's own metric — "click-through *rate* per page
  view" — is measurable (the conversion-less page-view impression is the rate's denominator).
  Reconciles with the out-of-scope line: app-pages does **not** run the impression allocator or
  generate *curated-feed (digest-surface)* shows — it records an `app_page`-surface shown
  instance, a distinct thing the `surface` field keeps segregated from digest CTR.
- **Alternatives rejected:** (b) Make `click_through`'s impression optional — a change to an
  approved, additive-only global schema (D-7) for a problem one enum value solves. (c) A new
  event kind for "page click" — duplicates `click_through` and fragments the funnel. (d) Capture
  nothing until `weekly-digest` exists — guts AC6 and the H1 metric at MVP (every visit is
  impression-less today). → tracked as OQ-2.

### AP-2: Press kit at MVP = the public page itself, no separate press apparatus
- **Date:** 2026-06-19
- **Stage / feature:** `1-define` / app-pages (Product Analyst)
- **Decision:** The "press kit / web home" role (vision §6) is realized **by the public
  page + a stable shareable link + the media already in submission**. No separate
  downloadable press-asset bundle, press-contact field, or embargo control is in the MVP.
- **Why:** The page is already self-contained and shareable (AC4); extra press apparatus is
  speculative scope (CLAUDE.md §5.5 no speculative abstraction) better placed in a later
  dev-facing feature if demand appears. Keeps app-pages a read-only render over the D-6
  catalog.
- **Alternatives rejected:** Build press-asset downloads / press-contact now — adds owned
  content and editing surface app-pages otherwise has none of, for no MVP-validated need.
  → tracked as OQ-3; confirmed by DN-9.
