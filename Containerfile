FROM registry.access.redhat.com/ubi9/python-312:latest

WORKDIR /app

USER 0
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN mkdir -p /app/data && chown -R 1001:0 /app/data
USER 1001

ENV PORT=5003
ENV HOST=0.0.0.0
ENV DATABASE_PATH=/app/data/hub.db

EXPOSE 5003

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:5003/health || exit 1

ENTRYPOINT ["python3", "-m", "app.main"]
