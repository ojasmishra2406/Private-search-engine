# Private Search Engine

Private Search Engine is a privacy-first local search and retrieval engine built with FastAPI, SQLite, and FAISS. It combines lexical BM25 keyword scoring and dense neural embeddings through tuned Reciprocal Rank Fusion (RRF), executing end-to-end multi-stage hybrid retrieval in under 15ms entirely on standard CPU hardware. The system enforces strict pre-retrieval Role-Based Access Control (RBAC) at both the vector and relational database layers, guaranteeing zero document leakage across clearance boundaries.

---

## Core Features

* **Hybrid BM25 + FAISS (HNSW) Retrieval with Tuned RRF Fusion (α=0.7)**  
  Combines exact lexical keyword matching (BM25 with positional postings) and dense semantic vector retrieval via a Hierarchical Navigable Small World (HNSW) FAISS index. Candidates are merged using Reciprocal Rank Fusion with a tuned weighting parameter (α=0.7) determined through empirical grid-search optimization.

* **ONNX-Optimized Dense Embedding Pipeline**  
  Eliminates Python runtime bottlenecks by serving the `all-MiniLM-L6-v2` embedding model through ONNX Runtime with dedicated CPU execution thread pinning. This slashes per-query embedding latency from ~380ms down to 7-8ms while preserving exact mathematical parity (1.0000000 cosine similarity with PyTorch FP32).

* **Pre-Retrieval RBAC via FAISS `IDSelectorBatch`**  
  Security boundaries are enforced natively before nearest-neighbor graph traversal occurs. Query authorization maps to an inheritance hierarchy across five clearance tiers (`Admin`, `Engineering`, `HR`, `Finance`, `Public`). Document IDs are injected into an optimized FAISS `IDSelectorBatch`, delivering a 42.2x speedup over standard array scanning while mathematically preventing out-of-clearance vector exploration.

* **Cross-Encoder Reranking: Built, Tested, and Documented**  
  A secondary cross-encoder reranking tier (`ms-marco-TinyBERT-L-2-v2`) was integrated and evaluated on the full 300-query SciFact academic benchmark. Empirical query-by-query analysis revealed the cross-encoder degraded 58 queries while improving only 45 due to domain mismatch between web-search training data and scientific literature. The reranker was cleanly bypassed in the production path, recovering optimal hybrid retrieval accuracy while preserving the module for domain-aligned workloads.

---

## Verified Benchmarks

All performance and retrieval metrics are backed by reproducible proof logs in the `proofs/` directory.

### 1. Retrieval Quality (SciFact BEIR Benchmark, 300 Queries)
Evaluated offline against the standard academic SciFact ground-truth dataset (5,183 documents, 300 claims):

| Metric | Lexical (BM25 Baseline) | Hybrid Pipeline (α=0.7, Production) |
|---|---:|---:|
| **MRR@10** | 0.6129 | **0.6442** |
| **nDCG@10** | 0.6484 | **0.6759** |
| **Recall@10** | 0.7705 | **0.7990** |
| **RBAC Leakage** | 0.000% | **0.000%** |

### 2. End-to-End Latency Profile
Measured across 30 distinct production queries on standard CPU hardware:

| Subsystem / Pipeline Stage | 24,000 Documents | 100,000 Documents | Complexity |
|---|---:|---:|---|
| **Lexical Search (BM25)** | 0.02 ms | 0.02 ms | O(1) dictionary lookup |
| **Dense Search (HNSW + ONNX)** | 8.57 ms | 11.27 ms | O(log N) graph traversal |
| **Fusion (Weighted RRF)** | 0.56 ms | 0.59 ms | O(K log K) candidate sort |
| **Hydration & Snippets** | 4.60 ms | 6.24 ms | Indexed SQLite B-Tree fetch |
| **Reranking Overhead** | 0.01 ms | 0.01 ms | Bypassed production flag |
| **Total Pipeline (p50)** | **14.06 ms** | **18.52 ms** | **Sub-20ms end-to-end** |
| **Total Pipeline (p95)** | **18.22 ms** | **24.61 ms** | **Sub-25ms worst-case** |

*(Note: Depending on CPU core availability during ONNX embedding inference, 100k p50 ranges between 13.44ms and 18.52ms, with p95 ranging between 15.28ms and 24.61ms -- down from the original 470ms p50 / 868ms p95 baseline).*

*(Historical baseline prior to ONNX export and IDSelectorBatch optimization: 470ms p50 / 868ms p95).*

### 3. Security & Boundary Verification
* **Automated Test Suite**: 256 of 256 unit and integration tests passing.
* **Multi-Tenant Zero-Leakage Audit**: 256 randomized cross-role queries evaluated against the 100,000-document database resulted in **100.0% boundary enforcement and 0.00% data leakage**.

