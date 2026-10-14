FROM python:3.12-slim-bookworm


# ============================================================
# БАЗОВЫЕ ПЕРЕМЕННЫЕ
# ============================================================

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUTF8=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DISPLAY=:99 \
    QT_QPA_PLATFORM=xcb \
    QT_X11_NO_MITSHM=1 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    VINOGRADOVS_DATA_DIR=/data \
    VINOGRADOVS_HOST_HOME=/host/home \
    VINOGRADOVS_HOST_VOLUMES=/host/volumes \
    XDG_RUNTIME_DIR=/tmp/runtime-vinogradovs


# ============================================================
# СИСТЕМНЫЕ ЗАВИСИМОСТИ
# ============================================================

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb \
        x11vnc \
        x11-utils \
        fluxbox \
        novnc \
        websockify \
        fonts-dejavu-core \
        fonts-liberation \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libgl1 \
        libopengl0 \
        libice6 \
        libsm6 \
        libx11-6 \
        libx11-xcb1 \
        libxext6 \
        libxi6 \
        libxkbcommon-x11-0 \
        libxrender1 \
        libxtst6 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxcb-util1 \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# РАБОЧАЯ ПАПКА
# ============================================================

WORKDIR /app


# ============================================================
# PYTHON-ЗАВИСИМОСТИ
# ============================================================

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        -r /app/requirements.txt


# ============================================================
# КОД ПРОЕКТА
# ============================================================

COPY . /app


# ============================================================
# БРАУЗЕРНАЯ ОБОЛОЧКА noVNC
# ============================================================

RUN cp \
        /app/docker-novnc-index.html \
        /usr/share/novnc/index.html \
    && cp \
        /app/assets/app_icon.png \
        /usr/share/novnc/vinogradovs-icon.png


# ============================================================
# НЕПРИВИЛЕГИРОВАННЫЙ ПОЛЬЗОВАТЕЛЬ
# ============================================================

RUN useradd \
        --create-home \
        --uid 1000 \
        digitizer \
    && mkdir -p \
        /data \
        /host/home \
        /host/volumes \
        /tmp/runtime-vinogradovs \
        /tmp/.X11-unix \
    && chown -R \
        digitizer:digitizer \
        /data \
        /app \
        /tmp/runtime-vinogradovs \
    && chown \
        root:root \
        /tmp/.X11-unix \
    && chmod \
        1777 \
        /tmp/.X11-unix \
    && chmod \
        700 \
        /tmp/runtime-vinogradovs \
    && chmod +x \
        /app/docker-entrypoint.sh \
        /app/docker_smoke_test.sh \
        /app/docker_start_macos.command \
        /app/docker_stop_macos.command


# ============================================================
# ЗАПУСК ОТ ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ
# ============================================================

USER digitizer


# ============================================================
# ПОРТ noVNC
# ============================================================

EXPOSE 6080


# ============================================================
# СЛУЖЕБНАЯ ПАПКА
# ============================================================

VOLUME ["/data"]


# ============================================================
# ПРОВЕРКА РАБОТОСПОСОБНОСТИ
# ============================================================

HEALTHCHECK \
    --interval=30s \
    --timeout=3s \
    --start-period=20s \
    --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6080/', timeout=2).read(1)" \
        || exit 1


# ============================================================
# ТОЧКА ВХОДА
# ============================================================

ENTRYPOINT ["/app/docker-entrypoint.sh"]