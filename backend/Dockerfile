# fly-safe backend — uv-based image for Fly.io.
FROM python:3.13-slim

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install deps first (cache layer) — prod only, from the lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# App code (includes content/history and the source modules).
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
# Ephemeral SQLite on the container's own disk (no persistent volume) — the
# snapshot is a disposable cache that repopulates from sources on each boot.
ENV DATABASE_URL="sqlite+aiosqlite:////tmp/flysafe.db"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
