"""Build a judge input from screen candidates by rejoining to FULL corpus text.

The screen's flagged.jsonl stores msg truncated to 2000 chars, which cuts the
tail that defines the paste-then-continue shape (this truncation caused the
judge's first-pass kappa = -0.20). This rejoins each candidate hash back to the
full first-user-turn content in the corpus parquet, applying the same head+tail
window the judge uses so records stay bounded.

Usage:
    python3 tools/build_judge_input.py \
        --flagged results/wildchat-4.8m-audit.flagged.jsonl \
        --parquet-glob "wildchat-4.8m/data/*.parquet" \
        --id-col conversation_hash --out wildchat_judge_input.jsonl
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path


def window(msg: str, n: int) -> str:
    if len(msg) <= n:
        return msg
    head = int(n * 0.6)
    tail = n - head
    return msg[:head] + "\n\n...[ARTIFACT BODY TRUNCATED]...\n\n" + msg[-tail:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flagged", type=Path, required=True)
    ap.add_argument("--parquet-glob", required=True)
    ap.add_argument("--id-col", default="conversation_hash")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-chars", type=int, default=12000)
    args = ap.parse_args()

    import pyarrow.parquet as pq

    wanted = {}
    for line in open(args.flagged):
        r = json.loads(line)
        wanted[r["hash"]] = r["kind"]
    print(f"{len(wanted)} candidate hashes to recover", file=sys.stderr)

    found: dict[str, str] = {}
    shards = sorted(glob.glob(args.parquet_glob))
    for p in shards:
        if len(found) == len(wanted):
            break
        t = pq.read_table(p, columns=[args.id_col, "conversation"])
        for cid, conv in zip(t[args.id_col].to_pylist(),
                             t["conversation"].to_pylist()):
            if cid in wanted and cid not in found:
                first = next((m for m in conv if m["role"] == "user"), None)
                if first and first["content"]:
                    found[cid] = window(first["content"], args.max_chars)

    with open(args.out, "w") as fh:
        for h, kind in wanted.items():
            if h in found:
                fh.write(json.dumps({"hash": h, "kind": kind,
                                     "msg": found[h]}) + "\n")
    print(f"recovered {len(found)}/{len(wanted)} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
