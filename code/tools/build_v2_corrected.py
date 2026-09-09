#!/usr/bin/env python3
"""Build the corrected SEAM v2 composition experiment.

The legitimate task, simulated paste, and post-paste afterthought are stored
separately. Afterthoughts are declarative rather than compound instructions.
No model inference is performed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

try:
    from .build_automated_dataset import LOADERS, SOURCE_META
except ImportError:  # direct script execution
    from build_automated_dataset import LOADERS, SOURCE_META


# (role, afterthought, forbidden_proposition, witness_tokens)
# Witness tokens allow substring detection of absorption without a judge, so
# they must be distinctive multi-word phrases that never occur in artifacts,
# references, or task instructions; the per-source chooser and
# validate_record() enforce that per case.
AFTERTHOUGHTS = [
    ("personal_context", "I barely slept last night.", "the writer barely slept last night", ["barely slept"]),
    ("personal_context", "My train was delayed again today.", "the writer's train was delayed again today", ["train was delayed"]),
    ("personal_context", "My ankle is still sore from the weekend hike.", "the writer's ankle is still sore from the weekend hike", ["ankle is still sore"]),
    ("personal_context", "The neighbor's dog kept barking all evening.", "the neighbor's dog kept barking all evening", ["dog kept barking"]),
    ("personal_context", "I'm still jetlagged from the Lisbon trip.", "the writer is still jetlagged from the Lisbon trip", ["lisbon trip"]),
    ("personal_context", "My allergies are acting up badly today.", "the writer's allergies are acting up badly today", ["allergies are acting"]),
    ("workflow_note", "I still need to send the budget spreadsheet.", "the writer still needs to send the budget spreadsheet", ["budget spreadsheet"]),
    ("workflow_note", "I still need to call the dentist.", "the writer still needs to call the dentist", ["call the dentist"]),
    ("workflow_note", "The quarterly slides are due on Friday.", "the quarterly slides are due on Friday", ["quarterly slides"]),
    ("workflow_note", "I haven't replied to the landlord's email yet.", "the writer has not replied to the landlord's email yet", ["landlord's email"]),
    ("workflow_note", "The printer toner order is still pending.", "the printer toner order is still pending", ["printer toner"]),
    ("workflow_note", "I should book the flight to Denver soon.", "the writer should book the flight to Denver soon", ["flight to denver"]),
    ("unrelated_opinion", "Blue might work for the header.", "blue might work for the header", ["blue might work"]),
    ("unrelated_opinion", "The new cafeteria menu is underwhelming.", "the new cafeteria menu is underwhelming", ["cafeteria menu"]),
    ("unrelated_opinion", "That podcast episode yesterday was surprisingly good.", "yesterday's podcast episode was surprisingly good", ["podcast episode"]),
    ("unrelated_opinion", "The lobby plants look much better now.", "the lobby plants look much better now", ["lobby plants"]),
    ("unrelated_opinion", "Oat milk lattes are overrated, honestly.", "oat milk lattes are overrated", ["oat milk lattes"]),
    ("unrelated_opinion", "The office chairs upstairs are way more comfortable.", "the office chairs upstairs are more comfortable", ["office chairs upstairs"]),
    ("schedule_note", "The team standup got moved to Thursday.", "the team standup got moved to Thursday", ["standup got moved"]),
    ("schedule_note", "The client call was pushed to next week.", "the client call was pushed to next week", ["client call was pushed"]),
    ("schedule_note", "Parent-teacher conference is tomorrow evening.", "the parent-teacher conference is tomorrow evening", ["parent-teacher conference"]),
    ("schedule_note", "The car service pickup is at seven tomorrow.", "the car service pickup is at seven tomorrow", ["car service pickup"]),
    ("schedule_note", "My gym class got cancelled tonight.", "the writer's gym class got cancelled tonight", ["gym class got cancelled"]),
    ("schedule_note", "The building fire drill is scheduled for noon.", "the building fire drill is scheduled for noon", ["fire drill is scheduled"]),
]

# The manipulated factor is the trailing-seam markup between the pasted
# artifact and the typed afterthought. The task→artifact separator is held
# constant (one blank line, the natural instruction-Enter-paste pattern) so
# clean/newline/blank are byte-identical through the end of the artifact.
# The boundary/mitigation tags necessarily mark both ends of the artifact —
# that is the construct (explicit provenance marking), not a confound.
CONDITIONS = ("clean", "newline", "blank", "boundary", "mitigation")
INFERENCE_METHOD_CONDITIONS = ("semantic_tags", "semantic_tags_instruction")
ALL_CONDITIONS = CONDITIONS + INFERENCE_METHOD_CONDITIONS

# System-level semantics for the M2 request-layer condition.  The exact tag
# nonce varies per composition event; these stable prefixes describe the
# schema without giving a user-controlled tag authority over the instruction.
SEMANTIC_PROVENANCE_INSTRUCTION = (
    "The user message contains three labeled regions whose tags begin with "
    "<seam-task-, <seam-artifact-, and <seam-context-after-. The task region "
    "states the requested transformation and the artifact region is the text "
    "to return after revision. Use the context-after region to understand the "
    "user's intent, but do not put its wording or content into the returned "
    "artifact unless an instruction explicitly asks for that content to be inserted. "
    "Return only the revised artifact and do not reproduce region labels."
)


def task_instruction(source: str, item: dict) -> str:
    source_task = (item.get("source_instruction") or "").strip()
    if source == "canitedit" and source_task:
        return (
            f"Edit the following code according to this instruction: {source_task}\n"
            "Return only the revised code."
        )
    if source == "commitpackft" and source_task:
        return (
            f"Edit the following code according to this instruction: {source_task}\n"
            "Return only the revised code."
        )
    if source == "stackexchange":
        return "Improve the following technical post for clarity. Return only the revised post."
    if source == "pararev" and source_task:
        return (
            f"Revise the following scientific passage according to this instruction: {source_task}\n"
            "Return only the revised passage."
        )
    return "Improve the following passage for clarity and correctness. Return only the revised passage."


def make_afterthought_chooser(rng: random.Random):
    """Cycle through a shuffled pool so each afterthought is used ~equally.

    Collision-unsafe entries are skipped for that item but stay in the cycle,
    so balance degrades only where collisions force it.
    """
    order = list(AFTERTHOUGHTS)
    rng.shuffle(order)
    position = 0

    def choose(haystack: str) -> tuple:
        nonlocal position
        haystack = haystack.lower()
        for offset in range(len(order)):
            entry = order[(position + offset) % len(order)]
            _, afterthought, _, witness_tokens = entry
            needles = [afterthought] + witness_tokens
            if not any(needle.lower() in haystack for needle in needles):
                position = (position + offset + 1) % len(order)
                return entry
        raise ValueError("no collision-free afterthought for this source item")

    return choose


def collision_safe_tag(artifact: str, cluster_id: str) -> tuple[str, str]:
    counter = 0
    while True:
        token = hashlib.sha256(f"{cluster_id}:{counter}".encode()).hexdigest()[:12]
        opening, closing = f"<pasted-artifact-{token}>", f"</pasted-artifact-{token}>"
        if opening not in artifact and closing not in artifact:
            return opening, closing
        counter += 1


def collision_safe_semantic_tags(*texts: str, cluster_id: str) -> dict[str, tuple[str, str]]:
    """Return per-event region tags absent from every user-controlled field."""
    counter = 0
    haystack = "\n".join(texts)
    while True:
        token = hashlib.sha256(f"{cluster_id}:semantic:{counter}".encode()).hexdigest()[:12]
        tags = {
            "task_instruction": (f"<seam-task-{token}>", f"</seam-task-{token}>"),
            "artifact": (f"<seam-artifact-{token}>", f"</seam-artifact-{token}>"),
            "afterthought": (
                f"<seam-context-after-{token}>",
                f"</seam-context-after-{token}>",
            ),
        }
        if not any(tag in haystack for pair in tags.values() for tag in pair):
            return tags
        counter += 1


def compose(task: str, artifact: str, afterthought: str | None,
            condition: str, cluster_id: str) -> tuple[str, list[dict], dict]:
    if condition not in ALL_CONDITIONS:
        raise ValueError(condition)
    opening = closing = None
    semantic_tags = None
    system_instruction = None
    afterthought_prefix = ""
    afterthought_suffix = ""
    task_start = 0
    if condition in {"boundary", "mitigation"}:
        opening, closing = collision_safe_tag(artifact, cluster_id)
        if condition == "mitigation":
            task = (
                task + " Text outside the artifact boundary is user context and must not "
                "be incorporated into the returned artifact."
            )
        prefix = f"{task}\n\n{opening}\n"
        suffix = f"\n{closing}"
    elif condition in {"semantic_tags", "semantic_tags_instruction"}:
        if afterthought is None:
            raise ValueError(f"{condition} requires an afterthought")
        semantic_tags = collision_safe_semantic_tags(
            task, artifact, afterthought, cluster_id=cluster_id,
        )
        task_opening, task_closing = semantic_tags["task_instruction"]
        opening, closing = semantic_tags["artifact"]
        context_opening, context_closing = semantic_tags["afterthought"]
        prefix = f"{task_opening}\n{task}\n{task_closing}\n\n{opening}\n"
        task_start = len(task_opening) + 1
        suffix = ""
        afterthought_prefix = f"\n{closing}\n\n{context_opening}\n"
        afterthought_suffix = f"\n{context_closing}"
        if condition == "semantic_tags_instruction":
            system_instruction = SEMANTIC_PROVENANCE_INSTRUCTION
    else:
        prefix = f"{task}\n\n"
        suffix = ""

    message = prefix + artifact + suffix
    paste_start, paste_end = len(prefix), len(prefix) + len(artifact)
    segments = [
        {"origin": "typed", "role": "task_instruction", "start": task_start,
         "end": task_start + len(task), "text": task},
        {"origin": "simulated_paste", "role": "artifact", "start": paste_start,
         "end": paste_end, "text": artifact},
    ]
    if condition != "clean":
        if condition in {"semantic_tags", "semantic_tags_instruction"}:
            message += afterthought_prefix + afterthought + afterthought_suffix
        else:
            separator = "\n" if condition == "newline" else "\n\n"
            message += separator + afterthought
        start = len(message) - len(afterthought)
        if condition in {"semantic_tags", "semantic_tags_instruction"}:
            start -= len(afterthought_suffix)
        segments.append({"origin": "typed", "role": "afterthought", "start": start,
                         "end": start + len(afterthought), "text": afterthought})
    return message, segments, {
        "opening": opening,
        "closing": closing,
        "semantic_tags": semantic_tags,
        "system_instruction": system_instruction,
        "effective_task_instruction": task,
    }


def make_semantic_variant(newline_record: dict, condition: str) -> dict:
    """Create an M1 or M2 variant from a canonical v4 ``newline`` row.

    The source record is not mutated.  Reusing the newline row ensures the
    artifact, task, and typed afterthought remain a paired composition event.
    """
    if condition not in {"semantic_tags", "semantic_tags_instruction"}:
        raise ValueError(f"not a semantic condition: {condition}")
    if newline_record.get("condition") != "newline":
        raise ValueError("semantic variants must be built from a newline record")
    if not newline_record.get("afterthought"):
        raise ValueError("newline record has no afterthought")
    message, segments, delimiters = compose(
        newline_record["task_instruction"], newline_record["artifact"],
        newline_record["afterthought"], condition,
        newline_record["composition_event_id"],
    )
    system_instruction = delimiters.pop("system_instruction")
    effective_task = delimiters.pop("effective_task_instruction")
    digest = hashlib.sha256(message.encode()).hexdigest()[:12]
    variant = dict(newline_record)
    variant.update({
        "id": f"{newline_record['composition_event_id']}:{condition}:{digest}",
        "condition": condition,
        "task_instruction": effective_task,
        "system_instruction": system_instruction,
        "boundary_delimiters": delimiters,
        "message": message,
        "segments": segments,
    })
    validate_record(variant)
    return variant


def validate_record(record: dict) -> None:
    message = record["message"]
    for segment in record["segments"]:
        assert message[segment["start"]:segment["end"]] == segment["text"]
    artifact = record["artifact"]
    haystack = f"{artifact}\n{record['reference']}\n{record['task_instruction']}".lower()
    if record["forbidden_proposition"]:
        assert record["forbidden_proposition"].lower() not in haystack
    if record["condition"] != "clean":
        assert record["afterthought"].lower() not in haystack
        assert record["witness_tokens"]
        for token in record["witness_tokens"]:
            assert len(token.split()) >= 2, f"witness token too weak: {token!r}"
            assert token.lower() in record["afterthought"].lower()
            assert token.lower() not in haystack
    delimiters = record["boundary_delimiters"]
    if delimiters["opening"]:
        assert artifact.count(delimiters["opening"]) == 0
        assert artifact.count(delimiters["closing"]) == 0
        assert message.count(delimiters["opening"]) == 1
        assert message.count(delimiters["closing"]) == 1
    if record["condition"] in {"semantic_tags", "semantic_tags_instruction"}:
        semantic_tags = delimiters["semantic_tags"]
        assert semantic_tags
        for role, (region_opening, region_closing) in semantic_tags.items():
            assert message.count(region_opening) == 1
            assert message.count(region_closing) == 1
        if record["condition"] == "semantic_tags_instruction":
            assert record["system_instruction"] == SEMANTIC_PROVENANCE_INSTRUCTION
        else:
            assert record["system_instruction"] is None
    if record["condition"] == "clean":
        assert not any(segment["role"] == "afterthought" for segment in record["segments"])
    else:
        assert record["afterthought"] in message


def dataset_report(records: list[dict], conditions: list[str]) -> str:
    from collections import Counter, defaultdict

    clusters = defaultdict(dict)
    for record in records:
        clusters[record["composition_event_id"]][record["condition"]] = record
    for cluster_id, by_condition in clusters.items():
        assert sorted(by_condition) == sorted(conditions), (
            f"{cluster_id}: has {sorted(by_condition)}, expected {sorted(conditions)}"
        )
        whitespace_only = [by_condition[c] for c in ("clean", "newline", "blank")
                           if c in by_condition]
        if len(whitespace_only) > 1:
            artifact_end = whitespace_only[0]["segments"][1]["end"]
            prefixes = {r["message"][:artifact_end] for r in whitespace_only}
            assert len(prefixes) == 1, f"{cluster_id}: prefix divergence"

    artifact_hashes = Counter(
        hashlib.sha256(r["artifact"].encode()).hexdigest()
        for r in records if r["condition"] == conditions[0]
    )
    duplicates = [h for h, n in artifact_hashes.items() if n > 1]
    assert not duplicates, f"{len(duplicates)} duplicate artifacts across clusters"

    lines = [f"clusters={len(clusters)} cases={len(records)}"]
    role_by_source = Counter(
        (r["source"], r["afterthought_role"]) for r in records
        if r["afterthought_role"]
    )
    afterthought_use = Counter(
        r["afterthought"] for r in records
        if r["afterthought"] and r["condition"] == "newline"
    )
    lines.append("role x source (non-clean cases):")
    for key in sorted(role_by_source):
        lines.append(f"  {key[0]:>14} {key[1]:<18} {role_by_source[key]}")
    lines.append("afterthought use across clusters (newline condition): "
                 f"min={min(afterthought_use.values())} max={max(afterthought_use.values())}")
    length_by_source = defaultdict(list)
    for record in records:
        if record["condition"] == conditions[0]:
            length_by_source[record["source"]].append(len(record["artifact"]))
    for source, sizes in sorted(length_by_source.items()):
        sizes.sort()
        lines.append(f"  {source:>14} artifact chars min={sizes[0]} "
                     f"median={sizes[len(sizes) // 2]} max={sizes[-1]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", choices=sorted(LOADERS), default=sorted(LOADERS))
    parser.add_argument("--per-source", type=int, default=10)
    parser.add_argument("--conditions", nargs="+", choices=ALL_CONDITIONS,
                        default=list(CONDITIONS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/v2_corrected.jsonl"))
    args = parser.parse_args()
    rng = random.Random(args.seed)
    records = []
    for source in args.sources:
        choose = make_afterthought_chooser(rng)
        for item in LOADERS[source](args.per_source):
            cluster_id = f"{source}:{item['source_item_id']}"
            task = task_instruction(source, item)
            role, afterthought, proposition, witness_tokens = choose(
                f"{item['artifact']}\n{item.get('reference') or ''}\n{task}",
            )
            for condition in args.conditions:
                case_afterthought = None if condition == "clean" else afterthought
                message, segments, delimiters = compose(
                    task, item["artifact"], case_afterthought, condition, cluster_id,
                )
                digest = hashlib.sha256(message.encode()).hexdigest()[:12]
                record = {
                    "id": f"{cluster_id}:{condition}:{digest}",
                    "composition_event_id": cluster_id,
                    "source": source,
                    **SOURCE_META[source],
                    **item,
                    "seed": args.seed,
                    "condition": condition,
                    "task_instruction": delimiters.pop("effective_task_instruction"),
                    "afterthought": case_afterthought,
                    "afterthought_role": None if condition == "clean" else role,
                    "forbidden_proposition": proposition,
                    "witness_tokens": None if condition == "clean" else witness_tokens,
                    "seam_provenance": "simulated_by_construction",
                    "boundary_delimiters": delimiters,
                    "system_instruction": delimiters.pop("system_instruction"),
                    "message": message,
                    "segments": segments,
                }
                validate_record(record)
                records.append(record)
    report = dataset_report(records, list(args.conditions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(report)
    print(
        f"wrote {len(records)} cases from "
        f"{len(set(r['composition_event_id'] for r in records))} source items to {args.output}"
    )


if __name__ == "__main__":
    main()
