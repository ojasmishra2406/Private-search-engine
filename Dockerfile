# Build environment
FROM python:3.12-slim as backend-builder

WORKDIR /app
# Install system build dependencies (required for compiling C-extensions on ARM64)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    swig \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Final environment
FROM python:3.12-slim

WORKDIR /app
# Install runtime dependencies for FAISS and ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY --from=backend-builder /app /app

ENV PYTHONPATH=/app
ENV APP_ENV=production

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
