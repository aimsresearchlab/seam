import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seam"))

import run_dataset  # noqa: E402


class DatasetRunnerDefaultsTests(unittest.TestCase):
    def test_runner_documents_bounded_default(self):
        source = Path("seam/run_dataset.py").read_text()
        self.assertIn('"--parallel-requests", "--parallelism"', source)
        self.assertIn("type=int, default=12", source)

    def test_builder_seed_is_42(self):
        source = Path("tools/build_automated_dataset.py").read_text()
        self.assertIn('ap.add_argument("--seed", type=int, default=42)', source)


class CompletedPairsTests(unittest.TestCase):
    def _write(self, rows):
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return Path(handle.name)

    def test_successful_rows_counted_errored_retried(self):
        path = self._write([
            {"model": "m", "case_id": "a", "response": "ok", "error": None},
            {"model": "m", "case_id": "b", "response": "", "error": "timeout"},
        ])
        self.assertEqual(run_dataset.completed_pairs(path), {("m", "a")})

    def test_retry_row_after_error_counts(self):
        path = self._write([
            {"model": "m", "case_id": "b", "response": "", "error": "timeout"},
            {"model": "m", "case_id": "b", "response": "ok", "error": None},
        ])
        self.assertEqual(run_dataset.completed_pairs(path), {("m", "b")})


class FakeChoice:
    def __init__(self, text, finish_reason="stop"):
        self.message = type("M", (), {"content": text})()
        self.finish_reason = finish_reason


class FakeClient:
    """Counts calls; fails case ids listed in `fail_once` on first attempt."""

    def __init__(self, fail_once=()):
        self.calls = []
        self.requests = []
        self.failed = set()
        self.fail_once = set(fail_once)
        outer = self

        class Completions:
            def create(self, **request):
                request.pop("timeout", None)
                content = request["messages"][0]["content"]
                outer.calls.append(content)
                outer.requests.append(dict(request))
                if content in outer.fail_once and content not in outer.failed:
                    outer.failed.add(content)
                    raise RuntimeError("boom")
                return type("R", (), {
                    "choices": [FakeChoice(f"echo:{content}")],
                    "model_dump": lambda self_: {"ok": True},
                })()

        self.chat = type("Chat", (), {"completions": Completions()})()


class SystemInstructionTests(unittest.TestCase):
    def test_system_instruction_is_sent_as_a_separate_privileged_message(self):
        client = FakeClient()
        row, _ = run_dataset.call(
            client, "m",
            {"id": "c1", "message": "payload", "system_instruction": "rule"},
            max_tokens=32, request_timeout=10,
        )
        self.assertIsNone(row["error"])
        self.assertEqual(client.requests[0]["messages"], [
            {"role": "system", "content": "rule"},
            {"role": "user", "content": "payload"},
        ])


class ResumeEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.dataset = Path(self.dir.name) / "cases.jsonl"
        with self.dataset.open("w") as handle:
            for cid in ("c1", "c2", "c3"):
                handle.write(json.dumps({"id": cid, "message": cid}) + "\n")
        self.output = Path(self.dir.name) / "out.jsonl"

    def _run(self, client, extra=()):
        argv = ["run_dataset.py", str(self.dataset), "--models", "m",
                "--output", str(self.output), "--parallel-requests", "1",
                *extra]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_dataset, "make_client",
                                  return_value=(client, None)):
            run_dataset.main()

    def _rows(self):
        return [json.loads(l) for l in self.output.open()]

    def test_rows_written_incrementally_and_resume_skips_done(self):
        client = FakeClient(fail_once=["c2"])
        self._run(client)
        rows = self._rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(bool(r["error"]) for r in rows), 1)
        # traces written next to output when --output is explicit
        self.assertTrue(self.output.with_suffix(".traces.jsonl").exists())

        # resume: only the errored case is retried, successes are skipped
        client2 = FakeClient()
        self._run(client2, extra=["--resume"])
        self.assertEqual(client2.calls, ["c2"])
        rows = self._rows()
        self.assertEqual(len(rows), 4)
        # last row per case wins for readers: c2's final row is a success
        final = {r["case_id"]: r for r in rows if not r.get("error")}
        self.assertEqual(sorted(final), ["c1", "c2", "c3"])

    def test_temperature_flag_passed_and_recorded_on_rows(self):
        client = FakeClient()
        self._run(client, extra=["--temperature", "1.0"])
        self.assertTrue(all(r["temperature"] == 1.0 for r in client.requests))
        self.assertTrue(all(r.get("temperature") == 1.0 for r in self._rows()))

    def test_default_temperature_zero_and_untagged(self):
        client = FakeClient()
        self._run(client)
        self.assertTrue(all(r["temperature"] == 0.0 for r in client.requests))
        self.assertTrue(all("temperature" not in r for r in self._rows()))

    def test_chat_template_kwargs_passed_via_extra_body(self):
        # local hybrid-reasoning models (Qwen3) need chat_template_kwargs
        # (e.g. enable_thinking=false); OpenAI-compatible servers take these
        # via extra_body. Absent the flag, no extra_body is sent.
        client = FakeClient()
        self._run(client, extra=["--chat-template-kwargs",
                                 '{"enable_thinking": false}'])
        self.assertTrue(all(
            r["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
            for r in client.requests))

    def test_no_extra_body_by_default(self):
        client = FakeClient()
        self._run(client)
        self.assertTrue(all("extra_body" not in r for r in client.requests))

    def test_existing_output_without_resume_refuses(self):
        self._run(FakeClient())
        with self.assertRaises(SystemExit):
            self._run(FakeClient())

    def test_resume_retries_empty_and_length_rows(self):
        self.output.write_text("\n".join([
            json.dumps({"model": "m", "case_id": "c1", "response": "ok",
                        "finish_reason": "stop", "error": None}),
            json.dumps({"model": "m", "case_id": "c2", "response": "",
                        "finish_reason": "length", "error": None}),
            json.dumps({"model": "m", "case_id": "c3", "response": "",
                        "finish_reason": "stop", "error": None}),
        ]) + "\n")
        client = FakeClient()
        self._run(client, extra=["--resume"])
        self.assertEqual(client.calls, ["c2", "c3"])

    def test_legacy_length_trace_is_retried(self):
        self.output.write_text(json.dumps({
            "model": "m", "case_id": "c1", "response": "", "error": None,
        }) + "\n")
        trace = {
            "case_id": "c1", "request": {"model": "m"},
            "response": {"choices": [{"finish_reason": "length"}]},
        }
        self.output.with_suffix(".traces.jsonl").write_text(
            json.dumps(trace) + "\n")
        client = FakeClient()
        self._run(client, extra=["--resume"])
        self.assertEqual(client.calls, ["c1", "c2", "c3"])


if __name__ == "__main__":
    unittest.main()
