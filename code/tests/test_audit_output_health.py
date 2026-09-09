from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from audit_output_health import (
    REFUSAL,
    RUNS,
    Run,
    merged_latest_results,
    paired_flag_counts,
    python_parse_error,
    strip_boundary_tag_lines,
    trace_finish_reasons,
    trace_paths,
)


def test_refusal_pattern_requires_inability_to_do_task():
    assert REFUSAL.search("I'm sorry, I can't help rewrite that passage.")
    assert REFUSAL.search("I cannot comply with this request.")
    assert not REFUSAL.search("I'm sorry to hear about the barking dog.")
    assert not REFUSAL.search("I can't decide whether this wording is clear.")


def test_python_parse_error_is_nonexecuting_syntax_check():
    assert python_parse_error("def revised():\n    return 1\n") is None
    assert python_parse_error("def revised(:\n    return 1\n") is not None


def test_boundary_wrapper_lines_can_be_audited_separately():
    wrapped = '<pasted-artifact-abc123>\ndef revised():\n    return 1\n</pasted-artifact-abc123>'
    assert python_parse_error(wrapped) is not None
    assert python_parse_error(strip_boundary_tag_lines(wrapped)) is None


def test_canonical_run_registry_covers_twenty_models_and_register_files():
    assert len(RUNS) == 20
    assert {run.slug for run in RUNS} >= {
        "claude-opus-4-8", "gpt-5.6-sol", "gemini-3.1-pro",
    }
    assert sum(bool(run.additional_results) for run in RUNS) == 17


def test_result_and_trace_histories_merge_with_latest_row_winning(tmp_path):
    primary = tmp_path / "primary.jsonl"
    extension = tmp_path / "extension.jsonl"
    primary.write_text(
        '{"case_id":"a","response":"old","error":"timeout"}\n'
        '{"case_id":"a","response":"final","error":null}\n'
    )
    extension.write_text(
        '{"case_id":"b","response":"native","error":null}\n'
    )
    primary_trace = tmp_path / "primary.traces.jsonl"
    extension_trace = tmp_path / "extension.traces.jsonl"
    primary_trace.write_text(
        '{"case_id":"a","response":{"choices":[{"finish_reason":"length"}]}}\n'
        '{"case_id":"a","response":{"choices":[{"finish_reason":"stop"}]}}\n'
    )
    extension_trace.write_text(
        '{"case_id":"b","response":{"choices":[{"finish_reason":"stop"}]}}\n'
    )
    run = Run("model", primary, additional_results=(extension,))

    rows = merged_latest_results(run)
    finishes = trace_finish_reasons(trace_paths(run))

    assert rows["a"]["response"] == "final"
    assert rows["b"]["response"] == "native"
    assert finishes == {"a": "stop", "b": "stop"}


def test_paired_flag_counts_uses_discordant_events_for_mcnemar():
    records = [
        {"model": "m", "composition_event_id": "1", "condition": "clean",
         "flags": []},
        {"model": "m", "composition_event_id": "1", "condition": "mitigation",
         "flags": ["python_syntax_error"]},
        {"model": "m", "composition_event_id": "2", "condition": "clean",
         "flags": ["python_syntax_error"]},
        {"model": "m", "composition_event_id": "2", "condition": "mitigation",
         "flags": ["python_syntax_error"]},
        {"model": "m", "composition_event_id": "3", "condition": "clean",
         "flags": []},
        {"model": "m", "composition_event_id": "3", "condition": "mitigation",
         "flags": []},
    ]

    counts = paired_flag_counts(
        records, "m", "clean", "mitigation", "python_syntax_error",
    )

    assert counts == {
        "n_pairs": 3,
        "both": 1,
        "a_only": 0,
        "b_only": 1,
        "neither": 1,
        "p_mcnemar_exact": 1.0,
    }
