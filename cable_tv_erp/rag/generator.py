"""
rag/generator.py — Generate answers using OpenAI GPT-4o-mini with retrieved context.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from rag.retriever import retrieve, format_context

MODEL = "gpt-4o-mini"
MAX_TOKENS = 512

SYSTEM_PROMPT = """You are a helpful assistant for a Cable TV ERP system. You answer questions about \
customers, subscriptions, invoices, payments, devices, tickets, and inventory.

You are given retrieved context documents from the ERP database below. Use ONLY \
the information in these documents to answer the question. If the answer is not \
contained in the context, say "I don't have enough information to answer that."

Be concise and direct. For numerical questions, give the number first. \
For customer questions, always include the customer's name and ID. \
Do not make up information that is not in the context."""


def _get_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to .env to use generation. "
            "For testing without an API key, use --dry-run mode."
        )
    return OpenAI(api_key=api_key)


def generate_answer(query, context_str):
    """
    Call OpenAI API with the system prompt and retrieved context.
    Returns the assistant's reply as a plain string.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context_str}\n\nQuestion: {query}"}
        ]
    )
    return response.choices[0].message.content


def rag_query(query, top_k=5):
    """
    Full RAG pipeline: retrieve → format context → generate answer.

    Returns:
        {
            "query":          str,
            "answer":         str,
            "retrieved_docs": list[dict],
            "context_str":    str
        }
    """
    retrieved_docs = retrieve(query, top_k=top_k)

    if not retrieved_docs:
        return {
            "query":          query,
            "answer":         "No relevant information found in the ERP database.",
            "retrieved_docs": [],
            "context_str":    ""
        }

    context_str = format_context(retrieved_docs)
    answer = generate_answer(query, context_str)

    return {
        "query":          query,
        "answer":         answer,
        "retrieved_docs": retrieved_docs,
        "context_str":    context_str
    }
