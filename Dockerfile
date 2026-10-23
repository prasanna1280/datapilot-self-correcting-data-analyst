# DataPilot app: Streamlit UI + AutoGen agent team (no AI code runs in here in production;
# it is sent to the separate sandbox container).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RUNTIME_DIR=/data/runtime \
    DB_PATH=/data/db/datapilot.db \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --uid 1000 --create-home appuser \
 && mkdir -p /data/runtime/sessions /data/db \
 && chown -R appuser:appuser /data
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"
CMD ["streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
