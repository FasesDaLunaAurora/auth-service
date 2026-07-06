# syntax=docker/dockerfile:1

# ==============================================================================
# Stage 1: builder — instala dependências em um virtualenv isolado
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# Instala apenas as dependências de execução para manter a imagem final o mais leve possível.

RUN pip install --upgrade pip \
    && pip install .

# ==============================================================================
# Etapa de teste — Inclui ferramentas de desenvolvimento (pytest, ruff, mypy).
# Usada só pelo docker-compose de teste, garantindo que a imagem de produção
# continue leve e sem arquivos desnecessários.
# ==============================================================================
FROM builder AS test

RUN pip install ".[dev]"

WORKDIR /app
COPY . .

CMD ["pytest", "--cov=app", "--cov-report=term-missing"]

# ==============================================================================
# Etapa de runtime — imagem final mínima, sem ferramentas de build/teste
# ==============================================================================
FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser pyproject.toml ./pyproject.toml

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
