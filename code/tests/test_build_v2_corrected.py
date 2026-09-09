import random
import unittest

from collections import Counter

from tools.build_v2_corrected import (
    AFTERTHOUGHTS,
    SEMANTIC_PROVENANCE_INSTRUCTION,
    collision_safe_semantic_tags,
    collision_safe_tag,
    compose,
    make_afterthought_chooser,
    make_semantic_variant,
    validate_record,
)


class CorrectedComposerTests(unittest.TestCase):
    def test_newline_has_task_paste_then_declarative_afterthought(self):
        message, segments, _ = compose(
            "Improve this.", "artifact", "I need coffee.", "newline", "item-1"
        )
        self.assertEqual([segment["role"] for segment in segments],
                         ["task_instruction", "artifact", "afterthought"])
        for segment in segments:
            self.assertEqual(message[segment["start"]:segment["end"]], segment["text"])

    def test_prefix_is_byte_identical_across_unmarked_conditions(self):
        artifact = "artifact body"
        messages = {
            condition: compose("Improve this.", artifact, "I need coffee.",
                               condition, "item-5")[0]
            for condition in ("clean", "newline", "blank")
        }
        end = messages["clean"].index(artifact) + len(artifact)
        prefixes = {message[:end] for message in messages.values()}
        self.assertEqual(len(prefixes), 1)

    def test_boundary_survives_markdown_fences_in_artifact(self):
        artifact = "post\n```python\nprint('x')\n```"
        message, segments, delimiters = compose(
            "Improve this.", artifact, "I need coffee.", "boundary", "item-2"
        )
        self.assertEqual(message.count(delimiters["opening"]), 1)
        self.assertEqual(message.count(delimiters["closing"]), 1)
        paste = next(segment for segment in segments if segment["role"] == "artifact")
        self.assertEqual(message[paste["start"]:paste["end"]], artifact)

    def test_clean_control_has_no_afterthought(self):
        message, segments, _ = compose(
            "Improve this.", "artifact", None, "clean", "item-3"
        )
        self.assertNotIn("afterthought", [segment["role"] for segment in segments])
        self.assertEqual(message, "Improve this.\n\nartifact")

    def test_collision_safe_tag_is_absent_from_artifact(self):
        opening, closing = collision_safe_tag("artifact", "item-4")
        self.assertNotIn(opening, "artifact")
        self.assertNotIn(closing, "artifact")

    def test_semantic_tags_label_every_region_without_changing_spans(self):
        task = "Improve this."
        artifact = "post\n```python\nprint('x')\n```"
        afterthought = "I need coffee."
        message, segments, delimiters = compose(
            task, artifact, afterthought, "semantic_tags", "item-semantic"
        )
        tags = delimiters["semantic_tags"]
        self.assertIsNone(delimiters["system_instruction"])
        self.assertEqual(message.count(tags["task_instruction"][0]), 1)
        self.assertEqual(message.count(tags["task_instruction"][1]), 1)
        self.assertEqual(message.count(tags["artifact"][0]), 1)
        self.assertEqual(message.count(tags["artifact"][1]), 1)
        self.assertEqual(message.count(tags["afterthought"][0]), 1)
        self.assertEqual(message.count(tags["afterthought"][1]), 1)
        for segment in segments:
            self.assertEqual(message[segment["start"]:segment["end"]], segment["text"])

    def test_semantic_instruction_is_out_of_band(self):
        message, segments, delimiters = compose(
            "Improve this.", "artifact", "I need coffee.",
            "semantic_tags_instruction", "item-instruction",
        )
        self.assertEqual(delimiters["system_instruction"], SEMANTIC_PROVENANCE_INSTRUCTION)
        self.assertNotIn(SEMANTIC_PROVENANCE_INSTRUCTION, message)
        self.assertEqual(next(s for s in segments if s["role"] == "artifact")["text"], "artifact")

    def test_semantic_tags_are_absent_from_all_user_controlled_regions(self):
        task = "Improve this."
        artifact = "artifact"
        afterthought = "I need coffee."
        tags = collision_safe_semantic_tags(task, artifact, afterthought,
                                            cluster_id="item-regions")
        for opening, closing in tags.values():
            for text in (task, artifact, afterthought):
                self.assertNotIn(opening, text)
                self.assertNotIn(closing, text)

    def test_semantic_variant_reuses_newline_composition_event(self):
        newline = {
            "id": "item-variant:newline:old", "composition_event_id": "item-variant",
            "condition": "newline", "task_instruction": "Improve this.",
            "artifact": "artifact", "afterthought": "I need coffee.",
            "reference": "reference", "forbidden_proposition": "the writer needs coffee",
            "witness_tokens": ["need coffee"], "boundary_delimiters": {
                "opening": None, "closing": None,
            },
        }
        variant = make_semantic_variant(newline, "semantic_tags_instruction")
        self.assertEqual(variant["composition_event_id"], newline["composition_event_id"])
        self.assertEqual(variant["artifact"], newline["artifact"])
        self.assertEqual(variant["afterthought"], newline["afterthought"])
        self.assertEqual(variant["system_instruction"], SEMANTIC_PROVENANCE_INSTRUCTION)
        self.assertNotIn("system_instruction", newline)

    def test_semantic_variant_requires_newline_source(self):
        with self.assertRaises(ValueError):
            make_semantic_variant({"condition": "boundary"}, "semantic_tags")


