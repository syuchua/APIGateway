# syntax=docker/dockerfile:1.6

## ------------------------------------------------------------
## Frontend builder stage: build Next.js app
## ------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /app/front

COPY front/package.json front/package-lock.json ./
RUN npm ci --omit=dev

# Copy remaining frontend source and build
COPY front/. .
RUN npm run build

## ------------------------------------------------------------
## Backend builder stage: install Python dependencies into venv
## ------------------------------------------------------------
FROM python:3.12-slim AS backend-builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./

RUN python -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --upgrade pip setuptools wheel \
 && pip install uv

COPY backend/. .
RUN . /opt/venv/bin/activate \
 && pip install --no-cache-dir .

## ------------------------------------------------------------
## Runtime stage: serve Backend (FastAPI) + Frontend (Next.js)
## ------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    NEXT_PUBLIC_API_URL="/api"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 nodejs npm \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend runtime
COPY --from=backend-builder /opt/venv /opt/venv
COPY backend/. ./backend

# Frontend runtime (use production build from builder)
COPY --from=frontend-builder /app/front/.next ./front/.next
COPY --from=frontend-builder /app/front/public ./front/public
COPY --from=frontend-builder /app/front/package.json /app/front/package-lock.json ./front/

# Install runtime deps for Next.js
WORKDIR /app/front
RUN npm ci --omit=dev

WORKDIR /app

EXPOSE 8000 3000

CMD [ "/bin/sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & cd front && npm run start -- --hostname 0.0.0.0 --port 3000" ]
