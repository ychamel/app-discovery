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

## Tests and linting

```bash
python manage.py test          # full test suite (needs PostgreSQL)
ruff check .                   # lint
```

A full deploy runbook (`.env` reference, first-admin bootstrap, token-purge schedule,
rollback) is at [docs/deploy-identity-accounts.md](docs/deploy-identity-accounts.md).
