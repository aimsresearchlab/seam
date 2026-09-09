import unittest

from tools.build_automated_dataset import compose, stratified_sample


class ComposeTests(unittest.TestCase):
    def test_none_offsets_round_trip(self):
        message, segments = compose("artifact", "typed tail", "none")
        self.assertEqual(message[segments[0]["start"]:segments[0]["end"]], "artifact")
        self.assertEqual(message[segments[1]["start"]:segments[1]["end"]], "typed tail")

    def test_fence_offsets_exclude_markup(self):
        message, segments = compose("artifact", "typed tail", "fence")
        self.assertEqual(message[segments[0]["start"]:segments[0]["end"]], "artifact")
        self.assertEqual(message[segments[1]["start"]:segments[1]["end"]], "typed tail")


def make_candidates(count, size=lambda i: 100 + i * 37):
    return [{"source_item_id": str(i), "artifact": "x" * size(i)}
            for i in range(count)]


class StratifiedSampleTests(unittest.TestCase):
    def test_deterministic_across_calls(self):
        first = stratified_sample(make_candidates(90), 30, "src")
        second = stratified_sample(make_candidates(90), 30, "src")
        self.assertEqual([r["source_item_id"] for r in first],
                         [r["source_item_id"] for r in second])

    def test_covers_all_length_buckets(self):
        picked = stratified_sample(make_candidates(90), 30, "src")
        sizes = sorted(len(r["artifact"]) for r in picked)
        pool_sizes = sorted(100 + i * 37 for i in range(90))
        lo, hi = pool_sizes[30], pool_sizes[60]
        self.assertEqual(sum(1 for s in sizes if s <= lo), 10)
        self.assertEqual(sum(1 for s in sizes if lo < s <= hi), 10)
        self.assertEqual(sum(1 for s in sizes if s > hi), 10)

    def test_dedups_identical_artifacts(self):
        candidates = make_candidates(40) + make_candidates(40)
        picked = stratified_sample(candidates, 20, "src")
        artifacts = [r["artifact"] for r in picked]
        self.assertEqual(len(artifacts), len(set(artifacts)))

    def test_hard_fails_on_shortfall(self):
        with self.assertRaises(SystemExit):
            stratified_sample(make_candidates(10), 20, "src")

    def test_drains_uneven_buckets(self):
        picked = stratified_sample(make_candidates(30), 30, "src")
        self.assertEqual(len(picked), 30)


if __name__ == "__main__":
    unittest.main()
