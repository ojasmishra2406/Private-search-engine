import os
import shutil
import pytest
from src.api.config import settings

@pytest.fixture(scope="session", autouse=True)
def isolated_production_artifacts(tmp_path_factory):
    """
    Copy production DB and indexes to a temporary directory 
    and override settings so tests don't mutate the real production state.
    """
    tmp_dir = tmp_path_factory.mktemp("prod_artifacts")
    
    # Original paths
    prod_db = "search.db"
    prod_lexical = "index.pkl"
    prod_dense = "dense.index"
    prod_dense_map = "dense_map.pkl"
    
    # Copy to tmp
    for f in [prod_db, prod_lexical, prod_dense, prod_dense_map]:
        if os.path.exists(f):
            shutil.copy2(f, str(tmp_dir / f))
            
    # Override settings dynamically for the session
    db_path = str(tmp_dir / prod_db)
    db_path = db_path.replace("\\", "/")
    settings.DB_PATH = f"sqlite:///{db_path}"
    
    settings.LEXICAL_INDEX_PATH = str(tmp_dir / prod_lexical)
    settings.DENSE_INDEX_PATH = str(tmp_dir / prod_dense)
    settings.DENSE_MAP_PATH = str(tmp_dir / prod_dense_map)
    
    yield

