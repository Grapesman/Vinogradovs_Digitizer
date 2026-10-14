#!/bin/bash
set -Eeuo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден."
  read -r -p "Нажмите Enter для выхода..." _
  exit 1
fi

echo "Остановка Vinogradov's Digitizer..."

docker compose down

echo
echo "Vinogradov's Digitizer остановлен."