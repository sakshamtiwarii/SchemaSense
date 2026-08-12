FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docker ./docker

EXPOSE 8000

# Shell form (not exec-array form) so $PORT actually expands — Railway
# assigns a dynamic port at runtime via this env var; local docker-compose
# doesn't set it, so it falls back to 8000 same as before.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
