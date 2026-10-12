import sys
from scripts.run_real_eval_reranker import evaluate_full_pipeline

if __name__ == '__main__':
    print('RUN 1')
    evaluate_full_pipeline()
    print('RUN 2')
    evaluate_full_pipeline()
