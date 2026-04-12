"""
rag/retriever.py — Retrieve top-k relevant documents for a query using ChromaDB.

Uses the same embedding backend (sentence-transformers or TF-IDF fallback) that
was chosen when the index was built.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag.embedder import (
    get_collection, get_tfidf_vectorizer,
    EMBEDDING_MODEL, TFIDF_PATH
)

DEFAULT_TOP_K = 5

# Module-level cache
_st_model   = None
_st_failed  = False   # set to True once we know the ST model isn't available


def _embed_query(query_text):
    """Embed a single query string. Mirrors the backend used at index-build time."""
    global _st_model, _st_failed

    # If TF-IDF vectorizer exists on disk, the index was built with TF-IDF
    tfidf_vec = get_tfidf_vectorizer()
    if tfidf_vec is not None:
        from rag.embedder import _tfidf_embed
        embeddings, _ = _tfidf_embed([query_text], vectorizer=tfidf_vec)
        return embeddings[0]

    # Otherwise try sentence-transformers
    if not _st_failed:
        try:
            if _st_model is None:
                from sentence_transformers import SentenceTransformer
                _st_model = SentenceTransformer(EMBEDDING_MODEL)
            return _st_model.encode([query_text], show_progress_bar=False)[0].tolist()
        except Exception:
            _st_failed = True

    # Last resort: pure TF-IDF even without a saved vectorizer
    # (shouldn't normally happen — means index was built with ST but query env differs)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    import numpy as np
    vec = TfidfVectorizer(max_features=512, sublinear_tf=True, ngram_range=(1, 2))
    matrix = vec.fit_transform([query_text])
    dense = matrix.toarray().astype(np.float32)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (dense / norms)[0].tolist()


def retrieve(query, top_k=DEFAULT_TOP_K):
    """
    Embed the query and return the top_k most relevant documents from ChromaDB.

    Returns a list of dicts:
        { id, text, metadata, distance }
    distance is cosine distance (lower = more similar).
    """
    query_embedding = _embed_query(query)

    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=['documents', 'metadatas', 'distances']
    )

    if not results or not results.get('ids') or not results['ids'][0]:
        return []

    docs = []
    for i in range(len(results['ids'][0])):
        docs.append({
            'id':       results['ids'][0][i],
            'text':     results['documents'][0][i],
            'metadata': results['metadatas'][0][i],
            'distance': results['distances'][0][i],
        })
    return docs


def format_context(retrieved_docs):
    """
    Format a list of retrieved documents into a single context string for the LLM.
    """
    if not retrieved_docs:
        return "No relevant documents found."

    parts = []
    for i, doc in enumerate(retrieved_docs, start=1):
        table = doc['metadata'].get('table', 'unknown')
        parts.append(f"[Document {i} — {table}]\n{doc['text']}")

    return "\n\n".join(parts)
