# ==========================================
# Stage 1: Установка зависимостей
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ==========================================
# Stage 2: Production образ
# ==========================================
FROM python:3.12-slim AS production

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

# Копируем установленные пакеты из builder
COPY --from=builder /install /usr/local

# Создаем non-root пользователя
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/data /app/backups && \
    chown -R appuser:appuser /app

# Копируем исходный код
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Инициализация БД вынесена в CMD перед запуском uvicorn
CMD ["sh", "-c", "python -m app.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
