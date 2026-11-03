# syntax=docker/dockerfile:1

# --------------------------------------------------------------------------- #
# 1. build the React frontend
# --------------------------------------------------------------------------- #
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --------------------------------------------------------------------------- #
# 2. Python runtime with gunicorn
# --------------------------------------------------------------------------- #
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    STORAGE_DIR=/data

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
# Flask serves the built app from ../frontend/dist, so keep that layout.
COPY --from=frontend-build /build/dist frontend/dist
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh && mkdir -p /data/data /data/uploads

EXPOSE 8080

# Seeds the demo feed once per volume, then execs gunicorn on $PORT.
CMD ["./entrypoint.sh"]
