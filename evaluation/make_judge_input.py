#!/usr/bin/env python3
"""
Generate a ChatGPT judge prompt for one question.

Usage:
    python eval/make_judge_input.py FAB-F-01
    python eval/make_judge_input.py FAB-F-01 | chatgpt > eval/scores/FAB-F-01.json

Without an argument, prints all question IDs.
"""

import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "raw_answers"  # fabry.json, ctx.json, lung_adenocarcinoma.json, scrna.json

RUBRIC = """\
You are an expert in molecular biology, genomics, bioinformatics, and clinical medicine \
evaluating LLM responses to biomedical and scientific questions.

The dataset covers four domains:
  fabry / ctx / lung_adenocarcinoma  — disease domains (clinical questions)
  scrna                              — single-cell RNA sequencing methodology (technical questions)

Score each response on three dimensions (1–5 each):

  accuracy       — factually correct; no hallucinations or errors
  completeness   — covers all key aspects the question requires
  clarity        — well-structured, concise, and actionable for the domain

Score 1 = poor, 3 = acceptable, 5 = excellent.
For RAG conditions: higher score if the response integrates the retrieved context.
For the scrna domain: judge technical precision, not clinical applicability.
If a response is empty or an error message, score all dimensions 1.

Return ONLY a JSON array — no explanation, no markdown fences, no extra text.
Each element:
  {"codename": "MXX", "condition": "...", "accuracy": N, "completeness": N, "clarity": N}
"""

CONDITIONS_ORDER = ["no_rag", "rag_bge_small", "rag_bge_large", "rag_pubmedbert"]


def load_results() -> list[dict]:
    results = []
    for f in sorted(RESULTS_DIR.glob("*.json")):
        results.extend(json.loads(f.read_text()))
    return results


def make_prompt(question_id: str, results: list[dict]) -> str:
    entries = [r for r in results if r["question_id"] == question_id]
    if not entries:
        sys.exit(f"No results found for question ID: {question_id}")

    question_text = entries[0]["question"]
    disease = entries[0]["disease"]

    # Build response blocks sorted by codename then condition order
    codenames = sorted({e["codename"] for e in entries})
    blocks = []
    for codename in codenames:
        for cond in CONDITIONS_ORDER:
            match = next(
                (e for e in entries if e["codename"] == codename and e["condition"] == cond),
                None,
            )
            if not match:
                continue
            response = match["response"].strip() or "[empty response]"
            blocks.append(
                f"MODEL: {codename} | CONDITION: {cond}\n"
                f"{'-' * 60}\n"
                f"{response}\n"
            )

    responses_block = "\n".join(blocks)

    return (
        f"{RUBRIC}\n"
        f"{'=' * 70}\n"
        f"QUESTION ID: {question_id}  |  DISEASE: {disease}\n"
        f"QUESTION: {question_text}\n"
        f"{'=' * 70}\n\n"
        f"RESPONSES ({len(entries)} total — {len(codenames)} models × {len(CONDITIONS_ORDER)} conditions):\n\n"
        f"{responses_block}\n"
        f"{'=' * 70}\n"
        f"Now output the JSON array scoring all {len(entries)} (MODEL, CONDITION) pairs above.\n"
    )


def main() -> None:
    results = load_results()

    if len(sys.argv) < 2:
        ids = sorted({r["question_id"] for r in results})
        print("\n".join(ids))
        return

    question_id = sys.argv[1].upper()
    print(make_prompt(question_id, results))


if __name__ == "__main__":
    main()
