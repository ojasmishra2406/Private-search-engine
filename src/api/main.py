import os
import sys
import pickle
import time
import threading
from contextlib import asynccontextmanager
from typing import List, Optional, Dict
import urllib.parse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.security import get_authorized_doc_ids
from pydantic import BaseModel
from src.api.query_utils import normalize_query

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.search import LexicalSearch
from src.core.tokenizer import Tokenizer
from src.storage.database import Database
from src.storage.models import DBDocument
from src.api.snippets import SnippetGenerator
from src.api.config import settings
from src.core.logger import logger

# Global state
app_state = {}

# Lock protecting in-memory index mutations during crawl/sync
_index_update_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load index on startup — exactly once.
    logger.logger.info("Loading InvertedIndex...")
    try:
        with open(settings.LEXICAL_INDEX_PATH, 'rb') as f:
            index = pickle.load(f)
        tokenizer = Tokenizer()
        app_state["search_engine"] = LexicalSearch(index, tokenizer)
        app_state["snippet_generator"] = SnippetGenerator(tokenizer)
        logger.logger.info(f"Index loaded successfully with {index.total_docs} documents.")
    except Exception as e:
        logger.logger.error(f"Warning: Failed to load index.pkl: {e}")
        app_state["search_engine"] = None

    # Setup database (applies Phase 3 migrations on first run)
    db = Database(db_url=settings.DB_PATH)
    db.init_db()
    app_state["db"] = db

    # Dense Retrieval Initialization
    try:
        logger.logger.info("Loading Dense Index...")
        from src.dense.embeddings import EmbeddingModel
        from src.dense.vector_index import VectorIndex
        from src.dense.retriever import DenseRetriever
        
        v_idx = VectorIndex(index_path=settings.DENSE_INDEX_PATH)
        emb_model = EmbeddingModel(settings.DENSE_MODEL_NAME)
        app_state["dense_retriever"] = DenseRetriever(emb_model, v_idx)
        logger.logger.info(f"Dense Index loaded successfully with {v_idx.total_docs} vectors.")
    except Exception as e:
        logger.logger.error(f"Warning: Failed to load dense retrieval subsystem: {e}")
        app_state["dense_retriever"] = None
        
    # Hybrid Retrieval Initialization
    from src.hybrid.retriever import HybridRetriever
    lexical = app_state.get("search_engine")
    dense = app_state.get("dense_retriever")
    if lexical and dense:
        app_state["hybrid_retriever"] = HybridRetriever(lexical, dense)
    else:
        # We can still initialize it, it will degrade gracefully
        app_state["hybrid_retriever"] = HybridRetriever(lexical, dense)


    # Cross-Encoder Reranker Initialization
    logger.logger.info("Loading Cross-Encoder...")
    try:
        from src.reranker.cross_encoder import CrossEncoderModel
        from src.reranker.reranker import CrossEncoderReranker
        # Load the model explicitly on CPU to ensure compatibility (default behavior)
        ce_model = CrossEncoderModel(model_name=settings.CROSS_ENCODER_MODEL_NAME)
        reranker = CrossEncoderReranker(ce_model)
        app_state["reranker"] = reranker
        logger.logger.info("Cross-Encoder loaded successfully.")
    except Exception as e:
        logger.logger.error(f"Warning: Failed to load Cross-Encoder: {e}")
        app_state["reranker"] = None

    yield

    logger.logger.info("Shutting down...")



