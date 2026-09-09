"""Is the vector/embedding detector actually good? Measure it on the gold set.

Tests whether dense embeddings separate genuine from not_genuine SEAM-shape
messages, using the 50 human-labeled screen-positives. Leave-one-out kNN
(cosine) gives a classifier; ROC-AUC gives the ranking quality if the vector
score is used as a soft filter. Compared against the trivial screen baseline
(every screen-positive predicted genuine).

Scope: these 50 are all screen-POSITIVE, so this measures the embedding's
ability to RERANK/FILTER screen output, not its recall of shapes the screen
missed. Recall needs a separately labeled random sample.

Usage:
    python3 tools/wild_vector_eval.py --in judge_gold.jsonl --model BAAI/bge-m3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--model", default="BAAI/bge-m3")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--max-chars", type=int, default=8000)
    args = ap.parse_args()

    records = [json.loads(l) for l in open(args.inp) if l.strip()]
    texts = [r["msg"][:args.max_chars] for r in records]
    y = np.array([r["gold"] == "genuine" for r in records])
    n = len(records)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    emb = model.encode(texts, normalize_embeddings=True, batch_size=16,
                       show_progress_bar=False)
    emb = np.asarray(emb)

    sim = emb @ emb.T
    np.fill_diagonal(sim, -1.0)  # exclude self from neighbors

    scores = np.zeros(n)
    preds = np.zeros(n, dtype=bool)
    for i in range(n):
        nn = np.argsort(-sim[i])[:args.k]
        frac = y[nn].mean()
        scores[i] = frac
        preds[i] = frac >= 0.5

    acc = (preds == y).mean()
    baseline = y.mean()  # predict-all-genuine on screen positives

    try:
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(y, scores)
    except Exception as e:
        auc = float("nan")
        print("AUC unavailable:", e)

    tp = int(((preds) & (y)).sum())
    tn = int(((~preds) & (~y)).sum())
    fp = int(((preds) & (~y)).sum())
    fn = int(((~preds) & (y)).sum())

    print(f"\n=== vector detector ({args.model}, LOO k={args.k}, n={n}) ===")
    print(f"embedding dim: {emb.shape[1]}")
    print(f"kNN accuracy {acc:.3f}  vs screen-baseline {baseline:.3f} "
          f"(predict-all-genuine)")
    print(f"ROC-AUC (rank genuine above not_genuine): {auc:.3f}")
    print(f"confusion: TP={tp} TN={tn} FP={fp} FN={fn}")
    print("interpretation: AUC~0.5 => embeddings do NOT capture the structural "
          "distinction (expected, they rank by topic); AUC>>0.5 => vector "
          "filter has real signal and belongs in the cascade.")


if __name__ == "__main__":
    main()
