"""
scripts/run_eval.py — Run the RAG eval suite and print accuracy report.

Usage:
    python scripts/run_eval.py                         # full pipeline (needs OPENAI_API_KEY)
    python scripts/run_eval.py --dry-run               # retrieval only, no API call
    python scripts/run_eval.py --top_k 3               # test with different k
    python scripts/run_eval.py --dry-run --top_k 3
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Cable TV ERP RAG eval suite.")
    parser.add_argument(
        '--top_k', type=int, default=5,
        help='Number of documents to retrieve per query (default: 5)'
    )
    parser.add_argument(
        '--dry-run', action='store_true', default=False,
        help='Retrieval only — skip generation and OpenAI API call'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    top_k   = args.top_k
    dry_run = args.dry_run

    print("=" * 60)
    print("  Cable TV ERP — RAG Eval Suite")
    print("=" * 60)
    print(f"  Running RAG eval with top_k={top_k} on 20 questions...")
    if dry_run:
        print("  [DRY RUN] Skipping generation — testing retrieval only.")

    from eval.eval_runner import run_eval
    result = run_eval(top_k=top_k, dry_run=dry_run)

    import json
    from eval.eval_runner import RESULTS_DIR
    latest = os.path.join(RESULTS_DIR, "eval_results_latest.json")
    print(f"  Full results: {os.path.abspath(latest)}")


if __name__ == '__main__':
    main()
