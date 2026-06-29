# DESIGN.md — app-page-redesign

*Stage 2 (Software Architect) — **APPROVED 2026-06-29** (DN-APR-DESIGN; APR-DESIGN-1/2 → global [D-14](../../DECISIONS.md)). Handed to the Planner (Stage 3).*

> Inputs read: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md); [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
> (Q1–Q4 + the uniformity guardrail); the live page
> ([`app_page.html`](../../apps/pages/templates/pages/app_page.html)) + view
> ([`pages/views.py`](../../apps/pages/views.py)); the catalog model
> ([`models.py`](../../apps/catalog/models.py)), read path
> ([`selectors.py`](../../apps/catalog/selectors.py)), write path
> ([`services.py`](../../apps/catalog/services.py)), gate ([`gate.py`](../../apps/catalog/gate.py)),
> forms/views ([`forms.py`](../../apps/catalog/forms.py) / [`views.py`](../../apps/catalog/views.py));
> the devlog read path ([`updates/selectors.py`](../../apps/updates/selectors.py)); [CODEMAP.md](../../CODEMAP.md);
> [DECISIONS.md](../../DECISIONS.md) ([D-4](../../DECISIONS.md)/[D-5](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md)/[D-13](../../DECISIONS.md)).
>
> **Two user decisions taken at Stage 2 (AskUserQuestion, 2026-06-29):**
> **(OQ1)** typed facets = **code-fixed structured fields**, kept out of the [D-5](../../DECISIONS.md)
> tag pool and out of ranking; the existing category tags stay as-is.
> **(re-review)** new public-claim fields **are gate-relevant**, *but* which fields force re-review
> is **config-togglable** (default: all on) so it can be tuned from deployment behaviour without a
> code change. Both ratified below as **APR-DESIGN-1 / APR-DESIGN-2** and promoted to global **D-14**.

---

## 1. Reasoning trace (the 14-step protocol, condensed)

1. **SCOPE.** Turn the uniform *listing* page into a uniform *launch page + developer hub*: add a
   pitch line, an in-action demo clip, typed facets, an expandable deep-dive, a developer-identity
   block, and an on-page devlog — every slot offered equally to every accepted app, none unlocked
   by tier/payment/identity. Stakeholders: wedge developers + their visitors. Lifespan: **platform**
   (this is the wedge's public face, [D-10](../../DECISIONS.md)) — rigor matches.
   *Out:* hosted video infra, follow-the-developer, community Q&A (all [APR-D-1](DECISIONS.md)),
   monetization/checkout, any ranking/discovery change.
2. **REQUIREMENTS.** Functional = AC-1…AC-9. Non-functional: server-rendered no-build
   ([D-4](../../DECISIONS.md)/[D-13](../../DECISIONS.md)); no-JS is the source of truth (AC-4/C5);
   every media item has alt text (C5); the devlog reuses the existing read path with **M5=0** intact
   (AC-6/C3); uniformity is a tested structural invariant (AC-7/R2). Assumptions A1/A2 stay
   unverified → measured post-deploy (M4/M5), not designed around.
3. **CONTEXT.** Reuse-first inventory in §2. The page is a thin D-6/D-7 consumer owning no model;
   all content comes from `catalog.selectors`; reviews/follow are already inclusion tags; the devlog
   producer (`updates.selectors.published_notices_for_apps`) already exists and imports nothing from
   `signals`. The design **adds to the catalog model + read path** and **adds one inclusion tag**, and
   changes the page template — it invents no new app and no new cross-cutting concern.
4. **MODULES.** §4. New: a code-fixed `catalog/facets.py` (pure declaration, mirrors `gate.py`); an
   `AppFacet` table + the new `App` columns; a page-scoped `AppPageContent` read in `catalog.selectors`;
   an `{% app_devlog app %}` inclusion tag in `apps/updates`. Each has one job, is testable in isolation.
5. **INTERFACES.** §6 (selector DTOs + signatures), §5 (the facet registry contract), §8 (write-path
   params), §7 (template slot contract). No "TBD".
6. **DATA & STATE.** §5. One source of truth per fact: facet vocabulary in code, facet *values* in
   `AppFacet`, marketing copy in new `App` columns, devlog in `updates` (unchanged). Additive
   migration, no backfill (new fields default empty → graceful-empty, M2).
7. **FAILURE.** §9. The catalog-owned page read fails **loud** (it *is* the page); cross-app
   enrichments (devlog, reviews, follow) are **fail-soft inclusion tags** — the existing split.
8. **CHANGE.** Most-likely-to-change = (a) *which* fields force re-review → **config toggle**
   (APR-DESIGN-2); (b) the facet vocabulary → **one code file** (`facets.py`); (c) limits (clip size,
   devlog count, other-apps count) → **`config.py`**. Irreversible = the additive migration (§10).
9. **TRADE-OFFS.** §11 — facets-as-structured-fields vs taxonomy vs JSON; page-scoped read vs
   fattening the shared `CatalogApp`; muted-loop clip vs GIF vs hosted video.
10. **SECURITY.** §9.4 — auto-escaped developer text (no raw HTML), closed-enum facets, generated
    clip filenames + size cap, accepted-only "other apps" (no unpublished leak), display-name-only
    identity (no new PII).
11. **OPERATIONS.** §9.5 — reuse `APP_PAGE_RENDERED`; add `APP_PAGE_DEVLOG_DEGRADED`; rollback =
    git revert + reverse migration (DU-REL-1 pattern, §10).
12. **TESTS.** §12 — every AC mapped; uniformity + firewall as hard invariants; empty/legacy-app
    graceful-empty cases.
13. **SELF-CRITIQUE.** §13.
14. **DELIVER.** §10 (smallest-useful first version + increments) + §14 (decisions/ADR).

---

## 2. Current-state summary (what exists, diffable against the change)

- **The page is a pure consumer.** [`pages/views.app_page`](../../apps/pages/views.py#L30) calls
  [`catalog.get_catalogued_app(app_id)`](../../apps/catalog/selectors.py#L274) → a `CatalogApp`
  (`id, name, description, url, tags, media` — **no owner, no facets, no marketing copy**), renders
  [`app_page.html`](../../apps/pages/templates/pages/app_page.html) (six fixed slots), and emits a
  fail-soft `app_page` impression. `try`/`share` also read `get_catalogued_app` (only for `url`).
- **`CatalogApp` is a shared cross-feature contract** (D-6) consumed by discovery, dashboard,
  subscriptions-feed, and widget. Adding page-only fields to it would bloat every consumer — avoided
  (§4 / §11b).
- **The catalog model** ([`models.py`](../../apps/catalog/models.py)): `App` (owner FK → `Account`,
  name/description/url/status/…), `AppTag` (soft `tag_id`, D-5), `AppMedia` (ordered image),
  `ReviewDecision`. **Fairness is structural** — no tier/payment/priority field exists (AC-7/R2).
- **The write path** ([`services.py`](../../apps/catalog/services.py)) is the single mutate surface;
  [`edit_app`](../../apps/catalog/services.py#L113) already returns an *accepted* app to `pending`
  when a field in [`gate.GATE_RELEVANT_FIELDS`](../../apps/catalog/gate.py#L67) changes — the exact
  seam the re-review toggle plugs into. `submit_app` validates the required floor (name/desc/url/≥1
  tag/≥1 image); new fields will be **optional**, so the submission floor is unchanged.
- **Authoring surfaces:** the server-rendered [`SubmissionForm`](../../apps/catalog/forms.py#L17) +
  `submit.html`/`app_detail.html`, and the DRF API ([`AppCreateView`](../../apps/catalog/views.py#L82)/
  [`AppDetailView.patch`](../../apps/catalog/views.py#L120)). Both call the same services (one source
  of truth). New fields are surfaced through both.
- **The devlog producer already exists:**
  [`updates.published_notices_for_apps(app_ids, *, limit)`](../../apps/updates/selectors.py#L54)
  returns PII-free `PublishedNotice` DTOs and the `updates` app imports nothing from `signals`
  (AST-enforced) → surfacing it is a **read only**, M5=0 by construction (AC-6/C3/R4).
- **Reviews + Follow are already inclusion tags** (`{% app_reviews %}` / `{% app_follow %}`,
  fail-soft) — the devlog will follow the identical pattern.
- **The design system is build-free** ([D-13](../../DECISIONS.md)): one token-driven
  `core/app.css`; existing classes the page already uses (`card`, `stack`, `cluster`, `badge`,
  `btn`, `empty-state`, `visually-hidden`, `screenshots-gallery`, `app-page-main/-sidebar/-reviews`).

## 3. Proposed architecture (overview)

```
pages/views.app_page(app_id)
   │  (non-accepted/unknown → 404; read raises → loud 500 — unchanged split)
   ▼
catalog.selectors.get_app_page_content(app_id) -> AppPageContent | None    ◄── NEW page-scoped read
   ├─ reuses _to_catalog_app(...)        → id/name/description/url/tags/media   (template-stable)
   ├─ + tagline / deep_dive              (new App columns)
   ├─ + demo_clip_url / demo_clip_alt    (new App column + alt)
   ├─ + facets: list[CatalogFacet]       (AppFacet rows resolved through catalog/facets.py registry)
   ├─ + developer: CatalogDeveloper      (owner.display_name — no new PII)
   └─ + other_apps: list[CatalogApp]     (bounded, ACCEPTED-only, excludes this app)
   ▼
app_page.html  (uniform fixed slot set, §7)
   ├─ catalog-owned slots render from AppPageContent (fail LOUD with the read)
   └─ cross-app enrichment slots are fail-soft inclusion tags:
        {% app_devlog app %}   ◄── NEW (apps/updates/templatetags) → published_notices_for_apps
        {% app_reviews app %}  (unchanged)
        {% app_follow app %}   (unchanged)

WRITE (one source of truth = catalog.services):
   submit_app / edit_app  gain optional: tagline, deep_dive, facet_values, demo_clip (+ alt)
   gate.gate_relevant_fields()  ◄── NEW: core floor ∪ config-toggled new fields (re-review seam)
   catalog/facets.py            ◄── NEW: code-fixed facet vocabulary + is_valid_facet_value()
```

**Coupling check.** Every new edge points at an existing stable surface: the page reads only
`catalog.selectors`; the devlog tag reads only `updates.selectors`; facets are validated by a pure
local declaration. No new app, no new cross-cutting concern. **Design-for-deletion:** removing the
redesign = delete `facets.py`, the inclusion tag, the new columns/table, and `AppPageContent`, and
restore the template — `CatalogApp` and every other consumer are untouched.

## 4. Modules (single responsibilities)

| Module | Owns | Exposes | Hides |
|---|---|---|---|
| `apps/catalog/facets.py` **(new)** | the **code-fixed** facet vocabulary (declaration only, no DB, mirrors `gate.py`) | `FACETS`, `FacetDef`/`FacetValue`/`FacetCardinality`, `is_valid_facet_value()`, `facet_keys()`, `resolve_facets(rows)` | the value lists (one edit site) |
| `apps/catalog/models.py` (extend) | `AppFacet` table + new `App` columns | `AppFacet`, `App.tagline/deep_dive/demo_clip/demo_clip_alt` | storage details |
| `apps/catalog/services.py` (extend) | the **single** write path for the new fields | optional params on `submit_app`/`edit_app`; clip validation | invariants/atomicity |
| `apps/catalog/gate.py` (extend) | the re-review seam | `gate_relevant_fields() -> frozenset[str]` (replaces the constant) | the config toggle wiring |
| `apps/catalog/selectors.py` (extend) | the **page-scoped** read | `AppPageContent`, `CatalogFacet`, `CatalogDeveloper`, `get_app_page_content()`, `accepted_apps_by_owner()` | tag/facet/owner resolution |
| `apps/updates/templatetags/updates_tags.py` **(new)** | the devlog slot | `{% app_devlog app %}` (fail-soft) | the capped read + degrade |
| `apps/pages/templates/pages/app_page.html` (rewrite) | the uniform slot layout | the fixed slot set (§7) | nothing app-identity-driven |

Each is testable in isolation: `facets.py` is pure; `AppPageContent` is a selector test against
seeded rows; the inclusion tag is a template-tag test; the template is a render test.

## 5. Data design

### 5.1 New `App` columns (additive, all optional → graceful empty, M2)

| Column | Type | Rule (write boundary) | Source of truth |
|---|---|---|---|
| `tagline` | `CharField(max_length=300, blank=True, default="")` | stripped; ≤300 (the pitch / meta-description, AC-1) | the dev's pitch |
| `deep_dive` | `TextField(blank=True, default="")` | stripped; bounded by `config.app_page_deep_dive_max_length()` (default 8000) | the dev's long-form (AC-4) |
| `demo_clip` | `FileField(upload_to="app_clips/%Y/%m/", blank=True, null=True)` | container is MP4/WebM (magic-bytes + extension), size ≤ `config.catalog_clip_max_bytes()` (default 10 MB), stored under a **generated** name (AC-2) | the dev's demo loop |
| `demo_clip_alt` | `CharField(max_length=200, blank=True, default="")` | required textual description **iff** a clip is set (C5/A4) | accessibility text |

`null=True` only on `demo_clip` (FileFields store `""` poorly); text columns use `blank=True,
default=""` (never NULL — one empty representation). **No tier/payment/identity column is added** —
AC-7/R2 stays structurally true.

### 5.2 `AppFacet` (new table — the typed-facet store, mirrors `AppTag`)

```python
class AppFacet(models.Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    app = ForeignKey(App, on_delete=CASCADE, related_name="app_facets")
    facet = CharField(max_length=32)   # a FACETS key (code-fixed); soft ref, validated at write
    value = CharField(max_length=48)   # a value key within that facet; soft ref, validated at write
    class Meta:
        db_table = "catalog_app_facet"
        constraints = [UniqueConstraint(fields=["app", "facet", "value"],
                                        name="catalog_app_facet_unique")]
        indexes = [models.Index(fields=["app"], name="catalog_app_facet_app_idx")]
```

- **Soft, code-validated reference** (the D-5 pattern): `facet`/`value` are validated against
  `facets.is_valid_facet_value()` at the write boundary and **resolved through the registry at read**
  — a value later removed from the registry is silently dropped at display (graceful, like
  `resolve_tag`), never an error.
- **Cardinality** (single vs multi) is a property of the `FacetDef` in code, enforced in the service
  (`submit_app`/`edit_app` refuse a 2nd value for a `SINGLE` facet). The unique constraint stops
  duplicate values; cardinality stops illegal multiplicity → **illegal states unrepresentable**.
- **Firewalled from ranking/discovery (AC-3, D-14):** `AppFacet` is **not** `AppTag`; it never enters
  `search_catalogue`'s tag filter or `interests.declared_tag_ids`. Facets are display-only in v1.

### 5.3 Facet vocabulary (code-fixed — `catalog/facets.py`)

Pure declaration, no DB, no migration to read, no editorial mutation path (the `gate.py` precedent).
The initial closed vocabulary (the **one** edit site to change it):

| `facet` key | cardinality | value keys |
|---|---|---|
| `pricing` | SINGLE | `free`, `freemium`, `paid`, `subscription` |
| `maturity` | SINGLE | `concept`, `alpha`, `beta`, `early_access`, `live` |
| `modality` | MULTI | `single_player`, `multiplayer`, `collaborative`, `online`, `offline`, `realtime`, `async` |
| `platform` | MULTI | `web`, `pwa`, `desktop`, `mobile` |

(Category/"genre" is **not** a facet — it stays the existing D-5 taxonomy tags already shown in the
header; OQ1 resolution. Adding/removing a facet or value is a one-file change.)

### 5.4 Ownership / lifecycle / retention

- Marketing columns + `AppFacet` rows are **owned by the app**, CASCADE-deleted with it (consistent
  with `AppTag`/`AppMedia`). Written **only** through `catalog.services`.
- `demo_clip` files live on the same media storage as screenshots (served by
  [`core.views.serve_media`](../../apps/core/views.py) in all envs — the documented single-node
  staging trade-off, object-store the growth path, [D-12](../../DECISIONS.md)). No transcoding/CDN.
- **Migration:** one additive migration (4 columns + 1 table + indexes). **No backfill** — existing
  apps get empty fields and render the graceful-empty state (M2). Reverse migration drops them cleanly
  (the only data loss on rollback is authored facet/marketing content, documented in §10).

## 6. Interface contracts (read side — no "TBD")

```python
# apps/catalog/selectors.py  (additive; CatalogApp/CatalogTag/CatalogMedia unchanged)

@dataclass(frozen=True)
class CatalogDeveloper:
    id: UUID
    display_name: str            # the only owner field exposed (already public; no PII added)

@dataclass(frozen=True)
class CatalogFacet:
    facet: str                   # registry key, e.g. "pricing"
    label: str                   # resolved display label, e.g. "Pricing"
    values: list[FacetValue]     # resolved, in registry order; [] if none set (caller hides empty)

@dataclass(frozen=True)
class AppPageContent:
    # --- the existing CatalogApp shape, flat, so the template keeps using app.name/.tags/.media ---
    id: UUID
    name: str
    description: str
    url: str
    tags: list[CatalogTag]
    media: list[CatalogMedia]
    # --- new page-only content (each degrades to empty/None gracefully, M2) ---
    tagline: str                 # "" when unset
    deep_dive: str               # "" when unset
    demo_clip_url: str | None    # None when no clip
    demo_clip_alt: str           # "" when no clip
    facets: list[CatalogFacet]   # registry order; only facets with ≥1 value, [] when none
    developer: CatalogDeveloper
    other_apps: list[CatalogApp] # ACCEPTED-only, excludes this app, bounded; [] when solo app

def get_app_page_content(app_id) -> AppPageContent | None:
    """The single page read: an accepted app's full page content, or None if not accepted (D-6).
    Bounded query count: 1 app row (select_related owner; prefetch media/app_tags/app_facets)
    + tag resolution + 1 bounded query for other_apps. No N+1. Raises only on a genuine DB
    failure (never a fake-empty page that would hide an outage)."""

def accepted_apps_by_owner(owner_id, *, exclude, limit) -> list[CatalogApp]:
    """Up to `limit` OTHER accepted apps by this owner, newest-accepted-first (the identity-block
    'other apps'). Accepted-only (no pending/rejected/withdrawn leak); reuses _to_catalog_app."""
```

**Reuse:** `get_app_page_content` builds the base fields via the existing private `_to_catalog_app`
(no duplicated tag/media resolution) and adds the new parts — the shared `CatalogApp` contract stays
**byte-stable** (AC-9 safety; discovery/dashboard/widget untouched).

**Devlog inclusion tag (cross-app read):**
```python
# apps/updates/templatetags/updates_tags.py  (new; mirrors ratings_tags/subscriptions_tags)
{% app_devlog app %}  # reads updates.published_notices_for_apps([app.id],
                      #   limit=config.app_page_devlog_limit())  (default 5, newest-first)
                      # fail-soft: on any error renders nothing + APP_PAGE_DEVLOG_DEGRADED, never 500s
```

## 7. UX flow — the uniform slot contract (AC-7)

Every accepted app renders the **same ordered slots**; presence/order/richness is **never** a function
of identity (the read-model carries no such field). Each slot states its empty behaviour (M2):

| # | Slot | Source | Empty-state behaviour |
|---|---|---|---|
| 1 | **Hero**: name + **pitch line** + at-a-glance **fact strip** (category tags + facets) | `name`, `tagline`, `tags`, `facets` | name always present; tagline hidden when `""`; fact strip shows only set facets/tags |
| 2 | **Media gallery**: **demo clip** (first, `<video autoplay muted loop playsinline>` + `aria-label`) then screenshots | `demo_clip_url`/`demo_clip_alt`, `media` | clip omitted when None; existing screenshots empty-state retained |
| 3 | **Try it** (primary CTA, sidebar) | `url` via `pages:try` | unchanged (always present) |
| 4 | **About** (existing description) | `description` | always present (D-6) |
| 5 | **Deep dive** ("show more") — native `<details><summary>` (no-JS reachable, AC-4/C5) | `deep_dive` | entire slot omitted when `""` |
| 6 | **Developer hub**: "An app by **{display_name}**" + grid of **other apps** | `developer`, `other_apps` | name always shown; "other apps" omitted when solo |
| 7 | **Devlog** (read-only recent updates) | `{% app_devlog %}` | renders its own empty/degraded state, never 500s |
| 8 | **Follow** | `{% app_follow %}` (unchanged) | unchanged |
| 9 | **Share** | `pages:share` (unchanged) | unchanged |
| 10 | **Reviews** | `{% app_reviews %}` (unchanged) | unchanged |

- **No-JS source of truth (AC-4/C5/[D-13](../../DECISIONS.md)):** "show more" is native `<details>` —
  open/keyboard/screen-reader without any JS. Facet strip + identity grid are plain server-rendered
  markup. HTMX stays optional `hx-boost` only.
- **Accessibility (C5):** clip carries `aria-label`/`demo_clip_alt`; muted + no audio; `prefers-reduced-motion`
  honored via the existing design-system motion guard (the clip can render paused with a play control
  under reduced-motion — presentation detail for Stage 4).
- **Presentation only via the [D-13](../../DECISIONS.md) design system** — new component classes
  (e.g. `fact-strip`, `facet`, `media--clip`, `devlog`, `dev-hub`, `other-apps-grid`) are added to the
  one `core/app.css`; **no new build step, no per-type templates** (expandability to "any app with a
  URL" is by facet *values*, not by template — OQ brainstorm).

## 8. Interface contracts (write side — one source of truth)

`catalog.services` gains **optional** params (absent ⇒ unchanged; the `_UNSET` sentinel pattern):

```python
submit_app(owner, *, name, description, url, tag_ids, media,
           tagline="", deep_dive="", facet_values=None, demo_clip=None, demo_clip_alt="")
edit_app(app, *, name=_UNSET, ..., tagline=_UNSET, deep_dive=_UNSET,
         facet_values=_UNSET, demo_clip=_UNSET, demo_clip_alt=_UNSET)
```

- `facet_values` = an iterable of `(facet, value)` pairs; each validated by
  `facets.is_valid_facet_value` (off-vocabulary refused, nothing written — mirrors `_require_valid_tags`),
  cardinality enforced per `FacetDef`; replace-set semantics (like `_set_tags`).
- `demo_clip` validated by a new `_validate_clip` (container sniff + size cap), stored under a
  generated name by a `_store_clip` helper (mirrors `_store_media`); setting a clip requires
  `demo_clip_alt`.
- **Both authoring surfaces** are extended (no second source of truth): the server-rendered
  `SubmissionForm` (+ `submit.html`/`app_detail.html` fields, fed facet choices from `facets.FACETS`)
  **and** the DRF `AppCreateView`/`AppDetailView.patch` (`_supplied_edits` learns the new keys). The
  `AppSerializer` and `_form_initial` expose the new fields back for editing.

### 8.1 Re-review seam — **config-togglable** (APR-DESIGN-2 / the user's refinement)

`gate.GATE_RELEVANT_FIELDS` (a constant) becomes a function so the set can change without a migration:

```python
# apps/catalog/gate.py
_CORE_GATE_FIELDS = frozenset({"name", "description", "url", "tags", "media"})   # always gated
_TOGGLEABLE_GATE_FIELDS = ("tagline", "deep_dive", "facets", "demo_clip")        # default gated

def gate_relevant_fields() -> frozenset[str]:
    """The fields whose edit on an ACCEPTED app forces re-review. Core floor inputs are always
    gated; the new public-claim fields are gated by config (default on) so re-review policy can be
    tuned from observed deployment behaviour without a code change (APR-DESIGN-2/D-14)."""
    return _CORE_GATE_FIELDS | config.app_page_gated_fields()
```

`config.app_page_gated_fields() -> frozenset[str]` defaults to **all** of `_TOGGLEABLE_GATE_FIELDS`
(matches the user's "Yes" — honesty-first default) and is overridable (env/config) to relax any field.
`edit_app` calls `gate_relevant_fields()` instead of reading the constant; it records the changed
field key per new field (`"tagline"`, `"deep_dive"`, `"facets"`, `"demo_clip"`) so the existing
`_return_to_review_if_accepted` mechanism toggles correctly. **One source of truth** for the policy.

## 9. Non-functional handling

### 9.1 Performance
`get_app_page_content` is bounded (≤ ~4 queries, no N+1) via `select_related("owner")` +
`prefetch_related("media", "app_tags", "app_facets")` + one bounded `accepted_apps_by_owner` query.
The devlog tag is one `LIMIT`-bounded query, follower-count-independent (R3 already). Clip is a static
file (size-capped), served like an image.

### 9.2 Failure modes (per component)
| Component | Failure | Response |
|---|---|---|
| `get_app_page_content` (the page itself) | DB error | **loud 500** (uncaught) — never a fake-empty page (existing `pages/views` posture, §7) |
| same | non-accepted/unknown id | **404** `not_available.html` (unchanged) |
| `{% app_devlog %}` | `updates` read raises | **fail-soft**: render nothing + `APP_PAGE_DEVLOG_DEGRADED`; page stays 200 |
| `{% app_reviews %}` / `{% app_follow %}` | raises | fail-soft (unchanged) |
| facet display | stored value not in current registry | silently dropped at resolve (graceful, D-5 pattern) |
| demo clip | file missing/undecodable at serve | browser shows no video; optional slot → soft visual gap, not a page error |
| write: bad facet / oversized or non-AV clip | — | **loud** `InvalidFacetError`/`MediaLimitError` at the boundary, nothing written (atomic) |

### 9.3 Firewall / privacy (AC-6/C3/R4 — M5=0 preserved structurally)
The devlog is a **pure read** of `updates.published_notices_for_apps` (PII-free DTOs); `apps/updates`
imports nothing from `signals` (AST-enforced) and the inclusion tag adds **no** signal emission. Adding
the slot therefore cannot create a score-affecting event — M5=0 holds by construction, asserted in tests.

### 9.4 Security (threat model)
- **XSS:** `tagline`/`deep_dive`/`demo_clip_alt`/facet labels render through Django **auto-escaping**;
  nothing is marked `safe`; multiline `deep_dive` uses `linebreaksbr`/CSS `white-space`, never raw HTML.
- **Facets:** closed code enum, validated at the boundary → no injection, no client-coined values.
- **Clip upload:** size cap + container sniff + **generated filename** (never the client's), same
  discipline as images. Residual: we do not deep-validate codecs/transcode (the APR-D-1 deferral) —
  mitigated by the size cap, `muted`, and inline static serving; deeper validation/CSP is a future
  hardening (noted, §13).
- **No PII added:** identity block exposes `display_name` only (already public on reviews); "other
  apps" is **ACCEPTED-only** (never leaks a developer's pending/rejected/withdrawn apps).
- **Attributable:** all writes stay on the audited `catalog.services` path; no new endpoint that
  bypasses owner-scoping.

### 9.5 Observability / rollback
Reuse `APP_PAGE_RENDERED`; add **one** metric constant `APP_PAGE_DEVLOG_DEGRADED` (the devlog tag's
fail-soft signal). Post-deploy adoption (M4) / try-through (M5) ride the existing `app_page` D-7
impression — no new instrumentation needed now. Rollback in §10.

## 10. Rollout strategy

- **No feature flag.** The redesigned template replaces the old one; all new fields **degrade to
  graceful-empty** (M2), so legacy/sparsely-filled apps render correctly with no data step.
- **Order:** ship the additive migration (4 columns + `AppFacet` + indexes) → write path + facets.py +
  gate toggle → read (`AppPageContent`) → inclusion tag → template + CSS. (Stage 3 sequences tasks;
  risk-first = migration + read contract.)
- **Backward compatible:** `CatalogApp` and every existing consumer/contract are unchanged (AC-9);
  `submit_app`'s required floor is unchanged (new fields optional).
- **Rollback (DU-REL-1 pattern):** `git revert` the build commit + reverse the migration. The
  reverse migration drops the new columns/table — **the only loss is authored facet/marketing content**
  (acceptable and documented; no impact on the existing app lifecycle). This is the one
  partially-irreversible step, justified by the Feature-Track schema posture (C4) and called out here.

## 11. Alternatives considered (≥1 genuinely different per major call)

**(a) Facets — chosen: code-fixed structured fields (`AppFacet` + `facets.py`).**
- *Rejected — extend the D-5 taxonomy* (facets as clusters/tags reusing `AppTag`): mixes facets into
  the **category/interest tag pool** that already feeds `search_catalogue` and the interest matcher →
  couples facets to ranking/discovery (breaks AC-3's "informational only"), and a flat tag pool can't
  enforce "one pricing value per app" (illegal states become representable). *(User-ratified rejection.)*
- *Rejected — a JSON blob column* on `App`: not integrity-checkable, not indexable, illegal states
  representable, harder to validate — against §5.4 "make illegal states unrepresentable."
- *Sacrifice of the chosen design:* a migration + new write surface, and no facet-based discovery
  filtering in v1 (display-only — a deliberate, named future bet).

**(b) Read model — chosen: page-scoped `AppPageContent`, shared `CatalogApp` untouched.**
- *Rejected — add the new fields to the shared `CatalogApp`:* bloats a cross-feature contract for the
  benefit of one consumer (discovery/dashboard/widget would carry tagline/deep_dive/facets/clip they
  never use), and adds an owner join to every consumer's read. Page-scoped isolation keeps the contract
  byte-stable (AC-9) and the feature deletable. *Sacrifice:* a small flat-field duplication between
  `CatalogApp` and `AppPageContent` (mitigated by reusing `_to_catalog_app` for the base).

**(c) Demo media — chosen: one optional self-hosted muted-loop clip (MP4/WebM `FileField`).**
- *Rejected — animated GIF in `AppMedia`:* poor quality/huge bytes, and pollutes the image-only
  invariants of `AppMedia`. *Rejected — hosted video (YouTube/Vimeo embed or transcoding pipeline):*
  the [APR-D-1](DECISIONS.md) deferral (real infra: storage/transcode/bandwidth/embed-privacy).
  *Sacrifice:* single-node static serving of a capped clip (growth path = the D-12 object store);
  no codec transcoding (size cap + muted mitigate).

## 12. Tests (every AC mapped)

| AC | Verification |
|---|---|
| AC-1 (pitch) | render shows tagline above deep-dive + as `<meta name="description">`; empty tagline → page renders, no broken slot |
| AC-2 (demo clip) | clip renders as first peer with `muted`+`aria-label`/alt; screenshots still render; no hosted-video dep |
| AC-3 (facets) | facets render as a fact strip; **assert `AppFacet` is read by no ranking/discovery path** (import/usage test) — informational only |
| AC-4 (deep dive) | `<details>` deep-dive present + reachable **with JS disabled** (markup assertion, no `hx`/JS dependency) |
| AC-5 (identity) | identity block shows `display_name` + links to **other ACCEPTED apps only**; assert no email/PII; assert pending/rejected excluded |
| AC-6 (devlog) | devlog renders via `published_notices_for_apps`; **assert no `signals` import added** (M5=0); fail-soft test |
| AC-7 (uniformity) | **two apps with wildly different content render the identical slot set/order**; read-model has no tier/payment/identity field (structural) |
| AC-8 (feel) | human sign-off (PS-3 precedent) on web+mobile — out of automated scope |
| AC-9 (no regression) | full suite green; canonical URL, try-it `app_page` impression, share, follow, reviews still pass; `makemigrations --check` clean **except** the one deliberate additive migration; `CatalogApp` byte-stable |
| re-review toggle | editing each new field on an accepted app returns it to `pending` when its toggle is on, and **does not** when toggled off (config-driven) |

Edge cases: empty everything (legacy app), oversized/non-AV clip rejected loudly, off-vocabulary facet
rejected loudly, `SINGLE`-facet 2nd value rejected, facet value removed from registry dropped at read,
solo developer (no "other apps"), devlog read raising (fail-soft).

## 13. Self-critique

- *Re-review churn vs. hub feel.* Defaulting all marketing fields to gated is honesty-first but could
  frustrate iteration. **Resolved** by the user's refinement (APR-DESIGN-2): the gated set is a config
  toggle — relax per field once deployment shows churn is a real cost, no code change. Flagged to
  revisit on real usage.
- *Clip validation depth.* We sniff container + cap size but don't transcode/validate codecs. Accepted
  for v1 (APR-D-1 scope line); mitigations stated (§9.4); CSP/transcode is a named future hardening.
- *`AppPageContent` flat-field duplication.* Minor; chosen over fattening the shared contract (§11b),
  and mitigated by reusing `_to_catalog_app`.
- *Simplification pass.* Dropped: a developer avatar/bio (needs new `Account` fields — out of scope,
  identity block is name + other-apps only); structured deep-dive sub-sections (one rich text field is
  enough — no speculative structure, §5.5); facet-based discovery filtering (display-only in v1). No
  speculative abstraction remains — every new element ties to an AC.

## 14. Tech-stack decision & ADR

No new stack: this stays within [D-4](../../DECISIONS.md) (Django + Postgres, server-rendered) and
[D-13](../../DECISIONS.md) (build-free token CSS). Shared-code root unchanged (`apps/`).

Two design choices **outlive this feature** (a later feature would be wrong to contradict them) → one
global ADR **D-14** (to be written into [DECISIONS.md](../../DECISIONS.md) on approval), plus
feature-local **APR-DESIGN-1/2** in [DECISIONS.md](DECISIONS.md):

- **APR-DESIGN-1 / D-14a — typed facets are code-fixed structured fields, firewalled from ranking.**
  Facets live in `AppFacet` + a code declaration (`facets.py`), **separate from the D-5 tag pool**;
  they never enter `search_catalogue`, the interest matcher, or any score. Category/"genre" stays the
  existing taxonomy. *(Rejected: taxonomy-extension, JSON blob — §11a.)*
- **APR-DESIGN-2 / D-14b — re-review policy for public-claim fields is config-togglable.** Core floor
  inputs (name/description/url/tags/media) are always gate-relevant; the new public-claim fields
  (tagline/deep_dive/facets/demo_clip) are gated by config (default on), tunable from deployment
  behaviour without a code change. *(Rejected: a hardcoded set — too rigid for an unvalidated policy.)*

CODEMAP additions (recorded at Stage 4 on build): `catalog/facets.py`, `AppFacet`,
`get_app_page_content`/`AppPageContent`/`CatalogFacet`/`CatalogDeveloper`/`accepted_apps_by_owner`,
`gate.gate_relevant_fields()`, `{% app_devlog %}`, and the new `config`/metric constants.

## 15. Exit-criteria check
- Every AC (AC-1…AC-9 + the toggle) maps to ≥1 design element (§7/§12). ✔
- All interfaces fully specified — read DTOs/signatures (§6), write params (§8), facet registry (§5.3),
  template slot contract (§7). No "TBD". ✔
- Each component's failure behaviour documented (§9.2). ✔
- Honors [CLAUDE.md](../../CLAUDE.md) §5: scalable (bounded reads, code-fixed vocab), readable
  (one-job modules), partitioned (page-scoped read, deletable), fail-loud (page read), one source of
  truth (services/registry/gate), no speculative abstraction (§13). ✔
