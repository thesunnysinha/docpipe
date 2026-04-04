FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir ".[all,server]"

ENTRYPOINT ["docpipe"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
