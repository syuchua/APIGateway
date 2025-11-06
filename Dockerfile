## ------------------------------------------------------------
## Frontend builder stage: build Next.js app
## ------------------------------------------------------------
FROM node:22-alpine AS frontend-builder

ARG NPM_REGISTRY=https://registry.npmjs.org

WORKDIR /app/front

COPY front/package.json front/package-lock.json ./
RUN npm set registry $NPM_REGISTRY \
 && npm ci --omit=dev

# Copy remaining frontend source and build
COPY front/. .
RUN npm run build

## ------------------------------------------------------------
## Backend builder stage: install Python dependencies into venv
## ------------------------------------------------------------
FROM python:3.12-alpine AS backend-builder

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=$PIP_INDEX_URL

RUN sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories \
 && apk add --no-cache \
    build-base \
    postgresql-dev \
    musl-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./

RUN python -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --upgrade pip setuptools wheel

COPY backend/. .
RUN . /opt/venv/bin/activate \
 && pip install --no-cache-dir .

## ------------------------------------------------------------
## Runtime stage: serve Backend (FastAPI) + Frontend (Next.js)
## ------------------------------------------------------------
FROM python:3.12-alpine AS runtime

ARG NPM_REGISTRY=https://registry.npmjs.org
ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    NEXT_PUBLIC_API_URL="/api" \
    DATABASE_URL="postgresql://gateway_user:gateway_pass_2025@postgres:5432/apigateway" \
    REDIS_HOST="redis" \
    REDIS_PORT="6379" \
    REDIS_PASSWORD="redis_pass_2025" \
    REDIS_DB="0"

RUN sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories \
 && apk add --no-cache \
    libstdc++ \
    postgresql-libs \
    nodejs \
    npm

WORKDIR /app

# Backend runtime
COPY --from=backend-builder /opt/venv /opt/venv
COPY backend/. ./backend
COPY backend/.env.docker /app/.env

# Frontend runtime (use production build from builder)
COPY --from=frontend-builder /app/front/.next ./front/.next
COPY --from=frontend-builder /app/front/public ./front/public
COPY --from=frontend-builder /app/front/package.json /app/front/package-lock.json ./front/

# Install runtime deps for Next.js
WORKDIR /app/front
RUN npm set registry $NPM_REGISTRY \
 && npm ci --omit=dev

WORKDIR /app

EXPOSE 8000 3000

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]

