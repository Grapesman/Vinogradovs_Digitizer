#!/usr/bin/env bash
set -Eeuo pipefail

export DISPLAY="${DISPLAY:-:99}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

export VINOGRADOVS_DATA_DIR="${VINOGRADOVS_DATA_DIR:-/data}"
export VINOGRADOVS_HOST_HOME="${VINOGRADOVS_HOST_HOME:-/host/home}"
export VINOGRADOVS_HOST_VOLUMES="${VINOGRADOVS_HOST_VOLUMES:-/host/volumes}"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-vinogradovs}"
export VNC_RESOLUTION="${VNC_RESOLUTION:-1600x860}"

mkdir -p "$VINOGRADOVS_DATA_DIR" "$XDG_RUNTIME_DIR"

chmod 700 "$XDG_RUNTIME_DIR" || true

# ------------------------------------------------------------
# Очистка старых X11-lock файлов
# ------------------------------------------------------------

DISPLAY_NUM="${DISPLAY#:}"
DISPLAY_NUM="${DISPLAY_NUM%%.*}"

rm -f \
    "/tmp/.X${DISPLAY_NUM}-lock" \
    "/tmp/.X11-unix/X${DISPLAY_NUM}" \
    2>/dev/null || true


# ------------------------------------------------------------
# Корректное завершение всех процессов контейнера
# ------------------------------------------------------------

cleanup() {
    kill \
        "${APP_PID:-}" \
        "${NOVNC_PID:-}" \
        "${VNC_PID:-}" \
        "${WM_PID:-}" \
        "${XVFB_PID:-}" \
        2>/dev/null || true
}

trap cleanup EXIT INT TERM


# ------------------------------------------------------------
# Виртуальный экран
# ------------------------------------------------------------

Xvfb \
    "$DISPLAY" \
    -screen 0 "${VNC_RESOLUTION}x24" \
    -ac \
    +extension GLX \
    +render \
    -noreset &

XVFB_PID=$!


# ------------------------------------------------------------
# Ждём запуска Xvfb
# ------------------------------------------------------------

for _ in $(seq 1 50); do

    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        break
    fi

    sleep 0.1

done


if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then

    echo "ERROR: Xvfb did not start on $DISPLAY" >&2

    exit 1

fi


# ------------------------------------------------------------
# Оконный менеджер
# ------------------------------------------------------------

fluxbox \
    >/tmp/fluxbox.log \
    2>&1 &

WM_PID=$!


# ------------------------------------------------------------
# VNC
# ------------------------------------------------------------

x11vnc \
    -display "$DISPLAY" \
    -forever \
    -shared \
    -nopw \
    -rfbport 5900 \
    -localhost \
    -xkb \
    -noxrecord \
    -noxfixes \
    -noxdamage \
    >/tmp/x11vnc.log \
    2>&1 &

VNC_PID=$!


# ------------------------------------------------------------
# noVNC
# ------------------------------------------------------------

websockify \
    --web=/usr/share/novnc/ \
    6080 \
    localhost:5900 \
    >/tmp/novnc.log \
    2>&1 &

NOVNC_PID=$!


# ------------------------------------------------------------
# Рабочая папка приложения
# ------------------------------------------------------------
#
# Раньше приложение запускалось из /data.
#
# Теперь, если домашняя папка пользователя Mac подключена
# через docker-compose, файловые диалоги смогут открываться
# из неё и видеть Desktop / Documents / Downloads и т.д.
#
# Если /host/home недоступна — используем /data.
# ------------------------------------------------------------

if [ -d "$VINOGRADOVS_HOST_HOME" ]; then

    cd "$VINOGRADOVS_HOST_HOME"

elif [ -d "$VINOGRADOVS_DATA_DIR" ]; then

    cd "$VINOGRADOVS_DATA_DIR"

else

    cd /app

fi


# ------------------------------------------------------------
# Запуск Vinogradov's Digitizer
# ------------------------------------------------------------

python /app/main.py &

APP_PID=$!


# ------------------------------------------------------------
# Если один из основных процессов завершился,
# контейнер тоже должен завершиться.
# ------------------------------------------------------------

set +e

wait -n \
    "$APP_PID" \
    "$NOVNC_PID" \
    "$VNC_PID" \
    "$XVFB_PID"

status=$?

set -e

exit "$status"