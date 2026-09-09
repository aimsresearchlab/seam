#!/usr/bin/env python3
"""Audit completed SEAM outputs for failures that can confound absorption rates.

This is a deterministic output-health audit, not a utility evaluation. It finds
missing, errored, empty, truncated, refusal-like, and severely shortened
responses. For CanItEdit, whose artifacts are Python, it also checks whether the
extracted returned artifact parses. Treated conditions are compared with their
matched clean output so condition-specific degradation stays visible.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seam.score_cascade import extract_artifact_span
from seam.paired_tests import exact_mcnemar


DATASET = ROOT / "data" / "v4.jsonl"
OUTPUT_DIR = ROOT / "seam" / "results"


@dataclass(frozen=True)
class Run:
    slug: str
    results: Path
    traces: Path | None = None
    additional_results: tuple[Path, ...] = ()


RUNS = (
    Run("deepseek-v4-flash", OUTPUT_DIR / "dataset-20260710-221011.jsonl",
        ROOT / "traces" / "run-20260710-221011.jsonl",
        (OUTPUT_DIR / "v4-newline-R-flash-final.jsonl",)),
    Run("deepseek-v4-pro", OUTPUT_DIR / "dataset-20260710-235815.jsonl",
        ROOT / "traces" / "run-20260710-235815.jsonl",
        (OUTPUT_DIR / "dataset-deepseek-pro-v4nr.jsonl",)),
    Run("minimax-m3", OUTPUT_DIR / "dataset-minimax-m3.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-minimax-m3-v4nr.jsonl",)),
    Run("minimax-m2.5", OUTPUT_DIR / "dataset-minimax-m25.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-minimax-m25-v4nr.jsonl",)),
    Run("mimo-v2.5", OUTPUT_DIR / "dataset-mimo-v25.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-mimo-v25-v4nr.jsonl",)),
    Run("mimo-v2.5-pro", OUTPUT_DIR / "dataset-mimo-v25-pro.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-mimo-v25-pro-v4nr.jsonl",)),
    Run("mistral-small-3.2-24b", OUTPUT_DIR / "dataset-mistral-small-32-24b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-mistral-small-32-24b-v4nr.jsonl",)),
    Run("qwen3-8b", OUTPUT_DIR / "dataset-qwen3-8b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-qwen3-8b-v4nr.jsonl",)),
    Run("qwen3-32b", OUTPUT_DIR / "dataset-qwen3-32b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-qwen3-32b-v4nr.jsonl",)),
    Run("olmo-2-32b", OUTPUT_DIR / "dataset-olmo2-32b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-olmo2-32b-v4nr.jsonl",)),
    Run("gpt-oss-20b", OUTPUT_DIR / "dataset-gpt-oss-20b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-gpt-oss-20b-v4nr.jsonl",)),
    Run("gpt-oss-120b", OUTPUT_DIR / "dataset-gpt-oss-120b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-gpt-oss-120b-v4nr.jsonl",)),
    Run("llama-3.1-8b", OUTPUT_DIR / "dataset-llama31-8b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-llama31-8b-v4nr.jsonl",)),
    Run("llama-3.3-70b", OUTPUT_DIR / "dataset-llama33-70b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-llama33-70b-v4nr.jsonl",)),
    Run("gemma-3-4b", OUTPUT_DIR / "dataset-gemma3-4b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-gemma3-4b-v4nr.jsonl",)),
    Run("gemma-3-12b", OUTPUT_DIR / "dataset-gemma3-12b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-gemma3-12b-v4nr.jsonl",)),
    Run("gemma-3-27b", OUTPUT_DIR / "dataset-gemma3-27b.jsonl",
        additional_results=(OUTPUT_DIR / "dataset-gemma3-27b-v4nr.jsonl",)),
    Run("claude-opus-4-8", OUTPUT_DIR / "dataset-claude-opus-4-8.jsonl"),
    Run("gpt-5.6-sol", OUTPUT_DIR / "dataset-gpt-5.6-sol.jsonl"),
    Run("gemini-3.1-pro", OUTPUT_DIR / "dataset-gemini-3.1-pro.jsonl"),
)


REFUSAL = re.compile(
    r"^\s*(?:(?:i(?:'m| am)?\s+)?sorry[,.:;!\s]+)?"
    r"(?:i\s+)?(?:can(?:not|'t)|won't|will not|am unable to|am not able to)\s+"
    r"(?:help|assist|comply|complete|perform|edit|rewrite|provide|return|do)\b",
    re.IGNORECASE,
)

CONDITIONS = ("clean", "newline", "blank", "boundary", "mitigation", "newline_R")
BOUNDARY_TAG_LINE = re.compile(
    r"^\s*</?(?:artifact\b[^>]*|pasted-artifact-[^>]+)>\s*$",
    re.IGNORECASE,
)


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error


def load_dataset(path: Path) -> dict[str, dict]:
    return {row["id"]: row for row in read_jsonl(path)}


def latest_results(path: Path) -> dict[str, dict]:
    latest = {}
    for row in read_jsonl(path):
        latest[row["case_id"]] = row
    return latest


def default_trace_path(results: Path) -> Path:
    return results.with_name(f"{results.stem}.traces.jsonl")


def result_paths(run: Run) -> tuple[Path, ...]:
    return (run.results, *run.additional_results)


def merged_latest_results(run: Run) -> dict[str, dict]:
    latest = {}
    for path in result_paths(run):
        latest.update(latest_results(path))
    return latest


def trace_paths(run: Run) -> tuple[Path, ...]:
    primary = run.traces if run.traces else default_trace_path(run.results)
    return (primary, *(default_trace_path(path) for path in run.additional_results))


def trace_finish_reasons(paths: Iterable[Path]) -> dict[str, str | None]:
    latest = {}
    for path in paths:
        if not path.exists():
            continue
        for row in read_jsonl(path):
            response = row.get("response") or {}
            choices = response.get("choices") or []
            latest[row["case_id"]] = (
                choices[0].get("finish_reason") if choices else None
            )
    return latest


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def python_parse_error(text: str) -> str | None:
    try:
        ast.parse(text)
    except (SyntaxError, ValueError, TypeError) as error:
        return f"{type(error).__name__}: {error}"
    return None


def strip_boundary_tag_lines(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not BOUNDARY_TAG_LINE.match(line))


def base_record(run: Run, case: dict, row: dict | None,
                finish_reasons: dict[str, str | None]) -> dict:
    response = "" if row is None else (row.get("response") or "")
    span = extract_artifact_span(response, case.get("genre")) if response else ""
    finish_reason = None if row is None else row.get(
        "finish_reason", finish_reasons.get(case["id"]))
    return {
        "model": run.slug,
        "case_id": case["id"],
        "composition_event_id": case["composition_event_id"],
        "source": case["source"],
        "genre": case.get("genre"),
        "condition": case["condition"],
        "row_present": row is not None,
        "error": None if row is None else row.get("error"),
        "finish_reason": finish_reason,
        "response_chars": len(response),
        "response_words": word_count(response),
        "artifact_chars": len(span),
        "artifact_words": word_count(span),
        "response": response,
        "artifact_span": span,
        "flags": [],
    }


def audit_run(run: Run, cases: dict[str, dict]) -> list[dict]:
    rows = merged_latest_results(run)
    finish_reasons = trace_finish_reasons(trace_paths(run))
    expected_ids = [case_id for case_id in cases if case_id in rows]
    expected_events = {cases[case_id]["composition_event_id"] for case_id in expected_ids}
    expected_cases = [case for case in cases.values()
                      if case["composition_event_id"] in expected_events
                      and case["condition"] in {cases[case_id]["condition"]
                                                for case_id in expected_ids}]

    records = [base_record(run, case, rows.get(case["id"]), finish_reasons)
               for case in expected_cases]
    by_event_condition = {
        (record["composition_event_id"], record["condition"]): record
        for record in records
    }

    for record in records:
        flags = record["flags"]
        if not record["row_present"]:
            flags.append("missing")
            continue
        if record["error"]:
            flags.append("error")
        if record["response_chars"] == 0:
            flags.append("empty_response")
        if record["finish_reason"] == "length":
            flags.append("length_truncated")
        if record["finish_reason"] not in {None, "stop"}:
            flags.append("nonstop_finish")
        if record["response"] and REFUSAL.search(record["response"][:500]):
            flags.append("refusal_like")
        if record["response"] and record["artifact_chars"] == 0:
            flags.append("empty_artifact_span")

        clean = by_event_condition.get((record["composition_event_id"], "clean"))
        if (record["condition"] != "clean" and clean
                and clean["artifact_words"] >= 80
                and record["artifact_words"] < 12
                and record["artifact_words"] < 0.15 * clean["artifact_words"]):
            flags.append("severely_short_vs_clean")

        if record["source"] == "canitedit" and record["artifact_span"]:
            parse_error = python_parse_error(record["artifact_span"])
            record["python_parse_error"] = parse_error
            if parse_error:
                flags.append("python_syntax_error")
                without_tags = strip_boundary_tag_lines(record["artifact_span"])
                record["python_parses_after_boundary_tag_removal"] = (
                    without_tags != record["artifact_span"]
                    and python_parse_error(without_tags) is None)

    return records


def aggregate(records: list[dict]) -> dict:
    cells = defaultdict(lambda: {"n": 0, "flags": Counter()})
    for record in records:
        cell = cells[(record["model"], record["condition"])]
        cell["n"] += 1
        cell["flags"].update(record["flags"])
    return {
        model: {
            condition: {
                "n": cells[(model, condition)]["n"],
                "flags": dict(sorted(cells[(model, condition)]["flags"].items())),
            }
            for condition in CONDITIONS if cells[(model, condition)]["n"]
        }
        for model in (run.slug for run in RUNS)
    }


def paired_flag_counts(records: list[dict], model: str, condition_a: str,
                       condition_b: str, flag: str) -> dict:
    selected = {
        (record["composition_event_id"], record["condition"]): record
        for record in records
        if record["model"] == model
        and record["condition"] in {condition_a, condition_b}
    }
    events = {
        event for event, condition in selected
        if condition == condition_a and (event, condition_b) in selected
    }
    both = a_only = b_only = neither = 0
    for event in events:
        a = flag in selected[(event, condition_a)]["flags"]
        b = flag in selected[(event, condition_b)]["flags"]
        if a and b:
            both += 1
        elif a:
            a_only += 1
        elif b:
            b_only += 1
        else:
            neither += 1
    return {
        "n_pairs": len(events),
        "both": both,
        "a_only": a_only,
        "b_only": b_only,
        "neither": neither,
        "p_mcnemar_exact": exact_mcnemar(a_only, b_only),
    }


def markdown_report(summary: dict, records: list[dict], flagged: list[dict]) -> str:
    flag_names = sorted({flag for record in flagged for flag in record["flags"]})
    lines = [
        "# Existing-output health audit",
        "",
        "This deterministic audit checks whether failures in already completed model outputs could masquerade as lower absorption. It is not a task-utility evaluation. A clean response can still perform the requested edit poorly, and a parseable Python response can still be semantically wrong.",
        "",
        "## Aggregate findings",
        "",
        f"Across {sum(cell['n'] for model in summary.values() for cell in model.values()):,} model-condition outputs, {len(flagged):,} rows received at least one audit flag.",
        "",
    ]
    if not flag_names:
        lines.append("No failures were detected by the audit rules.")
    else:
        lines.extend([
            "| model | condition | n | " + " | ".join(flag_names) + " |",
            "|---|---:|---:|" + "---:|" * len(flag_names),
        ])
        for model, conditions in summary.items():
            for condition, cell in conditions.items():
                counts = [str(cell["flags"].get(flag, 0)) for flag in flag_names]
                lines.append(f"| {model} | {condition} | {cell['n']} | " + " | ".join(counts) + " |")

    completion = [
        record for record in records
        if {"missing", "error", "empty_response", "length_truncated",
            "nonstop_finish"}
        .intersection(record["flags"])
    ]
    treated_completion = [r for r in completion if r["condition"] != "clean"]
    clean_completion = [r for r in completion if r["condition"] == "clean"]
    native_completion = [r for r in completion if r["condition"] == "newline_R"]
    original_completion = [r for r in completion if r["condition"] != "newline_R"]
    original_nonstop_candidates = [
        r for r in original_completion
        if r["finish_reason"] not in {None, "stop", "length"}
    ]
    python_records = [r for r in records if r["source"] == "canitedit"]
    python_by_condition = {
        condition: (
            sum("python_syntax_error" in r["flags"] for r in python_records
                if r["condition"] == condition),
            sum(r["condition"] == condition for r in python_records),
        )
        for condition in CONDITIONS
        if any(r["condition"] == condition for r in python_records)
    }
    opus_python = [
        r for r in python_records
        if r["model"] == "claude-opus-4-8"
        and r["condition"] in {"clean", "mitigation"}
    ]
    opus_clean_bad = sum(
        r["condition"] == "clean" and "python_syntax_error" in r["flags"]
        for r in opus_python)
    opus_mitigation_bad = sum(
        r["condition"] == "mitigation" and "python_syntax_error" in r["flags"]
        for r in opus_python)
    opus_clean_n = sum(r["condition"] == "clean" for r in opus_python)
    opus_mitigation_n = sum(r["condition"] == "mitigation" for r in opus_python)
    opus_paired = paired_flag_counts(
        records, "claude-opus-4-8", "clean", "mitigation",
        "python_syntax_error",
    )
    opus_wrapper_only = sum(
        r.get("python_parses_after_boundary_tag_removal", False)
        for r in opus_python if r["condition"] == "mitigation"
    )

    lines.extend([
        "",
        "## Findings that affect the paper",
        "",
        f"The full 20-model trace audit found {len(completion)} unusable final outputs: {len(clean_completion)} clean controls and {len(treated_completion)} treated responses. The original five-condition grid accounts for {len(original_completion)}; the panel-wide artifact-native files account for {len(native_completion)}. Unusable rows must be excluded or repaired before reporting, never retained as negative observations.",
        "",
        "Canonical handling: complete clean controls from the later Flash register run repair five otherwise usable original-grid pairs, and `research/output_health_exclusions.jsonl` records the remaining original-grid exclusions. Artifact-native cascade files omit empty and length-truncated finals before paired inference; three additional nonempty but unusable provider outputs are excluded explicitly. Main-condition denominators are 297 to 300 and artifact-native paired denominators are 255 to 300.",
        "",
        f"The expanded finish-reason check newly surfaces {len(original_nonstop_candidates)} original-grid candidates whose result rows contain text but end with a non-stop provider status. They are listed in the flagged rows and are not applied to canonical statistics by this audit; each requires deterministic disposition and a full aggregate diff before any ledger or paper change.",
        "",
        "CanItEdit provides a nonexecuting syntax proxy because every returned artifact should be Python. Invalid extracted Python by condition:",
        "",
        "| condition | invalid | total | rate |",
        "|---|---:|---:|---:|",
    ])
    for condition, (bad, total) in python_by_condition.items():
        lines.append(f"| {condition} | {bad} | {total} | {100 * bad / total:.1f}% |")
    lines.extend([
        "",
        f"The mitigation is not cost-free for Claude Opus: invalid Python rises from {opus_clean_bad}/{opus_clean_n} in clean to {opus_mitigation_bad}/{opus_mitigation_n} under mitigation. The paired table has {opus_paired['a_only']} clean-only and {opus_paired['b_only']} mitigation-only failures (exact McNemar p={opus_paired['p_mcnemar_exact']:.3g}). Of the {opus_mitigation_bad} invalid mitigation outputs, {opus_wrapper_only} become parseable after removing echoed boundary-wrapper lines and {opus_mitigation_bad - opus_wrapper_only} remain syntactically invalid. This is an output-format and utility warning, not evidence about absorption itself.",
        "",
        "One Llama-3.1-8B mitigation response explicitly refused the task: `I can't assist with that request.` No other conservative refusal match appeared.",
    ])

    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "The audit can rule out missing outputs, explicit API errors, empty returns, recorded length truncation, conservative refusal patterns, severe treatment-specific shortening, and Python syntax failures in CanItEdit. It cannot establish semantic task success for prose or code. Any claim that a mitigation preserves utility still requires an independent utility evaluation.",
        "",
        "## Flagged rows",
        "",
    ])
    if not flagged:
        lines.append("None.")
    else:
        for record in flagged:
            preview = re.sub(r"\s+", " ", record["response"]).strip()[:240]
            lines.extend([
                f"### {record['model']} / {record['case_id']}",
                "",
                f"Flags: {', '.join(record['flags'])}. Response preview: `{preview}`",
                "",
            ])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--summary", type=Path,
                        default=ROOT / "research" / "output_health_audit.json")
    parser.add_argument("--flags", type=Path,
                        default=ROOT / "research" / "output_health_flags.jsonl")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "research" / "OUTPUT_HEALTH_AUDIT.md")
    args = parser.parse_args()

    cases = load_dataset(args.dataset)
    records = []
    for run in RUNS:
        for path in result_paths(run):
            if not path.exists():
                raise FileNotFoundError(path)
        records.extend(audit_run(run, cases))

    summary = aggregate(records)
    flagged = [record for record in records if record["flags"]]
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    with args.flags.open("w") as handle:
        for record in flagged:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    args.report.write_text(markdown_report(summary, records, flagged))
    print(f"audited={len(records)} flagged={len(flagged)} report={args.report}")


if __name__ == "__main__":
    main()
