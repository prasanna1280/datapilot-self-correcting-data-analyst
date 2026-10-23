# DataPilot code sandbox: runs AI-written Python with no secrets and no internet.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    SANDBOX_WORKSPACE=/data/runtime/sessions

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt \
 && useradd --uid 1000 --no-create-home sandbox \
 && mkdir -p /data/runtime/sessions && chown -R sandbox:sandbox /data

COPY server.py /srv/server.py
USER sandbox
EXPOSE 8800
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8800/health')"
CMD ["python", "/srv/server.py"]
