# Repository Guidelines

## Project Structure & Module Organization
Primary code now lives in `app/`:
- `app/main.py`: aiohttp app bootstrap and lifecycle hooks.
- `app/handlers/`: route modules split by concern:
  - `public.py`: site pages and public endpoints.
  - `manage.py`: admin page routes.
  - `api.py`: JSON API endpoints.
  - `common.py`: shared auth/cookie/paging helpers.
- `app/db/orm.py` + `app/db/models.py`: SQLAlchemy async compatibility ORM and models.
- `app/services/`: reusable logic (for example markdown rendering and sitemap caching).
- `app/templates/`, `app/static/`, `app/config/`: templates, frontend assets, and runtime config.
- `scripts/`: operational developer scripts (`generate_sitemap.py`, `pymonitor.py`).

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate`: create local virtualenv.
- `pip install -r requirements.txt`: install runtime deps.
- `python3 -m app.main`: run app locally on `9000`.
- `curl -s http://127.0.0.1:9000/sitemap.xml`: check live sitemap endpoint.
- `python3 scripts/generate_sitemap.py`: optional offline sitemap export.
- `python3 scripts/pymonitor.py -m app.main`: optional auto-restart runner.
- `docker compose up -d postgres app`: run full stack.
- `docker compose logs --tail=100 app`: inspect runtime errors.

## Coding Style & Naming Conventions
Use Python 3, UTF-8, and 4-space indentation.
- `snake_case`: module/function/variable names.
- `PascalCase`: model and exception classes.
- Keep handlers async and decorator-based (`@get`, `@post`).
- Keep template filenames lowercase with underscores.

No enforced formatter/linter in repo; keep edits small and PEP 8-aligned.

## Testing Guidelines
Automated tests are in early stage under `tests/`.
- Name tests as `test_*.py`.
- Run unit checks with `pytest` when available.
- Always smoke-test key flows (`/`, `/blog/{id}`, `/signin`, admin pages) after DB or handler changes.

## Commit & Pull Request Guidelines
Prefer short imperative commits (for example, `split handlers into modules`).
PRs should include:
- change summary and reason,
- config/schema/ops impact,
- verification evidence (commands run, screenshots for UI changes),
- linked issue/task if applicable.

## Security & Operations Notes
Do not commit real secrets in `app/config/user.json`. Use env vars (`DATABASE_DSN`, `DB_*`, `PG*`) for deployment overrides.
Use `ops/backup.sh`, `ops/restore.sh`, and weekly cron retention for PostgreSQL operations.
