# Curated App Discovery Platform

Django + DRF + PostgreSQL. The first feature is **identity-accounts** (passwordless
magic-link identity with extensible role-based authorization). See
[features/identity-accounts/](features/identity-accounts/) for its brief, design, and tasks,
and [CLAUDE.md](CLAUDE.md) for how this repo is run.

## Run locally

Requires Python 3.12+ and PostgreSQL 15+.

```bash
# 1. Create a virtualenv and install dependencies
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure the environment
cp .env.example .env        # then edit DB_* and DJANGO_SECRET_KEY

# 3. Apply migrations and start the dev server
python manage.py migrate
python manage.py runserver
```

In development the console email backend prints magic-links to the terminal, so no
real mail provider is needed.

Bootstrap an admin (idempotent) and check service health:

```bash
python manage.py create_admin you@example.com
curl -fsS http://localhost:8000/health      # 200 when DB + email are reachable
```

## Interest taxonomy (`apps/taxonomy`)

The shared, curated interest vocabulary — **tags** grouped into **clusters** — that both
a user's interests and an app's subject matter are written in. Its UUID `Tag.id` is the
stable cross-feature reference (see [D-5](DECISIONS.md)).

```bash
python manage.py migrate taxonomy     # create tables (no content)
python manage.py seed_taxonomy        # apply apps/taxonomy/seed/vocabulary.yaml (idempotent)
python manage.py check_taxonomy       # integrity gate; non-zero exit on a violation
```

Edit the vocabulary in [apps/taxonomy/seed/vocabulary.yaml](apps/taxonomy/seed/vocabulary.yaml)
(or via the `is_staff`-gated Django admin) and re-run `seed_taxonomy`; it upserts by `slug`
and never deletes a tag that drops out of the file (retiring is the explicit `retired:` flag).
Read the vocabulary over HTTP (authenticated session):

```
GET /taxonomy/tags          # active tags with their clusters
GET /taxonomy/tags/{id}     # one tag of any status (renders retired/remapped references)
GET /taxonomy/clusters      # clusters with their active tags
```

In-process consumers read through `apps.taxonomy.selectors` — `is_valid_tag(id)` at their
write boundary and `resolve_tag(id)` at read (the D-5 contract).

## App catalog (`apps/catalog`)

A developer's self-serve way to submit a web app, run it through an **objective** intake
gate (five fixed floors — works / not spam / not duplicate / honest metadata / basic
policy; **never taste**, [D-6](DECISIONS.md)), and produce an owned, correctly-tagged,
**accepted** app the rest of the platform reads.

```bash
pip install -e ".[dev]"               # brings in Pillow (image validation)
python manage.py migrate catalog      # create the four tables (no content)
```

Uploaded screenshots are written under `MEDIA_ROOT` (defaults to `./media`; serve via a
web server / object store in production). Per-app media limits are typed tunables
(`CATALOG_MEDIA_MAX_COUNT`, default 8; `CATALOG_MEDIA_MAX_BYTES`, default 5 MB) — **the
published media contract `app-pages` must adopt: 1–8 images, PNG/JPEG/WebP, ≤5 MB each.**

Human flows (server-rendered, role-gated):

```
GET/POST /catalog/submit          # developer: submit an app
GET      /catalog/apps            # developer: my apps + status + rejection reasons
GET/POST /catalog/apps/{id}       # developer: edit / withdraw / resubmit / media
GET      /catalog/review          # admin: FIFO review queue + duplicate hint
GET/POST /catalog/review/{id}     # admin: five-floor checklist → accept / reject
```

JSON API (session + role): developer endpoints under `/catalog/api/apps…` (create, mine,
detail, patch, media, withdraw, resubmit); review under `/catalog/api/review/queue` and
`/catalog/api/apps/{id}/decision`.

**Reading the catalog downstream:** consumers store **only `App.id`** and read through
`apps.catalog.selectors.list_catalogued_apps` / `get_catalogued_app`, which return
**accepted apps only**, with tags resolved via `resolve_tag` and media in stable order
(the [D-6](DECISIONS.md) contract — adopt it before storing any app reference). Never read
`catalog_app` directly past this surface.

Rollback: `python manage.py migrate catalog zero` drops the four tables (the shared
`citext` extension is retained); clear `MEDIA_ROOT` if you also want the uploaded files
removed.

## Tests and linting

```bash
python manage.py test          # full test suite (needs PostgreSQL)
ruff check .                   # lint
```

A full deploy runbook (`.env` reference, first-admin bootstrap, token-purge schedule,
rollback) is at [docs/deploy-identity-accounts.md](docs/deploy-identity-accounts.md).
