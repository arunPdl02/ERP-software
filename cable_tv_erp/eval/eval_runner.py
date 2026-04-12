"""
eval/eval_runner.py — Run the RAG eval suite and score results.

Usage:
    from eval.eval_runner import run_eval
    run_eval(top_k=5)
    run_eval(top_k=5, dry_run=True)   # retrieval only, no OpenAI call
"""

import os
import sys
import json
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from eval.ground_truth import GROUND_TRUTH
from rag.retriever import retrieve, format_context

RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')


def _keywords_matched(text, keywords):
    """Return list of keywords found in text (case-insensitive)."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def run_eval(top_k=5, dry_run=False):
    """
    Run all 20 ground truth questions through the RAG pipeline and score results.

    Args:
        top_k:    Number of documents to retrieve per query.
        dry_run:  If True, skip generation (retrieval only, no OpenAI call).

    Returns:
        dict with full results and metrics.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)

    mode = "dry_run" if dry_run else "full"
    results = []
    category_stats = defaultdict(lambda: {"correct": 0, "total": 0})

    total = len(GROUND_TRUTH)
    correct_answers = 0
    retrieval_hits = 0

    print(f"\nRunning {total} questions (top_k={top_k}, mode={mode})...\n")

    for i, q in enumerate(GROUND_TRUTH, start=1):
        qid       = q["id"]
        question  = q["question"]
        keywords  = q["expected_keywords"]
        category  = q["category"]

        print(f"  [{i:02d}/{total}] {qid}: {question[:60]}...", end="", flush=True)

        # --- Retrieval (always runs) ---
        retrieved_docs = retrieve(question, top_k=top_k)
        context_str    = format_context(retrieved_docs)

        # Retrieval hit: any keyword in context?
        retrieval_kw_hits = _keywords_matched(context_str, keywords)
        retrieval_hit     = 1 if retrieval_kw_hits else 0
        retrieval_hits   += retrieval_hit

        # --- Generation (skipped in dry_run) ---
        if dry_run:
            answer          = "[skipped — dry run]"
            answer_correct  = None
            answer_kw_hits  = []
        else:
            from rag.generator import generate_answer
            answer         = generate_answer(question, context_str)
            answer_kw_hits = _keywords_matched(answer, keywords)
            answer_correct = 1 if answer_kw_hits else 0
            correct_answers += answer_correct
            category_stats[category]["correct"] += answer_correct

        category_stats[category]["total"] += 1

        status_char = "✅" if (answer_correct == 1) else ("⏭ " if dry_run else "❌")
        print(f" {status_char}")

        results.append({
            "id":               qid,
            "category":         category,
            "question":         question,
            "expected":         q["expected_answer"],
            "got":              answer,
            "answer_correct":   answer_correct,
            "retrieval_hit":    retrieval_hit,
            "keywords_matched": answer_kw_hits if not dry_run else retrieval_kw_hits,
        })

    # --- Compute metrics ---
    answer_accuracy      = (correct_answers / total * 100) if not dry_run else None
    retrieval_hit_rate   = retrieval_hits / total * 100

    by_category = {}
    for cat, stats in sorted(category_stats.items()):
        if dry_run:
            by_category[cat] = {
                "correct": None,
                "total":   stats["total"],
                "accuracy": None
            }
        else:
            acc = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
            by_category[cat] = {
                "correct":  stats["correct"],
                "total":    stats["total"],
                "accuracy": round(acc, 1)
            }

    # --- Print report ---
    _print_report(
        results=results,
        total=total,
        correct_answers=correct_answers,
        retrieval_hits=retrieval_hits,
        answer_accuracy=answer_accuracy,
        retrieval_hit_rate=retrieval_hit_rate,
        by_category=by_category,
        dry_run=dry_run,
    )

    # --- Save results ---
    timestamp = datetime.now().isoformat(timespec='seconds')
    output = {
        "timestamp":          timestamp,
        "top_k":              top_k,
        "mode":               mode,
        "answer_accuracy":    round(answer_accuracy, 1) if answer_accuracy is not None else None,
        "retrieval_hit_rate": round(retrieval_hit_rate, 1),
        "total_questions":    total,
        "correct_answers":    correct_answers if not dry_run else None,
        "retrieval_hits":     retrieval_hits,
        "by_category":        by_category,
        "results":            results,
    }

    # Timestamped file
    ts_safe = timestamp.replace(":", "-").replace("T", "_")
    fname = os.path.join(RESULTS_DIR, f"eval_results_{ts_safe}.json")
    with open(fname, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    # Always-overwrite latest file
    latest_fname = os.path.join(RESULTS_DIR, "eval_results_latest.json")
    with open(latest_fname, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved to: {fname}")
    print(f"  Latest:           {latest_fname}\n")

    return output


def _print_report(results, total, correct_answers, retrieval_hits,
                  answer_accuracy, retrieval_hit_rate, by_category, dry_run):
    """Print the formatted eval report to console."""
    LINE = "=" * 60
    print(f"\n{LINE}")
    print(f"  RAG EVAL REPORT — Cable TV ERP")
    print(LINE)
    print(f"  Total Questions : {total}")

    if dry_run:
        print(f"  Answer Accuracy : N/A (dry run — retrieval only)")
    else:
        print(f"  Answer Accuracy : {correct_answers}/{total} ({answer_accuracy:.1f}%)")

    print(f"  Retrieval Rate  : {retrieval_hits}/{total} ({retrieval_hit_rate:.1f}%)")

    print(f"\n  By Category:")
    for cat, stats in sorted(by_category.items()):
        if dry_run:
            print(f"  {cat:<15}: {stats['total']} questions (retrieval only)")
        else:
            bar = "█" * stats["correct"] + "░" * (stats["total"] - stats["correct"])
            print(f"  {cat:<15}: {stats['correct']}/{stats['total']}  ({stats['accuracy']:.1f}%)  {bar}")

    print(f"\n  Detailed Results:")
    for r in results:
        if r["answer_correct"] == 1:
            mark = "✅ PASS"
        elif r["answer_correct"] is None:
            # dry run — show retrieval result instead
            mark = "📡 HIT " if r["retrieval_hit"] else "📭 MISS"
        else:
            mark = "❌ FAIL"

        print(f"  [{r['id']}] {mark}  {r['question'][:55]}")
        if r["answer_correct"] == 0:
            print(f"         Expected : {r['expected']}")
            print(f"         Got      : {r['got'][:80]}...")

    print(LINE)
