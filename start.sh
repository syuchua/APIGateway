#!/bin/sh
/opt/venv/bin/python -m alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
cd front && npm run start -- --hostname 0.0.0.0 --port 3000
