# lineage: frontend built with Node, served by a single FastAPI/uvicorn process.

# ---- stage 1: build the frontend -------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: backend + built frontend ---------------------------------------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    FRONTEND_DIR=/app/frontend/dist \
    LINEAGE_EXAMPLES=/app/examples
WORKDIR /app
COPY backend/ /app/backend/
RUN pip install --no-cache-dir /app/backend
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# The example data: the showcase accounts (demo, lineage) start from copies of it.
COPY examples/papers /app/examples/papers
COPY examples/lineage /app/examples/lineage
EXPOSE 8000
# One worker: writes are serialised by a lock inside the process.
CMD ["uvicorn", "--factory", "backend.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
