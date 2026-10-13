#!/usr/bin/env python3
"""
Inter-judge agreement: primary judge (GPT-5.5, eval/judge/*_scores_table.txt)
vs. second judge (Claude Sonnet 5.5, eval/judge_claude/replies/*.json).

Matches every (domain, question_id, codename, condition) cell scored by both
judges (4800 cells total if both are complete) and reports, overall and
broken down by dimension / domain / condition:
  - Spearman rank correlation (on the 1-5 integer scores and on the
    continuous "overall" = mean of the three dimensions)
  - Quadratic-weighted Cohen's kappa (per dimension, treats 1-5 as ordinal)
  - Exact-agreement % and within-1-point agreement %
  - Mean signed difference (judge2 - judge1) and mean absolute difference

Usage:
    python eval/judge_agreement.py
    python eval/judge_agreement.py --csv eval/judge_agreement_cells.csv
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

EVAL_DIR = Path(__file__).parent
JUDGE1_DIR = EVAL_DIR / "judge_gpt55"
JUDGE2_DIR = EVAL_DIR / "judge_claude_sonnet55" / "replies"

DOMAIN_FILES = {
    "fabry": JUDGE1_DIR / "fabry_scores.txt",
    "ctx": JUDGE1_DIR / "ctx_scores.txt",
    "lung_adenocarcinoma": JUDGE1_DIR / "lung_adenocarcinoma_scores.txt",
    "scrna": JUDGE1_DIR / "scrna_scores.txt",
}

CONDITIONS = ["no_rag", "rag_bge_small", "rag_bge_large", "rag_pubmedbert"]
DIMS = ["accuracy", "completeness", "clarity"]
QID_PREFIX_TO_DOMAIN = {"FAB": "fabry", "CTX": "ctx", "LAC": "lung_adenocarcinoma", "SCRNA": "scrna"}


def load_judge1() -> pd.DataFrame:
    rows = []
    for domain, path in DOMAIN_FILES.items():
        for line in path.read_text().splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 7 or cells[0] == "question_id" or set(cells[0]) <= {"-", ":"}:
                continue
            qid, codename, condition, acc, comp, clar, overall = cells
            if condition not in CONDITIONS:
                continue
            rows.append({
                "domain": domain, "question_id": qid, "codename": codename,
                "condition": condition, "accuracy": float(acc),
                "completeness": float(comp), "clarity": float(clar),
                "overall": float(overall),
            })
    return pd.DataFrame(rows)


def load_judge2() -> pd.DataFrame:
    rows = []
    for f in sorted(JUDGE2_DIR.glob("*.json")):
        qid = f.stem
        prefix = qid.split("-")[0]
        domain = QID_PREFIX_TO_DOMAIN.get(prefix)
        if domain is None:
            print(f"  skip {f.name}: unrecognized question_id prefix")
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, str):
            m = re.search(r"\[.*\]", data, re.DOTALL)
            data = json.loads(m.group()) if m else []
        for e in data:
            if e.get("condition") not in CONDITIONS:
                continue
            acc, comp, clar = e["accuracy"], e["completeness"], e["clarity"]
            rows.append({
                "domain": domain, "question_id": qid, "codename": e["codename"],
                "condition": e["condition"], "accuracy": acc,
                "completeness": comp, "clarity": clar,
                "overall": round((acc + comp + clar) / 3, 3),
            })
    return pd.DataFrame(rows)


def agreement_block(a: pd.Series, b: pd.Series, label: str) -> dict:
    rho, p = spearmanr(a, b)
    diff = b - a
    is_integer_scale = bool(((a % 1 == 0) & (b % 1 == 0)).all())
    return {
        "comparison": label, "n": len(a),
        "spearman_rho": round(float(rho), 3), "spearman_p": p,
        "mean_diff(j2-j1)": round(float(diff.mean()), 3),
        "mean_abs_diff": round(float(diff.abs().mean()), 3),
        "exact_agree_%": round(float((diff == 0).mean() * 100), 1) if is_integer_scale else None,
    }


def kappa_block(a: pd.Series, b: pd.Series, label: str) -> dict:
    # only meaningful on the integer 1-5 per-dimension scores, not the continuous overall
    return {
        "comparison": label, "n": len(a),
        "weighted_kappa": round(float(cohen_kappa_score(a.round().astype(int), b.round().astype(int), weights="quadratic")), 3),
        "within_1pt_%": round(float(((a - b).abs() <= 1).mean() * 100), 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="write the merged per-cell table to this CSV path")
    args = ap.parse_args()

    j1 = load_judge1()
    j2 = load_judge2()
    print(f"judge1 (GPT-5.5) rows: {len(j1)}   judge2 (Claude) rows: {len(j2)}", flush=True)

    merged = j1.merge(j2, on=["domain", "question_id", "codename", "condition"],
                       suffixes=("_j1", "_j2"), how="inner")
    print(f"matched cells: {len(merged)} (expect 4800 if both judges are complete)\n")

    if args.csv:
        merged.to_csv(args.csv, index=False)
        print(f"wrote merged per-cell table -> {args.csv}\n")

    print("=== Overall agreement (all cells) ===")
    print(agreement_block(merged["overall_j1"], merged["overall_j2"], "overall (mean of 3 dims)"))
    for dim in DIMS:
        print(kappa_block(merged[f"{dim}_j1"], merged[f"{dim}_j2"], dim))

    print("\n=== By dimension (Spearman on overall-equivalent, i.e. the raw 1-5 scores) ===")
    for dim in DIMS:
        print(agreement_block(merged[f"{dim}_j1"], merged[f"{dim}_j2"], dim))

    print("\n=== By domain (overall score) ===")
    for domain, sub in merged.groupby("domain"):
        print(agreement_block(sub["overall_j1"], sub["overall_j2"], domain))

    print("\n=== By condition (overall score) ===")
    for condition, sub in merged.groupby("condition"):
        print(agreement_block(sub["overall_j1"], sub["overall_j2"], condition))

    print("\n=== By tier (overall score) ===")
    merged["tier"] = merged["question_id"].str.extract(r"-([A-Z])-")[0]
    for tier, sub in merged.groupby("tier"):
        print(agreement_block(sub["overall_j1"], sub["overall_j2"], tier))


if __name__ == "__main__":
    main()
