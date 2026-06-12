# docpipe plugin licenses

docpipe core is **MIT**. Optional plugins may use copyleft or commercial-friendly licenses.

| Plugin | Group | License | GPU | Notes |
|--------|-------|---------|-----|-------|
| docling | parser | MIT | optional | Default balanced parser |
| markitdown | parser | MIT | no | Fast office/HTML conversion |
| pymupdf | parser | **AGPL-3.0** | no | Fast PDF; not in default `[all]` |
| mineru | parser | Apache-2.0 | yes | High-accuracy PDF/layout |
| paddleocr | parser | Apache-2.0 | optional | PP-Structure OCR |
| unstructured | parser | Apache-2.0 | optional | Broad format partition |
| glm-ocr | parser | see package | yes | Vision OCR |
| recursive | chunker | MIT | no | LangChain splitter (default) |
| semchunk | chunker | MIT | no | Hierarchical token chunking |
| chonkie-* | chunker | MIT | optional | Semantic / late chunking |
| flashrank | reranker | MIT | no | Fast CPU rerank |
| cohere | reranker | commercial API | no | Hosted rerank API |
| bge / mxbai | reranker | MIT models | optional | Quality cross-encoders |
| builtin | evaluator | MIT | no | Hit rate, MRR, LLM judges |
| ragas | evaluator | Apache-2.0 | optional | RAGAS metric suite |
| langchain | extractor | MIT | no | Native strict JSON schema |
| outlines | extractor | Apache-2.0 | optional | Local structured gen |
| autogen | agent | MIT | no | Microsoft AutoGen agents |
| langgraph | agent | MIT | no | LangGraph ReAct agent |
| lightrag | RAG strategy | MIT | optional | Graph-augmented RAG index |

Install copyleft parsers explicitly when policy allows:

```bash
pip install 'docpipe-sdk[pymupdf]'
```
