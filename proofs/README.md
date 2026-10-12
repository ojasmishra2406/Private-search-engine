# Verification Proofs & Benchmark Logs

This directory contains empirical evidence, benchmark outputs, and test logs backing every architectural and performance claim in the repository.

---

## Index of Proof Artifacts

### 1. Latency Optimization (`proofs/latency_optimization/`)
| Artifact Filename | What It Proves | Date |
|---|---|---|
| `idselector_optimization_proof.txt` | 42.2x speedup of `faiss.IDSelectorBatch` (0.476ms) over unoptimized `IDSelectorArray` (20.067ms) on 100k vectors | Oct 2026 |
| `onnx_vs_pytorch_lossless.txt` | Lossless mathematical equivalence (1.0000000 cosine similarity) between PyTorch FP32 and ONNX Runtime embeddings | Oct 2026 |
| `profile_24k_p50_14ms.txt` | Fresh 30-query per-stage breakdown on 24,000 corpus: **14.06ms p50 / 18.22ms p95** | Oct 2026 |
| `profile_100k_proof.txt` | Fresh 30-query per-stage breakdown on 100,000 corpus: **18.52ms p50 / 24.61ms p95** (idle baseline: 13.44ms / 15.28ms) | Oct 2026 |
| `debug_dense.log` | Raw per-query ONNX encode (~7-8ms) and FAISS graph search (~0.8-1.2ms) execution times | Oct 2026 |
| `mrr_and_latency_proof.txt` | Historical pre-optimization latency and MRR validation baseline | Oct 2026 |

### 2. Scale Testing (`proofs/scale_testing/`)
| Artifact Filename | What It Proves | Date |
|---|---|---|
| `scale_100k_counts_proof.txt` | Triple-verified count across SQLite (100,000), FAISS (100,000), and Lexical Inverted Index (100,000) | Oct 2026 |
| `scale_24k_counts_proof.txt` | Triple-verified count across SQLite (24,000), FAISS (24,000), and Lexical Inverted Index (24,000) | Oct 2026 |
| `24000_corpus_proof.txt` | Historical database row counts and index size validation for the 24k corpus | Oct 2026 |

### 3. Retrieval Quality & Evaluation (`proofs/retrieval_quality/`)
| Artifact Filename | What It Proves | Date |
|---|---|---|
| `hybrid_only_eval.txt` | Full 300-query SciFact academic benchmark (Hybrid-Only): **MRR@10 0.6442, nDCG@10 0.6759, Recall@10 0.7990** | Oct 2026 |
| `scifact_eval_100k.txt` | Validation that hybrid retrieval quality is scale-invariant and reproducible: **MRR@10 0.6442** | Oct 2026 |
| `reranker_impact.txt` | Direct A/B impact study on 300 queries: Cross-Encoder improved 45 queries but degraded 58 queries (net negative) | Oct 2026 |
| `reranker_output_with_recall.txt` | Full evaluation output with Recall@10 logged alongside MRR and nDCG | Oct 2026 |
| `det_test.txt` | Determinism validation proving back-to-back identical retrieval ranking across sessions | Oct 2026 |
| `scifact_eval.txt` | Baseline Lexical BM25 (MRR 0.6129, nDCG 0.6484) on standard SciFact | Oct 2026 |
| `scifact_eval_full.txt` | Historical baseline with initial Cross-Encoder scoring on SciFact | Oct 2026 |

### 4. Security & Access Control (`proofs/security/`)
| Artifact Filename | What It Proves | Date |
|---|---|---|
| `id_cache_collision_security_fix_proof.txt` | Security validation confirming elimination of Python `id()` cache collision vulnerability via `AuthorizedIdSet` | Oct 2026 |
| `rbac_100k_256_tests_proof.txt` | 256 randomized cross-role queries against 100,000-doc corpus: **256/256 passed (100.0%), 0.00% leakage** | Oct 2026 |
| `rbac_256_tests_proof.txt` | Historical 256 zero-leakage RBAC queries against 24,000-doc corpus (100.0% boundary enforcement) | Oct 2026 |
| `pytest_256_passed_proof.txt` | Complete test suite execution confirming **256/256 tests passing** | Oct 2026 |

---

### Legacy Benchmarks & Summaries
* `proofs/benchmarks/benchmark_report.json` - Structured JSON benchmark report
* `proofs/benchmarks/scale_and_quantization_proof.txt` - FP32 vs INT8 ONNX quantization log
* `proofs/tests/perfect_suite.log` - Pytest log output
* `proofs/tests/perfect_suite.txt` - Summary report of passing suite
