#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/python-awesome-web}"
TS="$(date +%F_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/awesome_blog_${TS}.dump"

mkdir -p "${BACKUP_DIR}"
cd "${ROOT_DIR}"

docker compose exec -T postgres pg_dump -U awesome -d awesome_blog -Fc > "${OUT_FILE}"
echo "backup saved: ${OUT_FILE}"