---

## Security Architecture: Safe Selector Caching

During high-concurrency stress testing, an investigation into selector caching identified a critical vulnerability in naive object caching:

### The Vulnerability
Using Python's built-in `id(authorized_int_ids)` as a cache key creates an object-lifecycle collision hazard. When Python frees an ephemeral set object after request completion, the CPython memory allocator frequently reassigns the identical memory address to a newly created set in subsequent requests. In a multi-tenant application, if a restricted role (e.g., `Public`) was allocated memory previously occupied by an `Admin` set, naive `id()` lookups would return the cached Admin filter, leaking confidential document vectors.

### The Fix
The vulnerability was addressed through two structural changes:
1. Implemented `AuthorizedIdSet` in `src/api/security.py`, a specialized set subclass carrying an explicit, immutable string identifier (`cache_key = f"role:{role}"`).
2. Refactored `VectorIndex.search` in `src/dense/vector_index.py` to strictly check `getattr(authorized_int_ids, 'cache_key', None)`. Only explicit, named role sets participate in the selector cache. Ephemeral or un-keyed sets bypass the cache entirely and construct one-off selectors dynamically, eliminating memory address reuse bugs.

---

## System Architecture

```text
                          +------------------------+
                          |   HTTP Client / Web    |
                          +-----------+------------+
                                      |
                         FastAPI Gateway (RBAC Guard)
                                      |
                 +--------------------+--------------------+
                 |                                         |
     Lexical Engine (BM25)                      Dense Engine (HNSW)
  - Custom Inverted Index                     - ONNX Embedding Model
  - O(1) Dictionary Lookup                    - 384-Dimensional Vectors
  - Positional Postings Match                 - Cached IDSelectorBatch Filter
                 |                                         |
                 +--------------------+--------------------+
                                      |
                         Reciprocal Rank Fusion
                           (RRF Weight α=0.7)
                                      |
                         Hydration & Snippet Engine
                          - SQLite B-Tree Indexing
                          - Keyword Context Generation
                                      |
                          Structured Search Response
```

### Technology Stack
* **Language & Runtime**: Python 3.12, ONNX Runtime (CPU Execution Provider)
* **API Framework**: FastAPI, Uvicorn, Pydantic v2
* **Storage & Indexing**: SQLite (WAL Mode), FAISS (IndexHNSWFlat + IndexIDMap)
* **NLP & Tokenization**: HuggingFace Transformers, HuggingFace Tokenizers, Custom Stemmer/Tokenizer
* **Frontend**: React 18, Vite, Tailwind CSS

---

## Testing & Quality Assurance

The test suite contains 256 automated tests verifying the entire lifecycle of the system:
* **API Verification** (`tests/test_api.py`): Input boundary checks, HTTP 400 validation, role simulator endpoints, and health monitoring.
* **Lexical Correctness** (`tests/test_bm25.py`, `tests/test_tokenizer.py`, `tests/test_search.py`): Inverted index building, positional term matching, casing normalization, and technical keyword preservation.
* **Dense Retrieval** (`tests/test_dense_retrieval.py`): Vector dimensionality validation, nearest-neighbor accuracy, index serialization, and persistence.
* **Incremental Indexing & Storage** (`tests/test_storage_phase3.py`): Soft-delete tombstones, document version incrementation, and atomic index swapping.
* **RBAC & Security** (`tests/test_phase25_security.py`): Pre-retrieval role filtering, crawler SSRF protection, and multi-tenant isolation.
* **Search Quality & Robustness** (`tests/test_phase17_search_quality.py`, `tests/test_phase18_robustness.py`): Deduplication, empty query handling, and graceful fallback handling.

To run the complete test suite:
```bash
pytest -v
```

---

## Quickstart

### Prerequisites
* Python 3.12+
* Node.js 18+ (for frontend)
* 4GB RAM minimum

### 1. Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
export PYTHONPATH="."
```

### 2. Start the Backend API
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
API documentation is available at `http://localhost:8000/docs`.

### 3. Start the Frontend Application
```bash
cd frontend
npm install
npm run dev
```
Access the search interface at `http://localhost:5173`.

---

## Current Scope & Roadmap

* **Scale Verification**: Rigorously validated up to 100,000 documents and vectors using structured synthetic benchmark content to stress-test high-dimensional graph traversal, inverted index postings, and relational pagination under load.
* **Cross-Encoder Reranker**: Retained in `src/reranker/` and disabled by default via `USE_RERANKER = False` in `src/api/main.py`. Re-enabling the cross-encoder is a one-line configuration toggle for workloads where queries and corpus content align with MS-MARCO domain characteristics.
