#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/awesome_blog_xxx.dump"
  exit 1
fi

DUMP_FILE="$1"
if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "dump file not found: ${DUMP_FILE}"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

cat "${DUMP_FILE}" | docker compose exec -T postgres pg_restore -U awesome -d awesome_blog --clean --if-exists --no-owner --no-privileges
echo "restore completed: ${DUMP_FILE}"
