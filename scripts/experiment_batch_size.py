import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reranker.cross_encoder import CrossEncoderModel

def main():
    model = CrossEncoderModel()
    pairs = [("python dictionary comprehension", "dictionary comprehensions are like list comprehensions")] * 200
    
    print(f"{'Batch':<6} | {'latency (s)':<12}")
    print("-" * 25)
    for b in [8, 16, 32]:
        t0 = time.perf_counter()
        model.predict_batch(pairs, batch_size=b)
        t1 = time.perf_counter()
        print(f"{b:<6} | {t1 - t0:.4f}")

if __name__ == "__main__":
    main()
