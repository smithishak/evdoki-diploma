FROM python:3.12-slim

WORKDIR /app

# Сначала зависимости — кэшируется отдельным слоем.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Файл БД по умолчанию — в томе /data (см. README).
ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/helpdesk.db
VOLUME ["/data"]

CMD ["python", "-m", "app.main"]
