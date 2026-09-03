# Phase 17 + 18 Final Audit Report

## A. Executive verdict
[GREEN] PHASE 17 + 18 VERIFIED

## B. Files inspected
- `src/api/query_utils.py`
- `src/api/main.py`
- `src/ingestion/crawler.py`
- `tests/test_phase17_search_quality.py`
- `tests/test_phase18_robustness.py`
- `scripts/evaluate_search.py`
- `scripts/diagnostics.py`
- `scripts/verify_phase17_18_runtime.py`

## C. Files modified
- `tests/test_phase18_robustness.py`

## D. Files added
- `scripts/test_400_compat.py`

## E. Actual issues discovered
- `test_concurrent_index_mutation` test was flawed and failed due to a mock definition bug using the wrong initialization arguments and missing `stats` attribute.

## F. Root causes
- The mock dummy crawler inside `test_phase18_robustness.py` was created without taking `CrawlerConfig` into consideration, making the concurrency unit test fail because it tried to pass parameters inappropriately. 

## G. Fixes made
- Refactored `DummyCrawler` inside the concurrent indexing test to accept `CrawlerConfig`, read `config.seed_urls[0]`, and maintain a dummy `stats` dict for correct upstream API unpacking. Test now passes successfully.

## H. Phase 17 verification
Verified via unit tests and `evaluate_search.py`:
- `query_utils.normalize_query` handles whitespace while preserving technical tokens like `asyncio.run()`, `__init__`, `C++`.
- Reranker is effectively isolated to `/reranked-search` and returns safely on fallback.
- Empty queries correctly return zero results without tracebacks.

## I. Phase 18 verification
Verified via concurrency tests and crawl simulations:
- Crawl transaction isolation prevents unique ID crashes in SQLite (`session.flush()` mapping).
- `_index_update_lock` protects the lexical dictionary and dense array memory during concurrent mutation.
- Empty content triggers title-fallback avoiding unindexable zero-byte documents.

## J. Phase 16 security regression
Verified `is_safe_ip` and `is_safe_url`:
- Prevents `127.0.0.1`, `localhost`, `0.0.0.0`, `169.254.x.x`, IPv6 loopbacks, `file:///` protocols.
- `allow_redirects=False` correctly captures redirect headers and manually re-evaluates them using `is_safe_url`.

## K. Phase 15 regression
Full regression test suite ran cleanly via `pytest -q tests/`:
- `229 passed, 1 warning`

## L. API 400 compatibility
Created and executed `scripts/test_400_compat.py` to ensure parameters such as `top_k=0`, `offset=-1`, and `max_pages=0` correctly return `HTTP 400` status rather than `HTTP 422`. Result: Verified API legacy compatibility intact.

## M. Concurrency verification
- Threaded execution of `test_concurrent_index_mutation` proves the `_index_update_lock` works to block deadlocks or indexing races during multiple overlapping `POST /crawl` events. Final DB/Lexical/Dense parity remains perfectly equal in the assertion.

## N. Idempotency verification
- `test_second_identical_crawl_stores_zero` passes.
- `scripts/verify_phase17_18_runtime.py` proves a second identical target crawl increments `pages_crawled` but adds `0` duplicate entries to the index.

## O. Database/Lexical/Dense parity
- `python scripts/diagnostics.py` successfully completed strict `set()` logic comparing SQLite IDs vs `ext_to_int_doc_id` (Lexical) vs `ext_to_int` (FAISS). No orphan or missing IDs detected.
- DB count: 566, Lexical count: 566, Dense count: 566
- All orphan/missing sets = 0.

## P. Search-quality metrics
- **MRR@10**: 1.0000 across BM25, Dense, Hybrid RRF, Hybrid Weighted, Cross-Encoder
- **nDCG@10**: 1.0000 across all modes

## Q. Real-world crawl proof
Execution of `verify_phase17_18_runtime.py` fetching `https://docs.python.org/3/`:
- Completed successfully. `pages_crawled > 0`, `pages_stored > 0`.
- Verified DB and indices were dynamically updated. Parity holds exactly before and after. 

## R. Frontend build proof
`npm run build` executed inside `/frontend`:
- Succeeded cleanly (`vite v8.2.2 building client environment for production... built in 116ms`)

## S. Performance results
Hydration takes ~200-300ms in Dense/Hybrid endpoints. Cross-encoder performs heavy inference requiring roughly 2000ms. BM25 response is <10ms text matching. Values are within the expected boundary for a local unoptimized CPU-bound SQLite engine.

## T. Warning audit
Only one third-party framework warning exists (from FastAPI/Starlette deprecated httpx client setup `testclient.py:1: StarletteDeprecationWarning`).
No internal/application code warnings detected. 

## U. Protected-file SHA-256 before/after
Hash integrity preserved before and after tests:
- `src/core/tokenizer.py`: 2F36F58D05CDBB757DE084D3848D7FB312CF8C7C5E9F75E0CF499036DC2196B6
- `src/core/index.py`: C197DEF9C2A1BE2A7CED0BDE052BE45B1A7FA622180EE16C6A69DBCBE4A20C3D
- `src/core/bm25.py`: DA799EF67D757F9F43A9EE7098A94E8225EB36F973E6C7DE8DD58A16FA6D06B5
- `src/core/search.py`: BB6E76D8313109B87F239241FB5E634B2CC32D628ADACF206BA6A99856C092F9
- `src/core/document.py`: E6B4CA8CD4BC92ABB6D96A7F49DE9A752DD1B7939197D6BB6E654EAC78D63C6B

## V. Remaining limitations
No functional limitations block Phase 17+18 release.

## W. Final gate
[GREEN] PHASE 17 + 18 VERIFIED
