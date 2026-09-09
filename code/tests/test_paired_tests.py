import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seam"))

from paired_tests import (  # noqa: E402
    between_models,
    contrast,
    exact_mcnemar,
    load_labels,
)


class ExactMcNemarTests(unittest.TestCase):
    def test_no_discordant_pairs_is_ns(self):
        self.assertEqual(exact_mcnemar(0, 0), 1.0)

    def test_one_sided_discordance_known_value(self):
        # b=5, c=0: two-sided exact p = 2 * 0.5^5 = 0.0625
        self.assertAlmostEqual(exact_mcnemar(5, 0), 0.0625)

    def test_symmetry(self):
        self.assertEqual(exact_mcnemar(8, 2), exact_mcnemar(2, 8))

    def test_balanced_discordance_is_ns(self):
        self.assertGreater(exact_mcnemar(5, 5), 0.99)

    def test_strong_asymmetry_is_significant(self):
        # 85 vs 11 discordant (Flash newline vs boundary scale)
        self.assertLess(exact_mcnemar(85, 11), 1e-10)


def label_rows(spec):
    """spec: {(cluster, condition): absorbed}"""
    return [{"composition_event_id": k[0], "condition": k[1], "absorbed": v}
            for k, v in spec.items()]


class ContrastTests(unittest.TestCase):
    def test_pairing_and_counts(self):
        labels = {("c1", "newline"): True, ("c1", "boundary"): False,
                  ("c2", "newline"): True, ("c2", "boundary"): True,
                  ("c3", "newline"): False, ("c3", "boundary"): False}
        r = contrast(labels, "newline", "boundary")
        self.assertEqual(r["n_pairs"], 3)
        self.assertEqual(r["a_only"], 1)
        self.assertEqual(r["b_only"], 0)
        self.assertEqual(r["both"], 1)
        self.assertAlmostEqual(r["rate_a"], 2 / 3)
        self.assertAlmostEqual(r["rate_b"], 1 / 3)

    def test_missing_condition_pairs_skipped(self):
        labels = {("c1", "newline"): True}  # no boundary row for c1
        r = contrast(labels, "newline", "boundary")
        self.assertEqual(r["n_pairs"], 0)
        self.assertEqual(r["p_exact"], 1.0)


class BetweenModelTests(unittest.TestCase):
    def test_same_condition_pairing(self):
        a = {("c1", "newline"): True, ("c2", "newline"): True,
             ("c1", "blank"): True}
        b = {("c1", "newline"): False, ("c2", "newline"): True}
        r = between_models(a, b, "newline")
        self.assertEqual(r["n_pairs"], 2)
        self.assertEqual(r["a_only"], 1)
        self.assertEqual(r["both"], 1)


class LoadLabelsTests(unittest.TestCase):
    def test_roundtrip(self):
        rows = label_rows({("c1", "newline"): True, ("c1", "blank"): False})
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        labels = load_labels(Path(handle.name))
        self.assertEqual(labels, {("c1", "newline"): True, ("c1", "blank"): False})


if __name__ == "__main__":
    unittest.main()
