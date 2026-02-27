# Production Cutover Checklist

## 1. Pre-check
- Ensure latest backup exists (`./ops/backup.sh`).
- Confirm PostgreSQL container healthy.
- Build app image on target host.

## 2. Deploy
```bash
docker compose up -d --build app
```

## 3. Verify
```bash
./ops/healthcheck.sh http://127.0.0.1:9000/
docker compose logs --tail=120 app
```

## 4. Rollback
If app fails after deployment:
1. Re-deploy previous app image tag.
2. If data incompatibility occurred, restore pre-cutover dump with `./ops/restore.sh <dump_file>`.
3. Re-run health check.
