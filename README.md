# python-awesome-web

Legacy blog upgraded to Python 3.11 + aiohttp 3.9 + PostgreSQL.

## 1) Dependencies (important)
- `requirements.txt`: app runtime only (used by Docker image).
- `requirements-migrate.txt`: migration tools (`aiomysql`) + runtime deps.

So:
- `aiomysql` is **not needed** for app runtime.
- `aiomysql` is **only needed** when running MySQL -> PostgreSQL migration script.

## 2) Version pinning
- `aiohttp` kept as range: `>=3.9,<3.10` (stable minor line, allows patch updates).
- If you need strict reproducibility, you can pin to `3.9.5`.

## 3) Build with slow network
Use mirror when building Docker:

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple docker compose build --no-cache app
```

Dockerfile already enables retry + timeout:
- `--retries 20`
- `--timeout 180`
- `--prefer-binary`

## 4) Start PostgreSQL in Docker
```bash
docker compose up -d postgres
```

Check:
```bash
docker compose ps
docker compose logs -f postgres
```

Default host mapping is `55432 -> container 5432` to avoid conflict with local PostgreSQL on `5432`.

## 5) Migrate host MySQL -> Docker PostgreSQL
Assume:
- MySQL runs on host `127.0.0.1:3306`
- PostgreSQL runs in Docker and maps to host `127.0.0.1:5432`

Run migration on host (recommended):

```bash
source venv/bin/activate
pip install -r requirements-migrate.txt

python scripts/migrate_mysql_to_postgres.py \
  --mysql-host 127.0.0.1 \
  --mysql-port 3306 \
  --mysql-user root \
  --mysql-password '<MYSQL_PASSWORD>' \
  --mysql-database awesome_blog \
  --pg-dsn 'postgresql://awesome:awesome@127.0.0.1:55432/awesome_blog'
```

## 6) Run app
Docker:
```bash
docker compose up -d app
```

Local:
```bash
export DATABASE_DSN='postgresql://<user>:<password>@127.0.0.1:5432/<db>'
python www/app.py
```

## 7) Notes
- If your local PostgreSQL password is not `awesome`, update `DATABASE_DSN` or `www/config/user.json`.
- New PostgreSQL schema: `conf/database.postgresql.sql`.
- Old MySQL schema remains in `conf/database.sql` for reference.
