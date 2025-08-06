FROM python:3.12.10-slim-bullseye

RUN apt-get update && apt-get install -y \
vim
RUN pip install --upgrade pip

# Install Poetry
RUN pip install poetry

# Copy project files
ADD app /app
ADD pyproject.toml pyproject.toml
ADD poetry.lock poetry.lock

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --no-root --only main

CMD [ "poetry", "run", "fastapi", "run", "./app/main.py", "--port", "80" ]
