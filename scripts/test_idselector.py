import time
import faiss
import numpy as np

def main():
    print("Testing IDSelectorArray vs IDSelectorBatch...")
    allowed_ids = np.arange(24000, dtype=np.int64)
    
    t0 = time.perf_counter()
    sel_array = faiss.IDSelectorArray(len(allowed_ids), faiss.swig_ptr(allowed_ids))
    t1 = time.perf_counter()
    
    t2 = time.perf_counter()
    # Let's see if IDSelectorBatch exists
    try:
        sel_batch = faiss.IDSelectorBatch(len(allowed_ids), faiss.swig_ptr(allowed_ids))
        print("IDSelectorBatch supported.")
    except Exception as e:
        print("IDSelectorBatch error:", e)
        
    print("Done")

if __name__ == "__main__":
    main()
