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

## Tests and linting

```bash
python manage.py test          # full test suite (needs PostgreSQL)
ruff check .                   # lint
```

A full deploy runbook (`.env` reference, first-admin bootstrap, token-purge schedule,
rollback) is at [docs/deploy-identity-accounts.md](docs/deploy-identity-accounts.md).
