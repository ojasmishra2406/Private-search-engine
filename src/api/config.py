import os
import json
from typing import List

class Settings:
    # Environment
    ENV: str = os.getenv("APP_ENV", "development")
    
    # Paths
    DB_PATH: str = os.getenv("DB_PATH", "sqlite:///search.db")
    LEXICAL_INDEX_PATH: str = os.getenv("LEXICAL_INDEX_PATH", "index.pkl")
    DENSE_INDEX_PATH: str = os.getenv("DENSE_INDEX_PATH", "dense.index")
    DENSE_MAP_PATH: str = os.getenv("DENSE_MAP_PATH", "dense_map.pkl")
    CACHE_DIR: str = os.getenv("HF_HOME", "hf_cache")
    
    # Models
    DENSE_MODEL_NAME: str = os.getenv("DENSE_MODEL_NAME", "all-MiniLM-L6-v2")
    CROSS_ENCODER_MODEL_NAME: str = os.getenv("CROSS_ENCODER_MODEL_NAME", "ms-marco-TinyBERT-L-2-v2")
    
    # Security & CORS
    _cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", '["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]')
    try:
        CORS_ALLOW_ORIGINS: List[str] = json.loads(_cors_origins_raw)
    except:
        CORS_ALLOW_ORIGINS = ["http://localhost:5173"]

    # API Limits
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "500"))
    MAX_TOP_K: int = int(os.getenv("MAX_TOP_K", "100"))
    MAX_CANDIDATE_POOL: int = int(os.getenv("MAX_CANDIDATE_POOL", "500"))
    MAX_OFFSET: int = int(os.getenv("MAX_OFFSET", "10000"))

settings = Settings()
