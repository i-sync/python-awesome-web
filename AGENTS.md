# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `www/`.
- `www/app.py`: aiohttp app bootstrap, middleware, and server startup (port `9000`).
- `www/handlers.py`: route handlers and page/API behavior.
- `www/coreweb.py`: custom `@get`/`@post` decorators and route registration.
- `www/models.py` + `www/orm.py`: data models and async ORM layer.
- `www/templates/` and `www/static/`: Jinja2 templates and frontend assets.
- `www/config/`: runtime JSON config (`config.json` base + `user.json` overrides).

Support files:
- `conf/database.postgresql.sql`: PostgreSQL schema initialization.
- `docker-compose.yml` + `Dockerfile`: containerized deployment.
- `log/`: runtime log directory placeholder.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate`: create local virtualenv.
- `pip install -r requirements.txt`: install runtime dependencies.
- `python3 www/app.py`: run the app locally at `http://127.0.0.1:9000`.
- `python3 www/pymonitor.py www/app.py`: run with auto-restart on `.py`/`.json` changes.
- `python3 www/generate_sitemap.py`: regenerate `sitemap.xml` from enabled blogs.
- `docker compose up -d postgres app`: run full stack with PostgreSQL.
- `docker compose logs --tail=100 app`: check runtime errors quickly.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation and UTF-8 files. Follow existing patterns:
- `snake_case` for modules/functions/variables.
- `PascalCase` for model and exception classes.
- Lowercase template names with underscores (for example, `manage_blog_edit.html`).
- Keep async handlers explicit and decorator-driven (`@get`, `@post`).

No formatter/linter is enforced in-repo; keep edits small, consistent, and PEP 8-aligned where practical.

## Testing Guidelines
There is currently no automated test suite or coverage gate in this repository. For each change:
- Run the app locally and smoke-test affected routes/pages.
- Validate DB-impacting changes against `conf/database.postgresql.sql`.
- Include manual verification steps in your PR.

If adding automated tests, place them under a new `tests/` directory and use `test_*.py` naming.

## Commit & Pull Request Guidelines
Recent commits use short, imperative messages (examples: `update robots.`, `fixed blog tags issue.`). Prefer:
- One-line subject in imperative mood, scoped to the change.
- Optional body for context when behavior, config, or schema changes.

PRs should include:
- What changed and why.
- Any config/database impact.
- Manual test evidence (and screenshots for template/static UI changes).
- Linked issue/task when available.

## Security & Configuration Tips
Treat `www/config/user.json` as environment-specific. Do not commit real credentials, cookie secrets, or production-only values. Keep local overrides minimal and review config diffs carefully.

## Operations Notes
- Standard data workflow is PostgreSQL backup/restore (`pg_dump`/`pg_restore` via `docker compose exec`).
- Prefer weekly cron backup with retention cleanup (see README).
- Keep backup dumps outside the repo (`/var/backups/python-awesome-web`).
