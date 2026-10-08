# AI Security Storyline Labs -- production image (gunicorn, non-root, one worker by design).
# Build:  docker build -t labdemo .
# Run behind an HTTPS proxy; see docker-compose.yml and DEPLOYMENT.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so code-only changes reuse the cached layer.
COPY requirements.txt requirements.lock requirements-prod.txt ./
RUN pip install -r requirements-prod.txt

# Unprivileged user; the instance dir (SQLite progress + secret key) is the only writable path.
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin labdemo \
 && mkdir -p /app/instance && chown labdemo:labdemo /app/instance
COPY --chown=labdemo:labdemo . .
USER labdemo

# The container listens on all interfaces *inside its network namespace*; publish it only to the proxy.
ENV LABDEMO_BIND=0.0.0.0:8000 \
    LABDEMO_INSTANCE=/app/instance
EXPOSE 8000
VOLUME ["/app/instance"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "scripts/healthcheck.py"]

# workers=1 is deliberate (in-process sandbox cache + rate limiter); see gunicorn.conf.py.
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
