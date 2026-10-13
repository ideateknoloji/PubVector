#!/usr/bin/env python3
"""
Re-runs every statistical family in stats_analysis.py, unchanged, but on the
second judge's (Claude Sonnet 5.5) scores instead of the primary judge's
(GPT-5.5). Answers: do the paper's substantive conclusions (RAG lift,
embedding comparison, per-model/tier/domain benefit, reasoning mode) hold up
under a different judge, not just "do the raw scores correlate."

Usage:
    python eval/stats_analysis_claude_judge.py
    python eval/stats_analysis_claude_judge.py --csv eval/judge_claude/stats_results_claude_judge.csv
"""

import argparse
from pathlib import Path

import pandas as pd

import stats_analysis as sa
from judge_agreement import load_judge2

EVAL_DIR = Path(__file__).parent


def load_all_claude() -> pd.DataFrame:
    df = load_judge2()
    df["tier"] = df["question_id"].str.extract(r"-([A-Z])-")[0]
    df["model"] = df["codename"].map(sa.CODENAME_MAP)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Write full results table to this CSV path")
    args = parser.parse_args()

    df = load_all_claude()
    print(f"Loaded {len(df)} scored rows (Claude Sonnet 5.5 judge) "
          f"({df['domain'].nunique()} domains x {df['question_id'].nunique()} question_ids "
          f"x {df['codename'].nunique()} codenames x {df['condition'].nunique()} conditions)\n")

    results = sa.run_families(df)
    out = pd.DataFrame(results)
    cols = ["family", "comparison", "n", "n_nonzero", "mean_a", "mean_b", "delta",
            "statistic", "z", "p_raw", "p_holm", "sig_05", "effect_r"]
    out = out[cols]

    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 50)
    for family, group in out.groupby("family", sort=False):
        print(f"── {family} " + "─" * max(1, 60 - len(family)))
        print(group.drop(columns=["family"]).to_string(index=False))
        print()

    if args.csv:
        out.to_csv(args.csv, index=False)
        print(f"Full results written to {args.csv}")


if __name__ == "__main__":
    main()
