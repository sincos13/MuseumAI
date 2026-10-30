FROM ghcr.io/astral-sh/uv:0.9.7 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend PATH=/app/.venv/bin:$PATH
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
COPY scripts ./scripts
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 museai && mkdir -p var/exhibit-images var/museum-imports logs && chown -R museai:museai var logs
USER museai
EXPOSE 8000
