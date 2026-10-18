FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.11.26

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY app ./app
RUN uv sync --frozen --no-dev --extra api --extra groq --extra dense && \
    rm -rf /tmp/uv-cache

RUN mkdir -p /app/data/models && chmod 1777 /app/data/models
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001:10001

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "constitution_evidence.api:app", "--host", "0.0.0.0", "--port", "8000"]
