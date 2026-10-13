#!/usr/bin/env python3
"""Validate second-judge (Claude Sonnet 5.5) replies saved in judge_claude_sonnet55/replies/<QID>.json.

Checks each reply is a JSON array of 40 entries (10 codenames x 4 conditions),
with integer scores 1-5, and reports per-(codename, condition) variance across
the questions scored so far (the reliability check used in the report).

Usage: python judge_claude_sonnet55/check_reply.py
"""
import json, statistics, sys
from pathlib import Path

HERE = Path(__file__).parent
CONDITIONS = {"no_rag", "rag_bge_small", "rag_bge_large", "rag_pubmedbert"}
CODENAMES = {f"M{i:02d}" for i in range(1, 11)}
DIMS = ["accuracy", "completeness", "clarity"]

ok, bad, scores = [], [], {}
for f in sorted((HERE / "replies").glob("*.json")):
    qid = f.stem
    try:
        arr = json.loads(f.read_text(encoding="utf-8"))
        assert isinstance(arr, list) and len(arr) == 40, f"{len(arr) if isinstance(arr, list) else 'not a list'} entries"
        pairs = {(e["codename"], e["condition"]) for e in arr}
        assert pairs == {(c, k) for c in CODENAMES for k in CONDITIONS}, "codename/condition set mismatch"
        for e in arr:
            for d in DIMS:
                assert isinstance(e[d], int) and 1 <= e[d] <= 5, f"bad {d}={e[d]!r} for {e['codename']}/{e['condition']}"
        ok.append(qid)
        for e in arr:
            scores.setdefault((e["codename"], e["condition"]), []).append(e["accuracy"] + e["completeness"] + e["clarity"])
    except (json.JSONDecodeError, AssertionError, KeyError, TypeError) as exc:
        bad.append((qid, str(exc)))

print(f"valid replies: {len(ok)}   invalid: {len(bad)}")
for qid, why in bad:
    print(f"  INVALID {qid}: {why}")
MIN_Q_FOR_RELIABILITY_CHECK = 10  # the report used 30; below this the stat is noise

if scores:
    n_q = len(ok)
    var = [statistics.pvariance(v) for v in scores.values() if len(v) > 1]
    if n_q < MIN_Q_FOR_RELIABILITY_CHECK:
        print(f"(reliability variance check needs >= {MIN_Q_FOR_RELIABILITY_CHECK} questions, "
              f"have {n_q} - skipping; see within-reply spread below instead)")
    elif var:
        print(f"per-(codename, condition) overall-variance across {n_q} questions: "
              f"median {statistics.median(var):.2f}, zero-variance pairs: {sum(v == 0 for v in var)}/{len(var)}")

# Within-reply spread is meaningful even with few questions: catches a judge that
# scores everything the same within a single question (bulk pattern-matching).
for qid in ok:
    arr = json.loads((HERE / "replies" / f"{qid}.json").read_text(encoding="utf-8"))
    sums = [e["accuracy"] + e["completeness"] + e["clarity"] for e in arr]
    print(f"{qid}: within-question distinct scores {len(set(sums))}/40, range {min(sums)}-{max(sums)}")
