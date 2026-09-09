import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seam"))

from patch_output import (  # noqa: E402
    Edit,
    Patch,
    PatchError,
    apply_patch,
    parse_patch,
    patch_output_instruction,
    patch_to_json,
)


class PatchOutputTests(unittest.TestCase):
    def test_instruction_states_strict_schema_and_offsets(self):
        instruction = patch_output_instruction()
        self.assertIn('"version"', instruction)
        self.assertIn('"edits"', instruction)
        self.assertIn("Unicode code-point", instruction)
        self.assertIn("only one JSON object", instruction)

    def test_replaces_multiple_spans_simultaneously(self):
        source = "alpha beta gamma"
        payload = {"version": 1, "edits": [
            {"start": 0, "end": 5, "replacement": "A"},
            {"start": 6, "end": 10, "replacement": "B"},
        ]}
        self.assertEqual(apply_patch(source, payload), "A B gamma")

    def test_unsorted_adjacent_edits_are_supported(self):
        source = "abcd"
        payload = {"version": 1, "edits": [
            {"start": 2, "end": 4, "replacement": "D"},
            {"start": 0, "end": 2, "replacement": "A"},
        ]}
        self.assertEqual(apply_patch(source, payload), "AD")

    def test_insertion_and_empty_patch(self):
        self.assertEqual(
            apply_patch("ac", {"version": 1, "edits": [{"start": 1, "end": 1, "replacement": "b"}]}),
            "abc",
        )
        self.assertEqual(apply_patch("unchanged", {"version": 1, "edits": []}), "unchanged")

    def test_unicode_offsets_are_code_point_offsets(self):
        source = "A🙂 café"
        # Python indexes the emoji and accented character as one code point each.
        payload = {"version": 1, "edits": [{"start": 2, "end": 7, "replacement": " tea"}]}
        self.assertEqual(apply_patch(source, payload), "A🙂 tea")

    def test_rejects_malformed_json_and_wrappers(self):
        for payload in ["not json", "```json\n{\"version\":1,\"edits\":[]}\n```", "{} trailing"]:
            with self.subTest(payload=payload):
                with self.assertRaises(PatchError):
                    parse_patch(payload)

    def test_rejects_unknown_or_missing_fields(self):
        bad = [
            {"version": 1, "edits": [], "comment": "extra"},
            {"version": 1},
            {"version": 1, "edits": [{"start": 0, "end": 0, "replacement": "", "x": 1}]},
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(PatchError):
                    parse_patch(payload)

    def test_rejects_wrong_types_and_version(self):
        bad = [
            {"version": True, "edits": []},
            {"version": 2, "edits": []},
            {"version": 1, "edits": {}},
            {"version": 1, "edits": [{"start": "0", "end": 0, "replacement": ""}]},
            {"version": 1, "edits": [{"start": 0, "end": 0, "replacement": 3}]},
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(PatchError):
                    parse_patch(payload)

    def test_rejects_out_of_range_and_reversed_spans(self):
        source = "abc"
        for span in [(4, 4), (-1, 0), (2, 1), (0, 5)]:
            with self.subTest(span=span):
                patch = Patch(1, (Edit(span[0], span[1], "x"),))
                with self.assertRaises(PatchError):
                    patch.apply(source)

    def test_rejects_overlapping_spans(self):
        patch = parse_patch({"version": 1, "edits": [
            {"start": 1, "end": 4, "replacement": "x"},
            {"start": 3, "end": 5, "replacement": "y"},
        ]})
        with self.assertRaises(PatchError):
            patch.apply("abcdef")

    def test_json_round_trip_preserves_unicode(self):
        patch = Patch(1, (Edit(0, 1, "é🙂"),))
        encoded = patch_to_json(patch)
        self.assertIn("é🙂", encoded)
        self.assertEqual(parse_patch(encoded), patch)


if __name__ == "__main__":
    unittest.main()
