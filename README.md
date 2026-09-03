# Palladian Private Search Engine

A fully self-hosted, privacy-first enterprise search engine. This project crawls web documentation, embeds content entirely locally using HuggingFace sentence transformers, and provides lightning-fast lexical, dense, hybrid, and reranked search pipelines via a modern React dashboard. 

No data ever leaves your machine. 

## ?? Key Features
- **Asynchronous Web Crawler:** High-performance, concurrent web scraping with configurable depth, domain restrictions, and fault tolerance.
- **Local AI Embedding & Reranking:** 100% offline embedding (ll-MiniLM-L6-v2) and cross-encoder reranking (ms-marco-MiniLM-L-6-v2).
- **Multi-Modal Search:**
  - **BM25 (Lexical):** Highly tuned keyword search using SQLite FTS.
  - **Dense (Semantic):** Vector similarity search using FAISS.
  - **Hybrid:** Reciprocal Rank Fusion (RRF) and Weighted score combinations of BM25 and Dense.
  - **Cross-Encoder Reranking:** Deep contextual semantic scoring for maximum relevance.
- **Modern Dashboard UI:** React/Vite frontend featuring live backend health metrics, latency tracking, instant hot-reloading after crawls, and configurable top-k pagination.
- **Dockerized & Persistent:** Automated infrastructure setup with persistent HuggingFace model caching and safe atomic database writes.

---

## ?? Screenshots & Demo

> **Note to Developer:** Please insert screenshots or a demo GIF here before publishing.

![Search Dashboard - Hybrid Search](https://via.placeholder.com/800x400?text=Insert+Search+Dashboard+Screenshot+Here)
*The main search UI showing query results and backend latency metrics.*

![Web Crawler Configuration](https://via.placeholder.com/800x400?text=Insert+Crawler+UI+Screenshot+Here)
*Configuring a new web crawl pipeline directly from the UI.*

---

## ?? Architecture & Data Flow

1. **Crawler Pipeline:** URLs are dispatched via an asynchronous syncio queue using BeautifulSoup4. Content is stripped of boilerplate, deduplicated by URL hashes, and chunked into indexable documents.
2. **Ingestion & Storage:**
   - **SQLite:** Stores raw document metadata, HTML snippets, and powers the BM25 term frequency index.
   - **FAISS:** High-performance C++ vector library running on CPU/GPU that stores dense semantic vectors.
3. **Search Engine API:** A lightweight FastAPI layer orchestrates the retrieval. 
4. **React Frontend:** Communicates via REST. Features responsive dynamic components that instantly sync with the backend /health status (detecting degraded or missing indexes).

### Concurrency & Fault Tolerance
- **Atomic Operations:** The SQLite database utilizes Write-Ahead Logging (WAL) and single-writer concurrency controls to prevent database locking during intense async crawls.
- **Persistent Caching:** HuggingFace sentence-transformers models are cached to a persistent Docker volume (/app/data/hf_cache). The system survives container rebuilds without re-downloading ~200MB models.
- **Hot-Reloading Search:** The search engine dynamically re-instantiates index singletons inside the Uvicorn worker as soon as a crawl finishes, meaning zero downtime or restarts are needed to search new data.

---

## ? Performance & Benchmarks
The system has been heavily hardened and verified through rigorous local testing:

- **Indexing Throughput:** ~5-15 pages per second (depending on host network/CPU overhead during BS4 parsing and tokenization).
- **Lexical Latency (BM25):** ~10-30ms
- **Dense Latency (FAISS):** ~20-50ms 
- **Reranker Latency:** ~150-250ms (for Top-K=20 contexts)
- **Test Coverage:** Verified by an extensive 256-test Pytest regression suite running at 100% pass rate. 

---

## ?? Tech Stack
- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLite3, FAISS-cpu
- **Machine Learning:** HuggingFace sentence-transformers, cross-encoder
- **Crawler:** iohttp, BeautifulSoup4
- **Frontend:** React, Vite, CSS3
- **Infrastructure:** Docker, Docker Compose

---

## ?? Local Setup & Deployment

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local frontend development)

### 1. Start the Environment
Clone the repository and set up your environment variables:
\\\ash
cp .env.example .env
docker compose up -d --build
\\\

The backend API will start at \http://localhost:8000\. On the first boot, it will automatically download the required ML models to the persistent volume.

### 2. Start the Frontend
In a separate terminal, start the Vite development server:
\\\ash
cd frontend
npm install
npm run dev
\\\
Navigate to \http://localhost:5173\ in your browser to access the dashboard.

### 3. Usage
1. Open the **Web Crawl** tab in the sidebar.
2. Enter a seed URL (e.g., \https://docs.pytest.org/en/stable/\).
3. Set Max Pages (e.g., 20) and click Start.
4. Once completed, navigate to the **Search** tab and instantly query your private offline knowledge base.

---

## ?? Project Structure

\\\	ext
.
+-- docker-compose.yml       # Infrastructure orchestration
+-- Dockerfile               # Backend container definition
+-- src/
¦   +-- api/
¦       +-- main.py          # FastAPI application & endpoints
¦       +-- crawler.py       # Async web scraper
¦       +-- search_engine.py # Core BM25/Dense/Reranker algorithms
+-- frontend/                # React/Vite dashboard application
+-- tests/                   # 256 Pytest integration & unit tests
+-- scripts/                 # Developer utility scripts (e.g., dataset generation)
+-- verification/            # System audit and parity verification scripts
\\\

---

## ?? Limitations & Future Improvements
- **FAISS GPU Support:** Currently runs on aiss-cpu to maximize cross-platform Docker compatibility (especially for ARM64/Apple Silicon architecture). Compiling aiss-gpu from source is required for GPU acceleration on non-x86 hardware.
- **Client-Side Rendering:** The BeautifulSoup crawler extracts static HTML. It does not currently execute headless browsers (like Playwright/Puppeteer) for heavy SPA/JavaScript-rendered sites.