app = FastAPI(title="Private Search Engine API", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.log_error(str(request.url.path), str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

@app.get("/ready")
def readiness_check():
    loaded = app_state.get("search_engine") is not None
    if not loaded:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SearchResultModel(BaseModel):
    doc_id:  str
    title:   str
    url:     str
    score:   float
    snippet: str
    matches: List[str]   # query tokens that appear in the snippet (for highlighting)
    rerank_score: Optional[float] = None
    lexical_score: Optional[float] = None
    dense_score: Optional[float] = None
    hybrid_score: Optional[float] = None
    allowed_roles: str = "Public"
    crag_score: float | None = None
    crag_status: str | None = None



class CrawlRequestModel(BaseModel):
    url: str
    max_pages: int = 10
    max_depth: int = 2
    same_domain_only: bool = True

class CrawlResponseModel(BaseModel):
    seed_url: str
    pages_crawled: int
    pages_stored: int
    pages_failed: int
    max_pages: int
    max_depth: int
    same_domain_only: bool

class SearchResponseModel(BaseModel):
    query:         str
    total_results: int
    offset:        int
    results:       List[SearchResultModel]
    timing:        Optional[Dict[str, float]] = None
    blocked_count: int = 0
    fallback_triggered: bool = False
    overall_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/roles")
def get_roles():
    from src.api.security import ROLE_INHERITANCE
    return {"roles": list(ROLE_INHERITANCE.keys())}

@app.get("/health")
def health_check():
    lexical = app_state.get("search_engine")
    dense = app_state.get("dense_retriever")
    reranker = app_state.get("reranker")
    db = app_state.get("db")
    
    db_reachable = False
    index_version = None
    db_doc_count = None
    if db:
        try:
            session = db.get_session()
            from src.storage.models import IndexVersion, DBDocument
            max_v = session.query(IndexVersion).order_by(IndexVersion.version.desc()).first()
            if max_v:
                index_version = max_v.version
            db_doc_count = session.query(DBDocument).filter_by(is_deleted=False).count()
            db_reachable = True
        except Exception:
            pass
        finally:
            if 'session' in locals():
                session.close()

    lexical_doc_count = lexical.index.total_docs if lexical else None
    dense_doc_count = None
    if dense:
        try:
            dense_doc_count = dense.vector_index.total_docs
        except Exception:
            pass
    parity_ok = (
        db_doc_count is not None
        and lexical_doc_count is not None
        and dense_doc_count is not None
        and db_doc_count == lexical_doc_count == dense_doc_count
    )
    
    status = "healthy" if (lexical and db_reachable and parity_ok) else "degraded"
    
    details = {
        "db": "ok" if db_reachable else "unavailable",
        "lexical_index": "ok" if lexical else "missing",
        "dense_index": "ok" if dense else "missing",
        "reranker": "ok" if reranker else "missing",
        "doc_counts": {
            "db": db_doc_count,
            "lexical": lexical_doc_count,
            "dense": dense_doc_count
        },
        "parity": "ok" if parity_ok else "mismatch",
        "index_version": index_version
    }
    

    logger.log_health(status, details)
                
    return {
        "status": "ok" if (lexical and db_reachable) else "degraded",
        "database_reachable": db_reachable,
        "lexical_index_loaded": lexical is not None,
        "dense_index_loaded": dense is not None,
        "reranker_loaded": reranker is not None,
        "index_generation": index_version,
        "db_doc_count": db_doc_count,
        "lexical_doc_count": lexical_doc_count,
        "dense_doc_count": dense_doc_count,
        "parity_ok": parity_ok,
    }



import math
def calculate_crag_status(logit: float) -> tuple[float, str]:
    if logit >= 0:
        z = math.exp(-logit)
        score = 1.0 / (1.0 + z)
    else:
        z = math.exp(logit)
        score = z / (1.0 + z)
        
    if score >= 0.75:
        status = "CORRECT"
    elif score >= 0.30:
        status = "AMBIGUOUS"
    else:
        status = "INCORRECT"
        
    return score, status

@app.get("/search"
, response_model=SearchResponseModel)
def search(
    q:      str           = Query(...,  description="Search query"),
    role:   str           = Query("Public", description="Simulated user role"),
    top_k:  int           = Query(20,   description="Number of results to return"),
    offset: int           = Query(0,    description="Zero-based result offset for pagination"),
    domain: Optional[str] = Query(None, description="Filter results to URLs containing this domain string"),
):
    """
    BM25 search endpoint.

    Pagination:
        top_k  – page size  (capped at 100)
        offset – skip first N matching results

    Filtering:
        domain – optional substring match against the result URL
                 (e.g. 'docs.python.org')
    """
    # --- Input validation ---
    if top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k must be strictly positive")
    if top_k > settings.MAX_TOP_K:
        top_k = settings.MAX_TOP_K
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")
    if offset > settings.MAX_OFFSET:
        offset = settings.MAX_OFFSET

    q = normalize_query(q)
    if len(q) > settings.MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
    if not q:
        return {"query": q, "total_results": 0, "offset": offset, "results": []}

    engine = app_state.get("search_engine")
    if not engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")

    snippet_gen = app_state.get("snippet_generator")
    db          = app_state.get("db")
    session     = db.get_session()

    try:
        t0 = time.perf_counter()
        # Over-fetch a fixed, large number of candidates so that total_results
        # is consistent regardless of the requested offset.  500 comfortably
        # exceeds the current 555-doc corpus while remaining fast.
        auth_str, auth_int, blocked_count = get_authorized_doc_ids(session, role)
        raw_results = engine.search(q, authorized_int_ids=auth_int, top_k=500)
        t_lexical = time.perf_counter()

        hydrated: List[SearchResultModel] = []
        t_hydration_start = time.perf_counter()

        seen_hashes = set()
        for res in raw_results:
            # Hydrate — skip tombstoned documents (is_deleted=True)
            db_doc = session.query(DBDocument).filter_by(
                int_id=res.doc_id, is_deleted=False
            ).first()

            if db_doc is None:
                continue  # tombstoned or orphaned index entry
                
            if db_doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(db_doc.content_hash)

            title   = db_doc.title   or "Untitled Document"
            url     = db_doc.url     or "unknown-url"
            content = db_doc.content or ""

            # --- Domain filter (Phase 6 requirement) ---
            if domain and domain.lower() not in url.lower():
                continue

            snippet_data = snippet_gen.generate(content, q)

            hydrated.append(SearchResultModel(
                doc_id=str(res.doc_id),
                title=title,
                url=url,
                score=res.score,
                snippet=snippet_data["text"],
                matches=snippet_data["matches"],
                lexical_score=res.score,
                allowed_roles=db_doc.allowed_roles or "Public"
            ))

        # Apply offset pagination
        total = len(hydrated)
        page  = hydrated[offset: offset + top_k]
        
        t_total = time.perf_counter()
        timing = {
            "lexical": t_lexical - t0,
            "hydration": t_total - t_hydration_start,
            "total": t_total - t0
        }
        

        logger.log_search(
            endpoint="/search",
            query=q,
            timing=timing,
            total_results=total,
            returned_results=len(page),
            mode="lexical"
        )

        return {
            "query":         q,
            "total_results": total,
            "offset":        offset,
            "results":       page,
            "timing":        timing
        }
    finally:
        session.close()

@app.get("/dense-search", response_model=SearchResponseModel)
def dense_search(
    q:      str           = Query(...,  description="Search query"),
    role:   str           = Query("Public", description="Simulated user role"),
    top_k:  int           = Query(20,   description="Number of results to return"),
    offset: int           = Query(0,    description="Zero-based result offset for pagination"),
    domain: Optional[str] = Query(None, description="Filter results to URLs containing this domain string"),
):
    """Phase 8 Dense retrieval search endpoint."""
    if top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k must be strictly positive")
    if top_k > settings.MAX_TOP_K:
        top_k = settings.MAX_TOP_K
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")
    if offset > settings.MAX_OFFSET:
        offset = settings.MAX_OFFSET

    q = normalize_query(q)
    if len(q) > settings.MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
    if not q:
        return {"query": q, "total_results": 0, "offset": offset, "results": []}

    dense_retriever = app_state.get("dense_retriever")
    if not dense_retriever:
        raise HTTPException(status_code=503, detail="Dense search engine not initialized")

    snippet_gen = app_state.get("snippet_generator")
    db          = app_state.get("db")
    session     = db.get_session()

    try:
        t0 = time.perf_counter()
        auth_str, auth_int, blocked_count = get_authorized_doc_ids(session, role)
        raw_results = dense_retriever.search(q, authorized_int_ids=auth_int, top_k=500)
        t_dense = time.perf_counter()
        
        hydrated: List[SearchResultModel] = []
        t_hydration_start = time.perf_counter()

        seen_hashes = set()
        for doc_id, score in raw_results:
            db_doc = session.query(DBDocument).filter_by(
                int_id=doc_id, is_deleted=False
            ).first()

            if db_doc is None:
                continue
                
            if db_doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(db_doc.content_hash)

            title   = db_doc.title   or "Untitled Document"
            url     = db_doc.url     or "unknown-url"
            content = db_doc.content or ""

            if domain and domain.lower() not in url.lower():
                continue

            snippet_data = snippet_gen.generate(content, q)

            hydrated.append(SearchResultModel(
                doc_id=str(doc_id),
                title=title,
                url=url,
                score=score,
                snippet=snippet_data["text"],
                matches=snippet_data["matches"],
                dense_score=score
            ))

        total = len(hydrated)
        page  = hydrated[offset: offset + top_k]
        
        t_total = time.perf_counter()
        timing = {
            "dense": t_dense - t0,
            "hydration": t_total - t_hydration_start,
            "total": t_total - t0
        }
        

        logger.log_search(
            endpoint="/dense-search",
            query=q,
            timing=timing,
            total_results=total,
            returned_results=len(page),
            mode="dense"
        )

        return {
            "query":         q,
            "total_results": total,
            "offset":        offset,
            "results":       page,
            "timing":        timing
        }
    finally:
        session.close()

@app.get("/hybrid-search", response_model=SearchResponseModel)
def hybrid_search(
    q:      str           = Query(...,  description="Search query"),
    role:   str           = Query("Public", description="Simulated user role"),
    top_k:  int           = Query(20,   description="Number of results to return"),
    offset: int           = Query(0,    description="Zero-based result offset for pagination"),
    domain: Optional[str] = Query(None, description="Filter results to URLs containing this domain string"),
    method: str           = Query('weighted', description="Fusion method: 'rrf' or 'weighted'"),
    alpha:  float         = Query(0.40,  description="Weight for BM25 in weighted fusion (0.0 to 1.0)"),
):
    """Phase 9 Hybrid retrieval search endpoint."""
    if top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k must be strictly positive")
    if top_k > settings.MAX_TOP_K:
        top_k = settings.MAX_TOP_K
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")
    if offset > settings.MAX_OFFSET:
        offset = settings.MAX_OFFSET

    q = normalize_query(q)
    if len(q) > settings.MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
    if not q:
        return {"query": q, "total_results": 0, "offset": offset, "results": []}

    hybrid_retriever = app_state.get("hybrid_retriever")
    if not hybrid_retriever:
        raise HTTPException(status_code=503, detail="Hybrid search engine not initialized")

    snippet_gen = app_state.get("snippet_generator")
    db          = app_state.get("db")
    session     = db.get_session()

    try:
        t0 = time.perf_counter()
        auth_str, auth_int, blocked_count = get_authorized_doc_ids(session, role)
        raw_results, diagnostics, timing = hybrid_retriever.search(
            q, authorized_int_ids=auth_int, top_k=500, candidate_pool_size=settings.MAX_CANDIDATE_POOL, method=method, alpha=alpha, return_diagnostics=True
        )
        t_hydration_start = time.perf_counter()
        
        hydrated: List[SearchResultModel] = []
        seen_hashes = set()

        for doc_id, score in raw_results:
            db_doc = session.query(DBDocument).filter_by(
                int_id=doc_id, is_deleted=False
            ).first()

            if db_doc is None:
                continue
                
            if db_doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(db_doc.content_hash)

            title   = db_doc.title   or "Untitled Document"
            url     = db_doc.url     or "unknown-url"
            content = db_doc.content or ""

            if domain and domain.lower() not in url.lower():
                continue

            snippet_data = snippet_gen.generate(content, q)

            diag = diagnostics.get(doc_id, {})
            hydrated.append(SearchResultModel(
                doc_id=str(doc_id),
                title=title,
                url=url,
                score=score,
                snippet=snippet_data["text"],
                matches=snippet_data["matches"],
                lexical_score=diag.get('lexical_score'),
                dense_score=diag.get('dense_score'),
                hybrid_score=score
            ))

        total = len(hydrated)
        page  = hydrated[offset: offset + top_k]
        
        t_total = time.perf_counter()
        timing['hydration'] = t_total - t_hydration_start
        timing['total'] = t_total - t0
        

        logger.log_search(
            endpoint="/hybrid-search",
            query=q,
            timing=timing,
            total_results=total,
            returned_results=len(page),
            mode=f"hybrid-{method}"
        )

        return {
            "query":         q,
            "total_results": total,
            "offset":        offset,
            "results":       page,
            "timing":        timing
        }
    finally:
        session.close()



@app.get("/reranked-search", response_model=SearchResponseModel)
def reranked_search(
    q:      str           = Query(...,  description="Search query"),
    role:   str           = Query("Public", description="Simulated user role"),
    top_k:  int           = Query(20,   description="Number of results to return"),
    offset: int           = Query(0,    description="Zero-based result offset for pagination"),
    domain: Optional[str] = Query(None, description="Filter results to URLs containing this domain string"),
    candidate_pool_size: int = Query(50, description="Number of candidates to fetch from hybrid before reranking"),
    method: str           = Query('weighted', description="Fusion method for hybrid retrieval"),
    alpha:  float         = Query(0.40,  description="Weight for BM25 in weighted fusion"),
):
    """Phase 10 Reranked search endpoint."""
    if top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k must be strictly positive")
    if top_k > settings.MAX_TOP_K:
        top_k = settings.MAX_TOP_K
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")
    if offset > settings.MAX_OFFSET:
        offset = settings.MAX_OFFSET
    if candidate_pool_size > settings.MAX_CANDIDATE_POOL:
        candidate_pool_size = settings.MAX_CANDIDATE_POOL

    q = normalize_query(q)
    if len(q) > settings.MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
    if not q:
        return {"query": q, "total_results": 0, "offset": offset, "results": []}

    hybrid_retriever = app_state.get("hybrid_retriever")
    if not hybrid_retriever:
        raise HTTPException(status_code=503, detail="Hybrid search engine not initialized")

    snippet_gen = app_state.get("snippet_generator")
    db          = app_state.get("db")
    session     = db.get_session()
    reranker = app_state.get("reranker")
    
    try:
        t0 = time.perf_counter()
        # 1. Retrieve candidates
        auth_str, auth_int, blocked_count = get_authorized_doc_ids(session, role)
        raw_results, diagnostics, timing = hybrid_retriever.search(
            q, authorized_int_ids=auth_int, top_k=candidate_pool_size + 100, candidate_pool_size=settings.MAX_CANDIDATE_POOL, method=method, alpha=alpha, return_diagnostics=True
        )
        
        t_hydration_start = time.perf_counter()
        # 2. Domain filtering and text hydration for candidate pool
        from src.reranker.reranker import RerankCandidate
        candidates = []
        doc_metadata = {}
        seen_hashes = set()
        
        for doc_id, score in raw_results:
            if len(candidates) >= candidate_pool_size:
                break
                
            db_doc = session.query(DBDocument).filter_by(int_id=doc_id, is_deleted=False).first()
            if db_doc is None:
                continue
                
            if db_doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(db_doc.content_hash)

            url = db_doc.url or "unknown-url"
            if domain and domain.lower() not in url.lower():
                continue

            title = db_doc.title or "Untitled Document"
            content = db_doc.content or ""
            snippet_data = snippet_gen.generate(content, q)
            text = f"{title}\n{snippet_data['text']}\n{content}"
            candidates.append(RerankCandidate(
                doc_id=str(doc_id),
                text=text,
                original_score=score
            ))
            
            doc_metadata[str(doc_id)] = {
                "title": title,
                "url": url,
                "snippet_text": snippet_data["text"],
                "matches": snippet_data["matches"],
                "lexical_score": diagnostics.get(doc_id, {}).get('lexical_score'),
                "dense_score": diagnostics.get(doc_id, {}).get('dense_score'),
                "allowed_roles": db_doc.allowed_roles
            }

        t_rerank_start = time.perf_counter()
        # 3. Rerank candidate pool
        if reranker and len(candidates) > 0:
            try:
                # Prune to Top 15 before cross-encoder latency optimization
                candidates = candidates[:15]
                # Keep all candidates in order to apply pagination safely
                reranked_cands = reranker.rerank(q, candidates, top_k=0)
            except Exception as e:
                logger.logger.warning(f"Reranker failed, falling back to hybrid: {e}")
                reranked_cands = candidates
        else:
            reranked_cands = candidates

        t_rerank_end = time.perf_counter()
        # 4. Apply offset/top_k
        total = len(reranked_cands)
        page = reranked_cands[offset: offset + top_k]

        # Evaluate global fallback triggered based on TOP-1 candidate GLOBALLY (not per page)
        fallback_triggered = False
        overall_confidence = 0.0
        
        if reranked_cands:
            top_cand = reranked_cands[0]
            # Ensure we use raw cross-encoder logit, not RRF score
            raw_logit = top_cand.rerank_score if top_cand.rerank_score is not None else -99.0
            overall_confidence, _ = calculate_crag_status(raw_logit)
            
            if overall_confidence < 0.30:
                fallback_triggered = True
        else:
            fallback_triggered = True

        # 5. Hydrate final output
        hydrated = []
        for cand in page:
            meta = doc_metadata[cand.doc_id]
            
            # Evaluate CRAG for the specific candidate
            cand_logit = cand.rerank_score if cand.rerank_score is not None else -99.0
            crag_score, crag_status = calculate_crag_status(cand_logit)
            
            hydrated.append(SearchResultModel(
                doc_id=cand.doc_id,
                title=meta["title"],
                url=meta["url"],
                score=cand.original_score,
                snippet=meta["snippet_text"],
                matches=meta["matches"],
                lexical_score=meta["lexical_score"],
                dense_score=meta["dense_score"],
                hybrid_score=cand.original_score,
                rerank_score=cand_logit,
                crag_score=crag_score,
                crag_status=crag_status,
                allowed_roles=meta.get("allowed_roles", "Public")
            ))
            
        t_total = time.perf_counter()
        timing['hydration'] = t_rerank_start - t_hydration_start
        timing['reranking'] = t_rerank_end - t_rerank_start
        timing['total'] = t_total - t0
        

        logger.log_search(
            endpoint="/reranked-search",
            query=q,
            timing=timing,
            total_results=total,
            returned_results=len(page),
            mode=f"reranked-{method}"
        )

        return {
            "query":         q,
            "total_results": total,
            "offset":        offset,
            "results":       hydrated,
            "timing":        timing,
            "fallback_triggered": fallback_triggered,
            "overall_confidence": overall_confidence
        }
    finally:
        session.close()


@app.post("/crawl", response_model=CrawlResponseModel)
def crawl_website(req: CrawlRequestModel):
    import time

    t0 = time.perf_counter()
    
    if req.max_pages <= 0 or req.max_pages > 100:
        raise HTTPException(status_code=400, detail="max_pages must be between 1 and 100")
    if req.max_depth < 0 or req.max_depth > 3:
        raise HTTPException(status_code=400, detail="max_depth must be between 0 and 3")
    
    parsed = urllib.parse.urlsplit(req.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme. Must be http or https")
    
    from src.ingestion.crawler import WebCrawler, CrawlerConfig, is_safe_url
    if not is_safe_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe URL")
        
    config = CrawlerConfig(
        seed_urls=[req.url],
        allowed_domains=[parsed.netloc.lower()],
        max_depth=req.max_depth,
        max_pages=req.max_pages,
        same_domain_only=req.same_domain_only
    )
    
    crawler = WebCrawler(config)
    pages_crawled = 0
    pages_stored = 0
    
    import hashlib
    from datetime import datetime, timezone
    from src.storage.database import Database
    from src.storage.models import DBDocument, IndexingStatus
    
    db = app_state.get("db")
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
        
    session = db.get_session()
    
    # Track doc_ids stored in THIS crawl session to avoid duplicate inserts
    # from the same URL appearing under multiple canonical forms in one batch
    crawl_session_ids: set = set()

    from sqlalchemy import func
    max_int_id_result = session.query(func.max(DBDocument.int_id)).scalar()
    next_int_id = (max_int_id_result or 0) + 1

    # Fetch all items concurrently from async crawler
    results = crawler.crawl()
    
    # 1. Fetch all existing documents matching the extracted doc_ids
    doc_ids = [hashlib.sha256(url.encode('utf-8')).hexdigest() for url, _, _ in results]
    existing_docs = session.query(DBDocument).filter(DBDocument.id.in_(doc_ids)).all()
    existing_map = {d.id: d for d in existing_docs}
    
    new_docs = []
    
    for url, title, content_text in results:
        pages_crawled += 1
        doc_id = hashlib.sha256(url.encode('utf-8')).hexdigest()
        content_hash = hashlib.sha256(content_text.encode('utf-8')).hexdigest()
        
        # RBAC Role Assignment
        lower_url = url.lower()
        if any(token in lower_url for token in ['/eng/', '/dev/', '/tech/']):
            assigned_role = 'Engineering'
        elif any(token in lower_url for token in ['/hr/', '/careers/', '/people/']):
            assigned_role = 'HR'
        elif any(token in lower_url for token in ['/finance/', '/pricing/', '/billing/']):
            assigned_role = 'Finance'
        elif any(token in lower_url for token in ['/admin/', '/internal/']):
            assigned_role = 'Admin'
        else:
            assigned_role = 'Public'
        
        # Skip if we already stored this doc_id in this crawl batch
        if doc_id in crawl_session_ids:
            continue

        existing = existing_map.get(doc_id)
        if existing:
            if existing.content_hash == content_hash and existing.allowed_roles == assigned_role:
                crawl_session_ids.add(doc_id)
                continue
            existing.title = title
            existing.content = content_text
            existing.content_hash = content_hash
            existing.url = url
            existing.version += 1
            existing.allowed_roles = assigned_role
            existing.indexing_status = IndexingStatus.PENDING.value
            existing.updated_at = datetime.now(timezone.utc)
            pages_stored += 1
        else:
            db_doc = DBDocument(
                id=doc_id,
                int_id=next_int_id,
                title=title,
                content=content_text,
                url=url,
                content_hash=content_hash,
                allowed_roles=assigned_role,
                created_at=datetime.now(timezone.utc),
                version=1,
                indexing_status=IndexingStatus.PENDING.value
            )
            new_docs.append(db_doc)
            next_int_id += 1
            pages_stored += 1
        crawl_session_ids.add(doc_id)

    if new_docs:
        session.bulk_save_objects(new_docs)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.logger.warning("Crawl final commit failed: %s", str(e))
        logger.log_crawl(req.url, crawler.stats, time.perf_counter() - t0, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to persist crawled documents")

    if pages_stored > 0:
        # Use the module-level lock so concurrent crawls don't corrupt in-memory index
        with _index_update_lock:
            # Sync index
            from src.core.indexer import IncrementalIndexer
            t_idx = time.perf_counter()
            indexer = IncrementalIndexer(settings.LEXICAL_INDEX_PATH)
            
            dense_indexer = None
            dr = app_state.get("dense_retriever")
            if dr:
                from src.dense.indexer import DenseIndexer
                dense_indexer = DenseIndexer(dr.model, dr.vector_index)
                
            indexer.sync(session, dense_indexer=dense_indexer)
            
            # Reload the lexical index in memory so /search sees new documents
            import pickle
            with open(settings.LEXICAL_INDEX_PATH, 'rb') as f:
                new_index = pickle.load(f)
            se = app_state.get("search_engine")
            if se:
                se.index = new_index
            else:
                from src.core.search import LexicalSearch
                from src.core.tokenizer import Tokenizer
                from src.api.snippets import SnippetGenerator
                from src.hybrid.retriever import HybridRetriever

                tokenizer = Tokenizer()
                se = LexicalSearch(new_index, tokenizer)
                app_state["search_engine"] = se
                if not app_state.get("snippet_generator"):
                    app_state["snippet_generator"] = SnippetGenerator(tokenizer)
                
                dense = app_state.get("dense_retriever")
                if dense:
                    app_state["hybrid_retriever"] = HybridRetriever(se, dense)
                
            logger.log_index(time.perf_counter() - t_idx, {"docs_synced": pages_stored})
            
    logger.log_crawl(req.url, crawler.stats, time.perf_counter() - t0)
            
    return CrawlResponseModel(
        seed_url=req.url,
        pages_crawled=crawler.stats["fetched"],
        pages_stored=pages_stored,
        pages_failed=crawler.stats["failed"],
        max_pages=req.max_pages,
        max_depth=req.max_depth,
        same_domain_only=req.same_domain_only
    )

from fastapi.responses import StreamingResponse
from src.rag.generator import StreamingRAGGenerator

@app.get("/rag/stream")
async def rag_stream(q: str = Query(...), role: str = Query("Public"), domain: Optional[str] = None):
    # 1. Reuse reranked-search logic to get candidates
    search_resp = reranked_search(q=q, role=role, top_k=20, offset=0, domain=domain, candidate_pool_size=50, method="weighted", alpha=0.40)
    
    generator = StreamingRAGGenerator()
    
    # 2. Check CRAG
    if search_resp.get('fallback_triggered', False) or not search_resp.get('results', []):
        return StreamingResponse(generator.fallback_stream(), media_type="text/event-stream")
        
    # 3. Generate Answer
    top_docs = search_resp.get('results', [])[:3]
    return StreamingResponse(generator.generate_stream(q, top_docs), media_type="text/event-stream")
