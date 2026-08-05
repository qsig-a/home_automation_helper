FROM python:3.12.10-slim-bullseye

RUN apt-get update && apt-get install -y \
vim
RUN pip install --upgrade pip

# Install Poetry
RUN pip install poetry

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy project files
ADD --chown=appuser:appuser app ./app
ADD --chown=appuser:appuser pyproject.toml pyproject.toml
ADD --chown=appuser:appuser poetry.lock poetry.lock

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --no-root --only main

# Switch to non-root user
USER appuser

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080" ]
