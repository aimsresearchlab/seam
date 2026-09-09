#!/usr/bin/env python3
"""Build simulated-paste SEAM cases from public corpus APIs.

This command makes no model calls. It downloads source rows, chooses artifacts
deterministically, attaches programmatic typed tails, and emits exact segment
offsets plus separator counterfactuals.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SOURCE_META = {
    "coedit": {
        "license": "Apache-2.0",
        "url": "https://huggingface.co/datasets/grammarly/coedit",
        "genre": "prose",
    },
    "iterater": {
        "license": "Apache-2.0",
        "url": "https://huggingface.co/datasets/wanyu/IteraTeR_human_doc",
        "genre": "prose_long",
    },
    "stackexchange": {
        "license": "CC-BY-SA; version must be resolved from item revision date",
        "url": "https://stackoverflow.com/help/licensing",
        "genre": "technical",
    },
    "canitedit": {
        "license": "MIT",
        "url": "https://huggingface.co/datasets/nuprl/CanItEdit",
        "genre": "code",
        "release_partition": "permissive",
    },
    "commitpackft": {
        "license": "MIT dataset; item repository license retained",
        "url": "https://huggingface.co/datasets/bigcode/commitpackft",
        "genre": "code",
        "release_partition": "permissive_review",
    },
    "pararev": {
        "license": "CC-BY-NC-SA-4.0",
        "url": "https://huggingface.co/datasets/taln-ls2n/pararev",
        "genre": "scientific_prose",
        "release_partition": "noncommercial_sharealike",
    },
}

TAILS = [
    ("personal_context", "please clean this up, I barely slept last night", "the writer barely slept last night"),
    ("personal_context", "fix the wording, my train was delayed again today", "the writer's train was delayed again today"),
    ("workflow_note", "make this clearer, I still need to send the budget spreadsheet", "the writer still needs to send the budget spreadsheet"),
    ("unrelated_question", "improve this, do you think blue would work for the header?", "the writer asks whether blue would work for the header"),
    ("personal_context", "edit for clarity, I haven't had coffee yet", "the writer has not had coffee yet"),
    ("workflow_note", "rewrite this, remind me to call the dentist afterward", "the writer wants a reminder to call the dentist afterward"),
]

SEPARATORS = {
    "none": "\n",
    "blank": "\n\n",
    "dashes": "\n\n---\n\n",
    "fence": None,
}


def get_json(url: str, attempts: int = 4) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SEAM-research/0.1"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def clean_text(value: str) -> str:
    value = re.sub(r"<pre><code>(.*?)</code></pre>", r"\n```\n\1\n```\n", value, flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"[ \t]+", " ", html.unescape(value)).strip()


def hf_rows(dataset: str, split: str, limit: int, config: str = "default") -> list[dict]:
    """Fetch up to `limit` rows via the paginated /rows endpoint (100 per page)."""
    rows: list[dict] = []
    while len(rows) < limit:
        params = urllib.parse.urlencode({
            "dataset": dataset, "config": config, "split": split,
            "offset": len(rows), "length": min(100, limit - len(rows)),
        })
        payload = get_json(f"https://datasets-server.huggingface.co/rows?{params}")
        page = [row["row"] for row in payload.get("rows", [])]
        if not page:
            break
        rows.extend(page)
        if len(rows) >= payload.get("num_rows_total", len(rows)):
            break
    return rows[:limit]


def stratified_sample(records: list[dict], limit: int, source: str) -> list[dict]:
    """Pick `limit` records evenly across short/medium/long artifact lengths.

    Deterministic and seed-free: candidates are deduped by artifact hash,
    bucketed by length terciles of the candidate pool, ordered within each
    bucket by a stable hash of the item id, and drawn round-robin.
    """
    unique: dict[str, dict] = {}
    for record in records:
        digest = hashlib.sha256(record["artifact"].encode()).hexdigest()
        unique.setdefault(digest, record)
    candidates = list(unique.values())
    if len(candidates) < limit:
        raise SystemExit(
            f"{source}: only {len(candidates)} unique candidates for limit={limit}; "
            "raise the fetch pool or lower --per-source"
        )
    lengths = sorted(len(r["artifact"]) for r in candidates)
    lo = lengths[len(lengths) // 3]
    hi = lengths[2 * len(lengths) // 3]
    buckets: list[list[dict]] = [[], [], []]
    for record in candidates:
        size = len(record["artifact"])
        buckets[0 if size <= lo else 1 if size <= hi else 2].append(record)
    for bucket in buckets:
        bucket.sort(key=lambda r: hashlib.sha256(
            f"{source}:{r['source_item_id']}".encode()).hexdigest())
    picked: list[dict] = []
    while len(picked) < limit:
        progressed = False
        for bucket in buckets:
            if bucket and len(picked) < limit:
                picked.append(bucket.pop(0))
                progressed = True
        if not progressed:
            break
    return picked


def load_coedit(limit: int) -> list[dict]:
    records = []
    for row in hf_rows("grammarly/coedit", "train", max(limit * 8, 400)):
        src = re.sub(r"^[^:]{3,100}:\s*", "", row["src"], count=1)
        if 80 <= len(src) <= 4000:
            records.append({"source_item_id": str(row["_id"]), "artifact": src,
                            "reference": row.get("tgt"), "operation": "edit"})
    return stratified_sample(records, limit, "coedit")


def load_iterater(limit: int) -> list[dict]:
    records = []
    for row in hf_rows("wanyu/IteraTeR_human_doc", "train", max(limit * 8, 400)):
        src = (row.get("before_revision") or row.get("before_sent")
               or row.get("src") or row.get("source") or "")
        tgt = (row.get("after_revision") or row.get("after_sent")
               or row.get("tgt") or row.get("target"))
        if isinstance(src, str) and 80 <= len(src) <= 6000:
            base_id = str(row.get("doc_id", row.get("id", len(records))))
            revision = row.get("revision_depth")
            item_id = f"{base_id}:revision-{revision}" if revision is not None else base_id
            records.append({"source_item_id": item_id,
                            "artifact": src, "reference": tgt, "operation": "edit"})
    return stratified_sample(records, limit, "iterater")


def load_stackexchange(limit: int) -> list[dict]:
    records = []
    for page in range(1, 5):
        params = urllib.parse.urlencode({
            "site": "stackoverflow", "pagesize": 100, "page": page,
            "order": "desc", "sort": "relevance", "q": "refactor this code",
            "filter": "withbody",
        })
        payload = get_json(f"https://api.stackexchange.com/2.3/search/advanced?{params}")
        for row in payload.get("items", []):
            body = clean_text(row.get("body", ""))
            if 120 <= len(body) <= 6000:
                records.append({"source_item_id": str(row["question_id"]), "artifact": body,
                                "reference": None, "operation": "edit",
                                "canonical_url": row.get("link"),
                                "author": row.get("owner", {}).get("display_name")})
        if not payload.get("has_more"):
            break
    return stratified_sample(records, limit, "stackexchange")


def load_canitedit(limit: int) -> list[dict]:
    records = []
    for row in hf_rows("nuprl/CanItEdit", "test", 200):
        src, tgt = row.get("before", ""), row.get("after")
        if 80 <= len(src) <= 6000:
            records.append({
                "source_item_id": str(row["id"]), "artifact": src,
                "reference": tgt, "operation": "code_edit",
                "source_instruction": row.get("instruction_lazy"),
                "alternate_instruction": row.get("instruction_descriptive"),
                "utility_tests": row.get("tests"), "taxonomy": row.get("taxonomy"),
            })
    return stratified_sample(records, limit, "canitedit")


def load_commitpackft(limit: int) -> list[dict]:
    records = []
    for row in hf_rows("bigcode/commitpackft", "train", max(limit * 12, 600), config="python"):
        src, tgt = row.get("old_contents", ""), row.get("new_contents")
        subject = (row.get("subject") or "").strip()
        if 120 <= len(src) <= 6000 and tgt and src != tgt and 8 <= len(subject) <= 240:
            records.append({
                "source_item_id": f"{row['commit']}:{row.get('old_file')}",
                "artifact": src, "reference": tgt, "operation": "code_edit",
                "source_instruction": subject, "repository_license": row.get("license"),
                "repositories": row.get("repos"), "language": row.get("lang"),
            })
    return stratified_sample(records, limit, "commitpackft")


def load_pararev(limit: int) -> list[dict]:
    records = []
    rows = hf_rows("taln-ls2n/pararev", "train", max(limit * 8, 400),
                   config="pararev_annot_subset")
    for row in rows:
        src, tgt = row.get("parag_1", ""), row.get("parag_2")
        if 120 <= len(src) <= 6000 and tgt:
            instructions = [
                a.get("instruction", "").strip()
                for a in (row.get("annot_1", {}), row.get("annot_2", {}))
                if isinstance(a, dict) and a.get("instruction", "").strip()
            ]
            records.append({
                "source_item_id": str(row["id_paragraph"]), "artifact": src,
                "reference": tgt, "operation": "edit",
                "source_instruction": instructions[0] if instructions else None,
            })
    return stratified_sample(records, limit, "pararev")


LOADERS = {
    "canitedit": load_canitedit,
    "coedit": load_coedit,
    "commitpackft": load_commitpackft,
    "iterater": load_iterater,
    "pararev": load_pararev,
    "stackexchange": load_stackexchange,
}


def compose(artifact: str, tail: str, separator: str) -> tuple[str, list[dict]]:
    if separator == "fence":
        prefix, middle = "Please edit the pasted text.\n\n```\n", "\n```\n"
        final = prefix + artifact + middle + tail
        start = len(prefix)
    else:
        prefix, middle = "", SEPARATORS[separator]
        final = artifact + middle + tail
        start = 0
    paste_end = start + len(artifact)
    typed_start = paste_end + len(middle)
    return final, [
        {"origin": "simulated_paste", "start": start, "end": paste_end},
        {"origin": "simulated_typed", "start": typed_start, "end": len(final)},
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", choices=sorted(LOADERS), default=sorted(LOADERS))
    ap.add_argument("--per-source", type=int, default=10)
    ap.add_argument("--separators", nargs="+", choices=sorted(SEPARATORS), default=["none", "fence"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=Path("data/automated_v0.jsonl"))
    args = ap.parse_args()
    rng = random.Random(args.seed)
    rows = []
    for source in args.sources:
        for item in LOADERS[source](args.per_source):
            role, tail, proposition = rng.choice(TAILS)
            cluster_id = f"{source}:{item['source_item_id']}"
            for separator in args.separators:
                message, segments = compose(item["artifact"], tail, separator)
                digest = hashlib.sha256(message.encode()).hexdigest()[:12]
                rows.append({
                    "id": f"{cluster_id}:{separator}:{digest}",
                    "composition_event_id": cluster_id,
                    "source": source,
                    **SOURCE_META[source],
                    **item,
                    "seam_provenance": "simulated_by_construction",
                    "separator": separator,
                    "typed_tail": tail,
                    "typed_tail_role": role,
                    "forbidden_proposition": proposition,
                    "message": message,
                    "segments": segments,
                })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} cases from {len(rows) // len(args.separators)} source items to {args.output}")


if __name__ == "__main__":
    main()
