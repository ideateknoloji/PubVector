#!/usr/bin/env python3
"""
Statistical analysis of PubVector LLM-judge scores (eval/judge/*_scores_table.txt).

Recomputes every quantitative claim in the paper's Conclusions section with
real paired non-parametric tests instead of asserted p-values: RAG vs no-RAG,
embedding model comparison, per-model RAG lift, per-tier benefit, per-domain
benefit, and reasoning mode on/off. All comparisons are paired by
(domain, question_id, codename) since the same question was answered by the
same model under every condition (repeated-measures design), which is why
Wilcoxon signed-rank (not an unpaired t-test) is the correct test. Each family
of related comparisons is corrected for multiple comparisons with Holm's
method.

Usage:
    python eval/stats_analysis.py
    python eval/stats_analysis.py --csv eval/stats_results.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from statsmodels.stats.multitest import multipletests

EVAL_DIR = Path(__file__).parent
JUDGE_DIR = EVAL_DIR / "judge_gpt55"

DOMAIN_FILES = {
    "fabry": JUDGE_DIR / "fabry_scores.txt",
    "ctx": JUDGE_DIR / "ctx_scores.txt",
    "lung_adenocarcinoma": JUDGE_DIR / "lung_adenocarcinoma_scores.txt",
    "scrna": JUDGE_DIR / "scrna_scores.txt",
}

CONDITIONS = ["no_rag", "rag_bge_small", "rag_bge_large", "rag_pubmedbert"]
RAG_CONDITIONS = ["rag_bge_small", "rag_bge_large", "rag_pubmedbert"]
TIER_NAMES = {"F": "Factual", "C": "Conceptual/Clinical", "S": "Synthesis"}

CODENAME_MAP = {
    "M01": "qwen2.5:1.5b", "M02": "ministral-3:3b", "M03": "smollm:360m",
    "M04": "deepseek-r1:1.5b (think=off)", "M05": "qwen3:1.7b (think=off)",
    "M06": "qwen3.5:0.8b (think=on)", "M07": "qwen3.5:0.8b (think=off)",
    "M08": "qwen3:1.7b (think=on)", "M09": "deepseek-r1:1.5b (think=on)",
    "M10": "medgemma1.5:4b",
}

REASONING_PAIRS = [
    ("qwen3:1.7b", "M05", "M08"),
    ("deepseek-r1:1.5b", "M04", "M09"),
    ("qwen3.5:0.8b", "M07", "M06"),
]


def load_domain(domain: str, path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 7 or cells[0] == "question_id" or set(cells[0]) <= {"-", ":"}:
            continue
        qid, codename, condition, _acc, _comp, _clar, overall = cells
        if condition not in CONDITIONS:
            continue
        rows.append({
            "domain": domain, "question_id": qid, "codename": codename,
            "condition": condition, "overall": float(overall),
        })
    return pd.DataFrame(rows)


def load_all() -> pd.DataFrame:
    df = pd.concat([load_domain(d, p) for d, p in DOMAIN_FILES.items()], ignore_index=True)
    df["tier"] = df["question_id"].str.extract(r"-([A-Z])-")[0]
    df["model"] = df["codename"].map(CODENAME_MAP)
    return df


def get_pair(df: pd.DataFrame, cond_a: str, cond_b: str, mask: pd.Series | None = None):
    """Return two aligned arrays of 'overall' scores for cond_a/cond_b, matched
    on (domain, question_id, codename)."""
    d = df if mask is None else df[mask]
    wide = d.pivot_table(index=["domain", "question_id", "codename"],
                          columns="condition", values="overall")
    wide = wide.dropna(subset=[cond_a, cond_b])
    return wide[cond_a].to_numpy(), wide[cond_b].to_numpy()


def paired_test(family: str, label: str, a: np.ndarray, b: np.ndarray) -> dict:
    """Paired Wilcoxon signed-rank test with matched-pairs rank-biserial effect size."""
    diff = a - b
    n = len(a)
    n_nonzero = int((diff != 0).sum())
    if n_nonzero == 0:
        return dict(family=family, comparison=label, n=n, n_nonzero=0,
                     mean_a=round(float(a.mean()), 3), mean_b=round(float(b.mean()), 3),
                     delta=round(float(a.mean() - b.mean()), 3),
                     statistic=np.nan, z=np.nan, p_raw=1.0, effect_r=0.0)
    res = wilcoxon(a, b, zero_method="wilcox", method="approx")
    z = float(res.zstatistic)
    effect_r = abs(z) / np.sqrt(n_nonzero)
    return dict(
        family=family, comparison=label, n=n, n_nonzero=n_nonzero,
        mean_a=round(float(a.mean()), 3), mean_b=round(float(b.mean()), 3),
        delta=round(float(a.mean() - b.mean()), 3),
        statistic=round(float(res.statistic), 1), z=round(z, 3),
        p_raw=float(res.pvalue), effect_r=round(effect_r, 3),
    )


def correct_family(rows: list[dict], method: str = "holm") -> list[dict]:
    if not rows:
        return rows
    pvals = [r["p_raw"] for r in rows]
    reject, p_corr, _, _ = multipletests(pvals, method=method)
    for r, pc, rej in zip(rows, p_corr, reject):
        r["p_holm"] = round(float(pc), 6)
        r["sig_05"] = bool(rej)
    return rows


def run_families(df: pd.DataFrame) -> list[dict]:
    results: list[dict] = []

    # Family 1: RAG vs no-RAG, each embedding condition, pooled over all
    # domains/models/questions (n = 4 domains x 30 questions x 10 models = 1200 pairs).
    fam = []
    for cond in RAG_CONDITIONS:
        a, b = get_pair(df, cond, "no_rag")
        fam.append(paired_test("1_rag_vs_norag", f"{cond} vs no_rag", a, b))
    results += correct_family(fam)

    # Family 2: embedding model comparison, pairwise among the 3 RAG conditions
    # (n = 1200 pairs each).
    fam = []
    pairs = [("rag_pubmedbert", "rag_bge_small"), ("rag_pubmedbert", "rag_bge_large"),
             ("rag_bge_small", "rag_bge_large")]
    for cond_a, cond_b in pairs:
        a, b = get_pair(df, cond_a, cond_b)
        fam.append(paired_test("2_embedding_comparison", f"{cond_a} vs {cond_b}", a, b))
    results += correct_family(fam)

    # Family 3: per-model RAG lift (no_rag vs each model's best mean RAG condition),
    # corrected across the 10 models (n = 120 pairs per model: 4 domains x 30 q).
    fam = []
    for codename, model_label in CODENAME_MAP.items():
        sub_mask = df["codename"] == codename
        means = df[sub_mask & df["condition"].isin(RAG_CONDITIONS)].groupby("condition")["overall"].mean()
        best_cond = means.idxmax()
        a, b = get_pair(df, best_cond, "no_rag", mask=sub_mask)
        fam.append(paired_test("3_per_model_rag_lift", f"{model_label}: {best_cond} vs no_rag", a, b))
    results += correct_family(fam)

    # Family 4: per-tier RAG benefit (best RAG per row's domain/model vs no_rag),
    # using each row's own best-mean condition per domain (approximates paper's
    # "best-performing configuration" framing), corrected across 3 tiers.
    fam = []
    for tier, tier_name in TIER_NAMES.items():
        mask = df["tier"] == tier
        means = df[mask & df["condition"].isin(RAG_CONDITIONS)].groupby("condition")["overall"].mean()
        best_cond = means.idxmax()
        a, b = get_pair(df, best_cond, "no_rag", mask=mask)
        fam.append(paired_test("4_per_tier_benefit", f"{tier_name}: {best_cond} vs no_rag", a, b))
    results += correct_family(fam)

    # Family 5: per-domain RAG benefit (best RAG condition per domain vs no_rag),
    # corrected across 4 domains.
    fam = []
    for domain in DOMAIN_FILES:
        mask = df["domain"] == domain
        means = df[mask & df["condition"].isin(RAG_CONDITIONS)].groupby("condition")["overall"].mean()
        best_cond = means.idxmax()
        a, b = get_pair(df, best_cond, "no_rag", mask=mask)
        fam.append(paired_test("5_per_domain_benefit", f"{domain}: {best_cond} vs no_rag", a, b))
    results += correct_family(fam)

    # Family 5b: embedding conditions within Lung Adenocarcinoma specifically
    # (paper claims BGE variants *degrade* performance there), corrected across 3.
    fam = []
    mask = df["domain"] == "lung_adenocarcinoma"
    for cond in RAG_CONDITIONS:
        a, b = get_pair(df, cond, "no_rag", mask=mask)
        fam.append(paired_test("5b_lung_adenocarcinoma_embeddings", f"{cond} vs no_rag", a, b))
    results += correct_family(fam)

    # Family 6: reasoning mode on vs off, for the 3 models offering both,
    # corrected across 3. Paired by (domain, question_id, condition) since the
    # "codename" differs between the on/off variant of the same model.
    fam = []
    for model_label, off_code, on_code in REASONING_PAIRS:
        wide = df.pivot_table(index=["domain", "question_id", "condition"],
                               columns="codename", values="overall")
        wide = wide.dropna(subset=[off_code, on_code])
        a, b = wide[on_code].to_numpy(), wide[off_code].to_numpy()
        fam.append(paired_test("6_reasoning_mode", f"{model_label}: think=on vs think=off", a, b))
    results += correct_family(fam)

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Write full results table to this CSV path")
    args = parser.parse_args()

    df = load_all()
    print(f"Loaded {len(df)} scored rows "
          f"({df['domain'].nunique()} domains x {df['question_id'].nunique()} question_ids "
          f"x {df['codename'].nunique()} codenames x {df['condition'].nunique()} conditions)\n")

    results = run_families(df)
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
