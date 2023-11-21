FROM python:3.11-slim as builder

# Configure Poetry
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

RUN pip install --upgrade pip setuptools && \
    pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-root --no-ansi --without dev

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app
COPY --from=builder /app/.venv ./.venv

RUN mkdir -p /opt/miso/db/

COPY . /app

CMD ["python", "miso_nanopore_runscanner/main.py"]
