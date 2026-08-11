# ── Stage 1: install Python dependencies into a virtualenv ──
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: lean runtime image ──
FROM python:3.12-slim AS runtime

WORKDIR /app

# fastembed (ONNX) runtime dependency only — no build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/ ./backend/
COPY data/ ./data/

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    EMBEDDING_PROVIDER=fastembed

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
