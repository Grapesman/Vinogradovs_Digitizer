#!/bin/bash
set -Eeuo pipefail

cd "$(dirname "$0")"

mkdir -p data

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите Docker Desktop for Mac."
  read -r -p "Нажмите Enter для выхода..." _
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop установлен, но Docker Engine сейчас недоступен."
  echo "Запустите Docker Desktop и дождитесь статуса Engine running."
  read -r -p "Нажмите Enter для выхода..." _
  exit 1
fi

echo "Архитектура Mac: $(uname -m)"
echo "Сборка и запуск Vinogradov's Digitizer 2.3.0..."

docker compose up --build -d

echo
echo "Программа запущена: http://localhost:6080/"
echo "В окне открытия/сохранения доступны папки вашего Mac:"
echo "  Desktop, Documents, Downloads, Pictures и другие папки в $HOME"
echo "Папка ./data также остаётся доступной для тестов."
echo "Остановка: ./docker_stop_macos.command"

open "http://localhost:6080/" >/dev/null 2>&1 || true