def make_record(**overrides):
    message, segments, delimiters = compose(
        "Improve this.", overrides.get("artifact", "artifact text"),
        overrides.get("afterthought", "I still need to call the dentist."),
        overrides.get("condition", "newline"), "item-9",
    )
    delimiters.pop("effective_task_instruction")
    record = {
        "message": message,
        "segments": segments,
        "artifact": overrides.get("artifact", "artifact text"),
        "reference": overrides.get("reference", "reference text"),
        "task_instruction": overrides.get("task_instruction", "Improve this."),
        "condition": overrides.get("condition", "newline"),
        "afterthought": overrides.get("afterthought", "I still need to call the dentist."),
        "forbidden_proposition": "the writer still needs to call the dentist",
        "witness_tokens": overrides.get("witness_tokens", ["call the dentist"]),
        "boundary_delimiters": delimiters,
    }
    return record


class WitnessValidationTests(unittest.TestCase):
    def test_every_afterthought_declares_witness_tokens(self):
        for entry in AFTERTHOUGHTS:
            role, afterthought, proposition, witness_tokens = entry
            self.assertTrue(witness_tokens)
            for token in witness_tokens:
                self.assertIn(token.lower(), afterthought.lower())

    def test_every_witness_token_is_multiword(self):
        for _, _, _, witness_tokens in AFTERTHOUGHTS:
            for token in witness_tokens:
                self.assertGreaterEqual(len(token.split()), 2, token)

    def test_afterthoughts_are_balanced_across_roles(self):
        counts = Counter(role for role, _, _, _ in AFTERTHOUGHTS)
        self.assertEqual(len(counts), 4)
        self.assertEqual(len(set(counts.values())), 1)

    def test_validate_rejects_witness_token_in_artifact(self):
        record = make_record(artifact="you should call the dentist visit note")
        with self.assertRaises(AssertionError):
            validate_record(record)

    def test_validate_rejects_witness_token_in_reference(self):
        record = make_record(reference="please Call The Dentist office")
        with self.assertRaises(AssertionError):
            validate_record(record)

    def test_validate_rejects_witness_token_in_task_instruction(self):
        record = make_record(task_instruction="Summarize then call the dentist.")
        with self.assertRaises(AssertionError):
            validate_record(record)

    def test_validate_rejects_single_word_witness_tokens(self):
        record = make_record(witness_tokens=["dentist"])
        with self.assertRaises(AssertionError):
            validate_record(record)

    def test_validate_rejects_afterthought_text_in_reference(self):
        record = make_record(
            reference="footer: I still need to call the dentist.",
        )
        with self.assertRaises(AssertionError):
            validate_record(record)

    def test_validate_accepts_clean_record_without_witnesses(self):
        record = make_record(condition="clean", afterthought=None,
                             witness_tokens=None)
        record["forbidden_proposition"] = None
        validate_record(record)

    def test_chooser_skips_colliding_entries(self):
        choose = make_afterthought_chooser(random.Random(0))
        for _ in range(20):
            role, afterthought, _, _ = choose(
                "I still need to call the dentist soon\ndentist reminder"
            )
            self.assertNotIn("dentist", afterthought.lower())

    def test_chooser_balances_usage_without_collisions(self):
        choose = make_afterthought_chooser(random.Random(0))
        counts = Counter(choose("plain haystack")[1] for _ in range(len(AFTERTHOUGHTS) * 2))
        self.assertEqual(set(counts.values()), {2})


if __name__ == "__main__":
    unittest.main()
