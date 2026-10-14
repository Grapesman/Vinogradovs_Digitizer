#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")"
mkdir -p data

docker compose -f docker-compose.yml -f docker-compose.amd64.yml up --build -d
open "http://localhost:6080/" >/dev/null 2>&1 || true

echo "Vinogradovs Digitizer запущен через linux/amd64: http://localhost:6080/"
