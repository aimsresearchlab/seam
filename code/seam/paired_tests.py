"""Exact McNemar paired tests for absorption labels.

The repeated-measures design pairs every contrast on the cluster
(`composition_event_id`): each cluster sees all five conditions, so
condition contrasts within a model are within-cluster paired binary
outcomes, and model contrasts on the same condition are paired on the
cluster as well. The right test is McNemar's, exact (binomial on the
discordant pairs) — the discourse-role-labels paper's convention
(arXiv:2606.04109); no scipy needed.

Usage:
    # condition contrasts within one model's labels
    python3 seam/paired_tests.py --labels seam/results/v3-flash-cascade.jsonl

    # same-condition contrasts between two models
    python3 seam/paired_tests.py \
        --labels seam/results/v3-flash-cascade.jsonl \
        --labels-b seam/results/v3-pro-cascade.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CONDITION_CONTRASTS = [
    ("newline", "blank"),        # whitespace quantity (expect ns)
    ("newline", "boundary"),     # markup lever
    ("blank", "boundary"),
    ("boundary", "mitigation"),  # instruction on top of markup
]


def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def load_labels(path: Path) -> dict[tuple[str, str], bool]:
    """{(cluster, condition): absorbed} from a cascade labels JSONL."""
    out = {}
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            out[(row["composition_event_id"], row["condition"])] = row["absorbed"]
    return out


def contrast(labels: dict, key_a, key_b) -> dict:
    """Paired 2x2 for two within-labels keys; keys are (condition,) selectors."""
    b = c = both = neither = 0
    clusters = {k[0] for k in labels}
    for cluster in clusters:
        if (cluster, key_a) not in labels or (cluster, key_b) not in labels:
            continue
        x, y = labels[(cluster, key_a)], labels[(cluster, key_b)]
        if x and not y:
            b += 1
        elif y and not x:
            c += 1
        elif x and y:
            both += 1
        else:
            neither += 1
    n = b + c + both + neither
    return {"n_pairs": n, "a_only": b, "b_only": c, "both": both,
            "rate_a": (b + both) / n if n else 0.0,
            "rate_b": (c + both) / n if n else 0.0,
            "p_exact": exact_mcnemar(b, c)}


def between_models(labels_a: dict, labels_b: dict, condition: str) -> dict:
    """Paired 2x2 for the same condition across two models' labels."""
    b = c = both = neither = 0
    for key, x in labels_a.items():
        if key[1] != condition or key not in labels_b:
            continue
        y = labels_b[key]
        if x and not y:
            b += 1
        elif y and not x:
            c += 1
        elif x and y:
            both += 1
        else:
            neither += 1
    n = b + c + both + neither
    return {"n_pairs": n, "a_only": b, "b_only": c, "both": both,
            "rate_a": (b + both) / n if n else 0.0,
            "rate_b": (c + both) / n if n else 0.0,
            "p_exact": exact_mcnemar(b, c)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--labels-b", type=Path,
                        help="Second model's labels: run same-condition "
                             "between-model contrasts instead.")
    args = parser.parse_args()

    labels = load_labels(args.labels)
    report = {"labels": str(args.labels)}
    if args.labels_b:
        other = load_labels(args.labels_b)
        report["labels_b"] = str(args.labels_b)
        report["between_model"] = {
            cond: between_models(labels, other, cond)
            for cond in ("newline", "blank", "boundary", "mitigation")}
    else:
        report["condition_contrasts"] = {
            f"{a}_vs_{b}": contrast(labels, a, b)
            for a, b in CONDITION_CONTRASTS}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
