FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime (least privilege); owns workdir plus /data (the shared
# sqlite volume mount point from compose: sqlite:////data/geo_sentinel.db).
# Without this, the named volume arrives root-owned and appuser gets
# "sqlite3.OperationalError: unable to open database file" (backend crash-loop
# + silent worker rollbacks — reproduced 2026-09-18).
RUN useradd -m -u 10001 appuser \
 && mkdir -p /app/media /app/models /data \
 && chown -R appuser:appuser /app /data
USER appuser

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"

# Migrations run before serving so Postgres/prod deploys never boot on an
# empty schema (migration-lite: create_all + seed; see scripts/migrate.py).
CMD ["sh", "-c", "python scripts/migrate.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
