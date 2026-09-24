#!/usr/bin/env bash
# One-time setup for the Yarrow devcontainer. Runs as the vscode user.
# Idempotent: safe to re-run against a recreated container with persistent volumes.
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.poetry-venv/bin:$HOME/.local/bin:$PATH"

# Node comes from the devcontainer node feature (nvm under /usr/local/share/nvm)
export NVM_DIR=/usr/local/share/nvm
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi

# 1. App env file. The backend reads .env via pydantic-settings; defaults in
# app/core/config.py already match the compose service names in this project.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# 2. Python tooling, pinned to the version used by backend/worker Dockerfiles and CI.
# Lives in a tooling venv so no system pip (PEP 668) or sudo is needed.
if [ ! -x "$HOME/.poetry-venv/bin/poetry" ]; then
  python -m venv "$HOME/.poetry-venv"
  "$HOME/.poetry-venv/bin/pip" install --quiet --upgrade pip
  "$HOME/.poetry-venv/bin/pip" install --quiet "poetry==1.8.2"
fi

# 3. JS dependencies: root (husky, lint-staged, prettier) and frontend.
npm install --no-audit --no-fund
(cd frontend && npm install --no-audit --no-fund)

# 4. Python dependencies for backend and worker (project venvs under ~/.cache/pypoetry).
# --no-root: neither project is packaged (matches the Dockerfiles).
poetry -C backend install --no-interaction --no-root
poetry -C worker install --no-interaction --no-root

# 5. Wait for postgres to accept connections, then apply migrations.
# Seeding (backend: python -m app.db.seed) is left as a manual step: the
# locked passlib 1.7.4 + bcrypt 5.0.0 combination crashes in get_password_hash.
for _ in $(seq 1 30); do
  if poetry -C backend run python -c "
import asyncio, asyncpg
asyncio.run(asyncpg.connect('postgresql://yarrow:yarrow_password@postgres:5432/yarrow', timeout=2))
" 2>/dev/null; then
    break
  fi
  sleep 2
done
(cd backend && poetry run alembic upgrade head)

echo "post-install complete:"
node --version
poetry -C backend run python --version
