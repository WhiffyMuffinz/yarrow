FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# Build context is the repository root so that the shared ../packages/yarrow-db
# path dependency resolves. The repo layout is preserved inside the image.
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==2.5.1

# Copy the shared package first, then the service's dependency manifests
COPY packages/ /app/packages/
COPY worker/pyproject.toml worker/poetry.lock* /app/worker/

WORKDIR /app/worker

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY worker/ /app/worker/

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info"]
