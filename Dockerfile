ARG PYTHON_BASE=python:3.11-slim-bookworm
FROM ${PYTHON_BASE} AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock.txt .
RUN python -m pip install --no-cache-dir -r requirements.lock.txt \
    && python -m pip check

FROM dependencies AS backend
COPY backend/ backend/
COPY tests/ tests/
COPY artifacts/serving/ artifacts/serving/
ENV SERVING_DIR=/app/artifacts/serving
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM dependencies AS frontend
COPY frontend/ frontend/
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "frontend/app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true", "--browser.gatherUsageStats", "false", "--server.maxUploadSize", "1"]
