"""
Run this once to export ERP data from MySQL and build the ChromaDB vector index.

Usage:
    python scripts/build_index.py              # requires MySQL running
    python scripts/build_index.py --mock       # use hardcoded seed data (no MySQL needed)
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--mock', action='store_true', default=False,
        help='Use hardcoded seed data instead of a live MySQL connection'
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("  Cable TV ERP — RAG Index Builder")
    print("=" * 60)

    if args.mock:
        print("\nStep 1/2: Loading mock ERP data (--mock mode)...")
        from scripts.mock_data import MOCK_CHUNKS
        chunks = MOCK_CHUNKS
        print(f"Loaded {len(chunks)} mock documents across 9 entity types.")
    else:
        print("\nStep 1/2: Exporting ERP data from MySQL...")
        from rag.exporter import export_all_chunks
        chunks = export_all_chunks()

    print(f"\nStep 2/2: Building ChromaDB vector index...")
    from rag.embedder import build_index
    build_index(chunks)

    print("\nDone! You can now run the chatbot or eval suite.")
    print("  - Chatbot:   python app.py  →  http://localhost:5000/chatbot")
    print("  - Dry eval:  python scripts/run_eval.py --dry-run")
    print("  - Full eval: python scripts/run_eval.py  (requires OPENAI_API_KEY)")
    print("=" * 60)


if __name__ == '__main__':
    main()
