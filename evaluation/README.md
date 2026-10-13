# Evaluation data

Everything behind the paper's 4,800-answer evaluation (4 domains × 30 questions × 10 model
configurations × 4 retrieval conditions), released for independent inspection and reproduction.

## Contents

| Path | What it is |
|---|---|
| `question_set.md` | All 120 test questions, with IDs (e.g. `FAB-F-01`) and difficulty tier (Factual / Conceptual-Clinical / Synthesis). |
| `raw_answers/{fabry,ctx,lung_adenocarcinoma,scrna}.json` | The raw, unscored model answers — 1,200 entries each (`question_id`, `codename`, `condition`, `response`, `thinking`, `duration_s`). |
| `codename_map.json` | Maps each blinded codename (`M01`–`M10`) to the real model it refers to. |
| `make_judge_input.py` | The scoring rubric (verbatim, as given to both judges) and the script that builds each question's judge prompt from `raw_answers/`. Run `python make_judge_input.py <QID>` to regenerate the exact prompt sent to the judges for that question. |
| `judge_gpt55/{domain}_scores.txt` | Primary judge (GPT-5.5) scores — one row per (question, codename, condition), accuracy/completeness/clarity + overall. |
| `judge_claude_sonnet55/replies/<QID>.json` | Second, independent blind judge (Claude Sonnet 5.5, run 2026-10-08) — same rubric/codenames, used to check inter-rater reliability. `check_reply.py` validates the reply files and reports within-question score discrimination. |
| `stats_analysis.py` / `stats_results_gpt55.csv` | Every statistical test reported in the paper (paired Wilcoxon signed-rank, Holm-corrected), run on the primary judge's scores. |
| `stats_analysis_claude_judge.py` / `stats_results_claude_sonnet55.csv` | The same statistical tests re-run on the second judge's scores, to check which conclusions replicate. |
| `judge_agreement.py` / `judge_agreement_cells.csv` | Inter-judge agreement (Spearman's rho, quadratic-weighted kappa) between the two judges, overall and broken down by dimension / domain / condition / tier. |
| `AGREEMENT_FINDINGS.md` | Write-up of the inter-judge agreement results: what replicated under both judges and what didn't. |
| `report.md` | The full evaluation report (primary-judge results, methodology, charts). |

## Reproducing the analysis

```bash
pip install pandas numpy scipy statsmodels scikit-learn

python make_judge_input.py FAB-F-01      # regenerate one judge prompt
python stats_analysis.py                 # primary-judge (GPT-5.5) statistics
python stats_analysis_claude_judge.py    # second-judge (Claude Sonnet 5.5) statistics
python judge_agreement.py                # inter-judge agreement
python judge_claude_sonnet55/check_reply.py   # validate the second judge's reply files
```

All scripts are self-contained and read only from this `evaluation/` folder.

## Notes on judging

- Both judges scored the same 4,800 (question, codename, condition) answers blind, using the
  same rubric (`make_judge_input.py`) and the same codenames — neither judge was told which
  real model a codename corresponded to.
- No human ratings were collected for this study; "judge reliability" here means **agreement
  between two independent LLM judges**, not agreement with human raters. Treat findings that
  disagree between the two judges (see `AGREEMENT_FINDINGS.md`) as provisional.
