FROM python:3.12-slim

LABEL org.opencontainers.image.title="docpipe"
LABEL org.opencontainers.image.description="Unified document parsing, structured extraction, vector ingestion, and RAG pipeline SDK"
LABEL org.opencontainers.image.url="https://docpipe.sunnysinha.online"
LABEL org.opencontainers.image.source="https://github.com/thesunnysinha/docpipe"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir ".[all,server]"

EXPOSE 8000

ENTRYPOINT ["docpipe"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
