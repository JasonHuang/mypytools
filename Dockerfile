FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UPLOAD_FOLDER=/app/uploads

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY web_gui.py wsgi.py gunicorn.conf.py ./
COPY toolmist ./toolmist
COPY templates ./templates
COPY static ./static

RUN mkdir -p /app/uploads \
    && chown -R app:app /app

USER app

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/healthz', timeout=3)"]

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
