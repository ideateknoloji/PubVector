# Second-judge agreement: GPT-5.5 (primary) vs. Claude Sonnet 5.5 (second judge)

Generated 2026-10-08. Second judge scored all 120 questions x 10 models x 4 conditions = 4800
cells (`evaluation/judge_claude/replies/*.json`), same blind rubric/codenames as the primary
judge (`evaluation/judge/*_scores_table.txt`). Scripts: `judge_agreement.py`,
`stats_analysis_claude_judge.py`. Raw merged per-cell table: `judge_agreement_cells.csv`.

## 1. Raw agreement (4800 matched cells)

| | Spearman rho | weighted kappa | mean diff (Claude-GPT) | mean |abs diff| |
|---|---|---|---|---|
| overall (mean of 3 dims) | 0.527 | - | -0.662 | 0.957 |
| accuracy | 0.543 | 0.465 | -0.764 | 1.096 |
| completeness | 0.524 | 0.438 | -0.861 | 1.176 |
| clarity | 0.322 | 0.408 | -0.370 | 0.905 |

- **Moderate rank correlation, moderate weighted-kappa** (Landis & Koch: 0.4-0.6 = moderate).
  Comparable to typical human-vs-human or LLM-vs-LLM judge agreement reported elsewhere; not
  high enough to treat the two judges as interchangeable at the single-cell level.
- **Claude is a systematically harsher judge** — about 0.66 points lower on average on the 1-5
  scale (per dimension: -0.76 accuracy, -0.86 completeness, -0.37 clarity). This is a
  calibration/severity offset, not just noise: it holds in the same direction across every
  domain and condition (see below). Rank ordering is preserved reasonably well; absolute scale
  is not directly comparable between judges.
- Agreement is weakest in the **lung_adenocarcinoma domain** (rho=0.24, far below the other
  three domains at 0.64-0.69) and in the **Synthesis tier** (rho=0.42, vs. 0.53-0.56 for
  Factual/Conceptual).

## 2. Do the paper's statistical conclusions replicate under the second judge?

Re-ran every family in `stats_analysis.py` on the Claude-judge data
(`judge_claude/stats_results_claude_judge.csv`), unchanged methodology (paired Wilcoxon +
Holm correction).

**Replicates (same direction, significant in both):**
- RAG > no-RAG, pooled over all domains/models, for all 3 embedding conditions (Family 1).
- RAG lift is significant for every one of the 10 models individually (Family 3) — though
  *which* embedding condition is each model's best differs between judges in 6/10 cases.
- RAG > no-RAG for every tier (Factual/Conceptual/Synthesis) and every domain (Families 4-5).
- qwen3.5:0.8b's reasoning mode catastrophically *hurting* performance (think=on vs off,
  delta -1.87 under GPT-5.5, -1.94 under Claude, both p<1e-19) — the paper's most dramatic
  single-model finding is robust.

**Does NOT replicate — flag in limitations:**
- **"rag_pubmedbert is the best embedding overall" (Family 2).** Under GPT-5.5, pubmedbert
  beats both BGE variants significantly (p<0.001). Under Claude, none of the three pairwise
  embedding comparisons are significant (p_holm 0.92-1.0). The RAG-vs-no-RAG effect is robust;
  the specific "pubmedbert wins" ranking is judge-dependent and should be softened.
- **"BGE embeddings degrade performance in the lung_adenocarcinoma domain" (Family 5b).**
  Under GPT-5.5 this is the paper's headline domain-specific caveat: bge_small and bge_large
  both score *significantly worse* than no_rag in this domain (delta -0.15, -0.24, both
  significant), while pubmedbert still helps (+0.54). Under Claude, **all three** RAG
  conditions score *significantly better* than no_rag in this domain (+0.52, +0.57, +0.61,
  all p<0.001) — the opposite conclusion. This specific claim does not survive a second judge
  and should be either removed or explicitly caveated as judge-dependent.
- Reasoning-mode effects for qwen3:1.7b and deepseek-r1:1.5b are small and inconsistent in
  sign/significance across judges (qwen3: GPT +0.30 sig vs Claude -0.04 barely-sig;
  deepseek: GPT -0.07 n.s. vs Claude -0.13 sig) — treat these two as fragile/not robust,
  unlike the qwen3.5 finding above.

## 3. Recommended manuscript changes

1. Add a "Second judge / inter-rater reliability" paragraph to Methods or a new Limitations
   subsection, reporting the rho/kappa numbers in §1 and stating the judge model + date
   (Claude Sonnet 5.5, 2026-10-08) alongside the primary judge (GPT-5.5).
2. Soften or remove the "pubmedbert is the best embedding" claim, or explicitly note it did
   not replicate under the second judge.
3. Soften or remove the "BGE degrades performance in lung_adenocarcinoma" claim, or explicitly
   flag it as not replicating — this is the single largest judge disagreement found and
   directly answers the reviewer's concern about single-judge reliability.
4. Keep the RAG-vs-no-RAG headline finding and the qwen3.5 reasoning-mode finding as-is —
   both are robust across judges.
