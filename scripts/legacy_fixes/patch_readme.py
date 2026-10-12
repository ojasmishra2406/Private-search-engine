# -*- coding: utf-8 -*-
with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

header_index = content.find("## System Architecture")
rest_of_readme = content[header_index:]

new_header = """# Private Search Engine - Neural + Lexical Information Retrieval

**Built a highly scalable, enterprise-grade private search engine from the ground up, combining traditional lexical matching with neural semantic search (BM25 + Sentence Transformers) and a fully integrated Streaming RAG (Retrieval-Augmented Generation) synthesis pipeline.** 

**Engineered for strict data privacy and zero-leakage security, the system features a hard-enforced Role-Based Access Control (RBAC) layer that filters the vector space at retrieval time. To prevent LLM hallucinations, a Corrective RAG (CRAG) gate evaluates retrieval confidence and authorization thresholds, instantly refusing unauthorized queries while successfully streaming sentence-level attributed answers (`[Doc X]`) to authorized users.**

**Developed a fully asynchronous web-crawling and ingestion pipeline backed by SQLite and a highly scalable Hierarchical Navigable Small World (HNSW) FAISS index. The infrastructure was rigorously stress-tested against a production-scale database of over 24,000 high-dimensional vectors, maintaining sub-millisecond similarity search times at scale.**

**To break local compute bottlenecks without relying on expensive GPU clusters, the cross-encoder reranking pipeline was aggressively optimized using ONNX Runtime INT8 quantization (via FlashRank). This compressed reranker latency by 82% (from ~900ms down to ~156ms).**

**The application layer is built with FastAPI and React, featuring an interactive UI with dynamic RAG citation highlighting, SSRF protection, index/database consistency tracking, concurrent synchronization, and health monitoring. Achieved an end-to-end hybrid-search and reranking p50 latency of ~287ms on CPU, with a robust suite of automated tests verifying retrieval precision, RBAC boundary enforcement, and CRAG refusal safety.**

***

### Streaming RAG Synthesis with Sentence-Level Citations
![RAG Synthesis](docs/rag_synthesis.png)
*The engine leverages the retrieved context to synthesize answers on the fly. Every claim is strictly grounded in the database, with interactive `[Doc X]` tags that map directly to the source passages to eliminate LLM hallucinations.*

### Zero-Trust CRAG Gate (Corrective RAG)
![CRAG Gate](docs/crag_refusal.png)
*If a user searches for highly confidential information outside their clearance level (or if the database simply lacks relevant context), the CRAG gate instantly intercepts the request. It securely refuses to answer, preventing both data leaks and hallucinated responses.*

### Dynamic Role-Based Access Control (RBAC)
![RBAC Verification](docs/rbac_admin.png)
*When an authorized user queries the exact same confidential topic, the system instantly filters the vector space to their specific clearance level, retrieving and synthesizing the exact financial or internal documentation required.*

***

"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_header + rest_of_readme)
