# ---------- base: shared Python settings ----------
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---------- test: dev deps + tests; run with `docker run` to execute pytest ----------
FROM base AS test
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY app.py pytest.ini .flake8 ./
COPY tests ./tests
CMD ["pytest"]

# ---------- runtime: minimal, non-root image (default target) ----------
FROM base AS runtime
COPY requirements.txt ./
RUN pip install -r requirements.txt \
 && useradd --system --uid 10001 --no-create-home appuser \
 && mkdir /data && chown 10001:10001 /data
COPY app.py ./
ENV ACEEST_DB=/data/aceest_fitness.db PORT=5000
USER 10001
EXPOSE 5000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ['PORT'])"]
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 app:app"]
