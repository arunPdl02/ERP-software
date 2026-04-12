"""
rag/embedder.py — Embed text chunks and store in ChromaDB.

Primary:  sentence-transformers all-MiniLM-L6-v2  (requires network on first run)
Fallback: sklearn TF-IDF vectors                  (offline / no HuggingFace access)

The fallback is selected automatically if the ST model cannot be loaded.
"""

import os
import sys
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
COLLECTION_NAME = "erp_documents"
TFIDF_PATH = os.path.join(os.path.dirname(__file__), '..', 'chroma_db', 'tfidf.pkl')

BATCH_SIZE = 32


def _try_load_st_model():
    """Attempt to load the sentence-transformers model. Returns model or None."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        return model
    except Exception as e:
        print(f"  [!] sentence-transformers unavailable ({type(e).__name__}). "
              "Falling back to TF-IDF embeddings.")
        return None


def _tfidf_embed(texts, vectorizer=None):
    """
    Encode texts using TF-IDF and L2-normalise to unit vectors.
    Returns (embeddings_list, vectorizer).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    import numpy as np

    if vectorizer is None:
        vectorizer = TfidfVectorizer(
            max_features=512,
            sublinear_tf=True,
            ngram_range=(1, 2)
        )
        matrix = vectorizer.fit_transform(texts)
    else:
        matrix = vectorizer.transform(texts)

    dense = matrix.toarray().astype(np.float32)
    # L2-normalise so cosine similarity ~ dot product
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalised = dense / norms
    return normalised.tolist(), vectorizer


def build_index(chunks):
    """
    Embed all chunks and upsert into a persistent ChromaDB collection.
    Re-running this function is safe — it deletes and recreates the collection.
    """
    import chromadb

    os.makedirs(os.path.abspath(CHROMA_PATH), exist_ok=True)

    print(f"Initializing ChromaDB at: {os.path.abspath(CHROMA_PATH)}")
    client = chromadb.PersistentClient(path=os.path.abspath(CHROMA_PATH))

    # Delete existing collection if present
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'.")

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    texts     = [c['text']     for c in chunks]
    ids       = [c['id']       for c in chunks]
    metadatas = [c['metadata'] for c in chunks]

    # --- Try sentence-transformers, fall back to TF-IDF ---
    st_model = _try_load_st_model()

    if st_model is not None:
        print(f"Using sentence-transformers model '{EMBEDDING_MODEL}'.")
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        all_embeddings = []
        for batch_num in range(total_batches):
            start = batch_num * BATCH_SIZE
            end   = min(start + BATCH_SIZE, len(chunks))
            print(f"  Embedding batch {batch_num + 1}/{total_batches} "
                  f"(docs {start + 1}–{end})...")
            embs = st_model.encode(
                texts[start:end], show_progress_bar=False
            ).tolist()
            all_embeddings.extend(embs)
        vectorizer_used = None
    else:
        print(f"Using TF-IDF fallback embeddings (dim=512).")
        all_embeddings, tfidf_vec = _tfidf_embed(texts)
        # Persist the fitted vectorizer so retrieval can reuse it
        with open(TFIDF_PATH, 'wb') as f:
            pickle.dump(tfidf_vec, f)
        print(f"  TF-IDF vectorizer saved to {TFIDF_PATH}")
        vectorizer_used = tfidf_vec

    collection.upsert(
        ids=ids,
        embeddings=all_embeddings,
        documents=texts,
        metadatas=metadatas
    )

    print(f"Index built. {len(chunks)} documents stored in ChromaDB.")
    return collection


def get_collection():
    """
    Return the existing ChromaDB collection.
    Raises RuntimeError if the index hasn't been built yet.
    """
    import chromadb

    chroma_abs = os.path.abspath(CHROMA_PATH)
    if not os.path.exists(chroma_abs):
        raise RuntimeError(
            "ChromaDB index not found. Run 'python scripts/build_index.py' first."
        )

    client = chromadb.PersistentClient(path=chroma_abs)
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME not in existing:
        raise RuntimeError(
            "ChromaDB index not found. Run 'python scripts/build_index.py' first."
        )

    return client.get_collection(COLLECTION_NAME)


def upsert_document(chunk: dict) -> None:
    """
    Add or update a single document in ChromaDB.
    Silently logs and returns on any error — never crashes ERP routes.
    """
    try:
        collection = get_collection()
        tfidf_vec = get_tfidf_vectorizer()
        if tfidf_vec is not None:
            embedding, _ = _tfidf_embed([chunk['text']], vectorizer=tfidf_vec)
            emb = embedding[0]
        else:
            st_model = _try_load_st_model()
            if st_model is None:
                import logging
                logging.warning(f"RAG upsert skipped for {chunk.get('id')}: no embedding backend available.")
                return
            emb = st_model.encode([chunk['text']], show_progress_bar=False)[0].tolist()
        collection.upsert(
            ids=[chunk['id']],
            embeddings=[emb],
            documents=[chunk['text']],
            metadatas=[chunk['metadata']]
        )
    except Exception as e:
        import logging
        logging.warning(f"RAG upsert failed for {chunk.get('id')}: {e}")


def delete_document(document_id: str) -> None:
    """
    Remove a document from ChromaDB by ID.
    Silently logs and returns on any error — never crashes ERP routes.
    """
    try:
        collection = get_collection()
        collection.delete(ids=[document_id])
    except Exception as e:
        import logging
        logging.warning(f"RAG delete failed for {document_id}: {e}")


def get_tfidf_vectorizer():
    """Load the persisted TF-IDF vectorizer (if TF-IDF fallback was used)."""
    if not os.path.exists(TFIDF_PATH):
        return None
    with open(TFIDF_PATH, 'rb') as f:
        return pickle.load(f)
