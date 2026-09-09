import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seam"))

from provenance_methods import (  # noqa: E402
    JSON_FIELD_ORDER,
    collision_safe_line_marker,
    compose_line_marked_message,
    compose_typed_json_fields,
    mark_artifact_lines,
    parse_typed_json_fields,
    unmark_artifact_lines,
)


class TypedJsonFieldsTests(unittest.TestCase):
    def test_json_escapes_and_round_trips_all_regions(self):
        task = 'Revise "this" carefully.\\nUse Unicode: caf\u00e9.'
        artifact = 'def f(name):\n    return f"hi {name}\\\\ok"\n'
        tail = 'The note says: "do not add this."\n\U0001f642'

        message = compose_typed_json_fields(task, artifact, tail)

        self.assertEqual(parse_typed_json_fields(message), {
            "task_before": task, "artifact": artifact, "context_after": tail,
        })
        self.assertEqual(json.loads(message)["artifact"], artifact)
        self.assertIn('\\\\', message)
        self.assertEqual(tuple(json.loads(message)), JSON_FIELD_ORDER)

    def test_json_clean_control_uses_null_context_after(self):
        message = compose_typed_json_fields("task", "artifact", None)
        self.assertEqual(parse_typed_json_fields(message)["context_after"], None)

    def test_json_parser_rejects_extra_or_wrongly_typed_fields(self):
        with self.assertRaises(ValueError):
            parse_typed_json_fields('{"artifact":"a","task_before":"t","context_after":null}')
        with self.assertRaises(ValueError):
            parse_typed_json_fields('{"task_before":"t","artifact":"a","context_after":3}')


class ContinuousMarkingTests(unittest.TestCase):
    def test_marker_retries_when_its_first_deterministic_value_collides(self):
        first = collision_safe_line_marker("ordinary artifact", "cluster-7")
        chosen = collision_safe_line_marker(f"prefix {first} suffix", "cluster-7")
        self.assertNotEqual(chosen, first)
        self.assertNotIn(chosen, f"prefix {first} suffix")

    def test_marker_removal_round_trips_empty_and_multiline_artifacts(self):
        for artifact in ("", "one line", "a\nb\n", "a\r\nb\r\n"):
            with self.subTest(artifact=repr(artifact)):
                marked, marker = mark_artifact_lines(artifact, "cluster-round-trip")
                self.assertEqual(unmark_artifact_lines(marked, marker), artifact)

    def test_marking_preserves_python_indentation_after_removal(self):
        artifact = "def greet(name):\n    if name:\n        return f'Hi {name}'\n    return 'Hi'\n"
        marked, marker = mark_artifact_lines(artifact, "python-case")
        self.assertTrue(all(line.startswith(marker) for line in marked.splitlines()))
        recovered = unmark_artifact_lines(marked, marker)
        self.assertEqual(recovered, artifact)
        compile(recovered, "<artifact>", "exec")

    def test_unmark_rejects_an_unmarked_or_partially_marked_line(self):
        marked, marker = mark_artifact_lines("first\nsecond", "cluster-malformed")
        malformed = marked.replace(marker + "second", "second")
        with self.assertRaises(ValueError):
            unmark_artifact_lines(malformed, marker)

    def test_composed_wire_message_retains_canonical_provenance_metadata(self):
        message, metadata = compose_line_marked_message(
            "Improve the code.", "  x = 1\n", "I need coffee.", "event-1",
        )
        self.assertIn(metadata["line_marker"], message)
        self.assertEqual(unmark_artifact_lines(
            message.split("\n\n", 1)[1].rsplit("\n", 1)[0], metadata["line_marker"]
        ), metadata["artifact"])
        self.assertEqual(metadata["context_after"], "I need coffee.")


if __name__ == "__main__":
    unittest.main()
