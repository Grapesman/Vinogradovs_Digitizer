# Исправление Xvfb в Docker (2.3.0)

Версия 2.3.0 исправляет повторный запуск контейнера после остановки/сбоя.

Что исправлено:
- `/tmp/.X11-unix` создаётся от root с правами `1777`;
- перед запуском Xvfb удаляются устаревшие `/tmp/.X99-lock` и `/tmp/.X11-unix/X99`;
- ошибка `Server is already active for display 99` больше не должна приводить к циклическому перезапуску.

## Запуск

```bash
docker compose down --remove-orphans
docker compose up --build -d
```

Если Docker Hub временно недоступен, а образ уже был собран ранее:

```bash
docker compose up -d
```
