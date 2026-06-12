<span class="code-comment"># Ingest a document</span>
curl -u admin:docpipe -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "https://example.com/document.pdf",
    "connection_string": "postgresql://user:pass@db:5432/mydb",
    "table_name": "my_docs",
    "embedding_provider": "google",
    "embedding_model": "models/text-embedding-004",
    "preset": "balanced",
    "api_key": "YOUR_API_KEY"
  }'

<span class="code-comment"># RAG query</span>
curl -u admin:docpipe -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "connection_string": "postgresql://user:pass@db:5432/mydb",
    "table_name": "my_docs",
    "embedding_provider": "google",
    "embedding_model": "models/text-embedding-004",
    "llm_provider": "google",
    "llm_model": "gemini-2.0-flash",
    "api_key": "YOUR_API_KEY"
  }'
