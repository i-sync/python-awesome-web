# python-awesome-web

A lightweight blog app on `aiohttp` + PostgreSQL, organized under the `app/` package.

## Runtime Overview
- App container: `python-awesome-web-app`
- DB container: `postgres:16-alpine`
- App URL: `http://127.0.0.1:9000/`
- PostgreSQL host port: `55432` -> container `5432`

## Project Layout
- `app/main.py`: application bootstrap, middlewares, route registration.
- `app/handlers/`: route handlers split by domain (`public.py`, `manage.py`, `api.py`).
- `app/db/orm.py`: SQLAlchemy async compatibility ORM.
- `app/db/models.py`: model definitions.
- `app/services/`: shared business helpers.
- `app/templates/`, `app/static/`, `app/config/`: templates, frontend assets, and runtime config.
- `scripts/generate_sitemap.py`: regenerate `sitemap.xml`.
- `conf/database.postgresql.sql`: schema bootstrap SQL.
- `ops/`: backup/restore/health-check scripts.

## Daily Commands
Start services:
```bash
docker compose up -d postgres app
```

Check status:
```bash
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 postgres
```

Local run (venv):
```bash
python3 -m app.main
```

Regenerate sitemap:
```bash
python3 scripts/generate_sitemap.py
```

Slow network build:
```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple docker compose build --no-cache app
```

## PostgreSQL Backup / Restore
Use provided scripts:
```bash
./ops/backup.sh
./ops/restore.sh /var/backups/python-awesome-web/awesome_blog_<TS>.dump
```

Manual equivalents:
```bash
docker compose exec -T postgres pg_dump -U awesome -d awesome_blog -Fc > backups/awesome_blog_$(date +%F_%H%M%S).dump
cat backups/awesome_blog_<TS>.dump | docker compose exec -T postgres pg_restore -U awesome -d awesome_blog --clean --if-exists --no-owner --no-privileges
```

## Weekly Backup (crontab)
```bash
0 4 * * 0 cd /var/www/python-awesome-web && ./ops/backup.sh >> /var/log/python-awesome-web-backup.log 2>&1
30 4 * * 0 find /var/backups/python-awesome-web -name '*.dump' -mtime +90 -delete
```

## New Server Migration (PostgreSQL -> PostgreSQL)
1. On old server: run `./ops/backup.sh`.
2. Copy code + dump to new server.
3. Start DB: `docker compose up -d postgres`.
4. Restore dump with `./ops/restore.sh <dump_file>`.
5. Start app: `docker compose up -d --build app`.
6. Verify: `./ops/healthcheck.sh http://127.0.0.1:9000/`.

## Legacy Note
Legacy MySQL migration tooling was removed after cutover. Keep old MySQL dumps offline for archival recovery only.
