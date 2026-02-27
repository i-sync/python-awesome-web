#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:9000/}"
STATUS="$(curl -s -o /tmp/python-awesome-web-health.html -w "%{http_code}" "${URL}")"

if [[ "${STATUS}" != "200" ]]; then
  echo "health check failed: ${URL} -> ${STATUS}"
  exit 1
fi

echo "health check passed: ${URL} -> ${STATUS}"
