# python-awesome-web

Lightweight blog app running on Python 3.11 + aiohttp 3.9 + PostgreSQL.

## Runtime Overview
- App container: `python-awesome-web-app`
- DB container: `postgres:16-alpine`
- App URL: `http://127.0.0.1:9000/`
- PostgreSQL host port: `55432` (mapped to container `5432`)

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

Build with slow network mirror:
```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple docker compose build --no-cache app
```

## Deploy to a New Server (PostgreSQL -> PostgreSQL)
Use this when moving to a new machine.

1. On old server, export dump:
```bash
mkdir -p /var/backups/python-awesome-web
TS=$(date +%F_%H%M%S)
docker compose exec -T postgres pg_dump -U awesome -d awesome_blog -Fc \
  > /var/backups/python-awesome-web/awesome_blog_${TS}.dump
```

2. Copy code + dump to new server.

3. On new server, start PostgreSQL:
```bash
docker compose up -d postgres
```

4. Restore data:
```bash
cat /var/backups/python-awesome-web/awesome_blog_<TS>.dump | \
docker compose exec -T postgres pg_restore -U awesome -d awesome_blog \
  --clean --if-exists --no-owner --no-privileges
```

5. Start app:
```bash
docker compose up -d --build app
```

6. Verify:
```bash
curl --noproxy '*' -I http://127.0.0.1:9000/
```

## PostgreSQL Backup and Restore
One-off backup:
```bash
docker compose exec -T postgres pg_dump -U awesome -d awesome_blog -Fc > backups/awesome_blog_$(date +%F_%H%M%S).dump
```

Restore from dump:
```bash
cat backups/awesome_blog_<TS>.dump | docker compose exec -T postgres pg_restore -U awesome -d awesome_blog --clean --if-exists --no-owner --no-privileges
```

## Weekly Scheduled Backup (crontab)
Create backup directory:
```bash
mkdir -p /var/backups/python-awesome-web
```

Open crontab:
```bash
crontab -e
```

Add weekly backup at Sunday 03:00:
```bash
0 4 * * 0 cd /var/www/python-awesome-web && docker compose exec -T postgres pg_dump -U awesome -d awesome_blog -Fc > /var/backups/python-awesome-web/awesome_blog_$(date +\%F_\%H\%M).dump 2>>/var/log/python-awesome-web-backup.log
```

Optional retention (delete backups older than 90 days):
```bash
30 4 * * 0 find /var/backups/python-awesome-web -name '*.dump' -mtime +90 -delete
```

## Legacy Note
MySQL migration tooling has been removed from this repo after cutover. Keep old MySQL dump files offline for archival recovery only.
