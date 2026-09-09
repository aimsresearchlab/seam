# SEAM: absorption at unmarked within-turn seams

One user turn can flatten a task, a pasted artifact, and later typed speech
into a single message. SEAM measures **absorption**: the model returns that
trailing user speech *inside* the edited artifact, even though the speech is
benign and asks for no insertion.

```text
typed task        simulated paste             typed afterthought
-----------+----------------------------+-------------------------
Improve it.| Dear Alex, ...             | I still need coffee.
           +-------- expected artifact -+
```

The model sees only the flattened message. The benchmark keeps the segment
boundaries private and checks whether the afterthought enters the deliverable.

## Contents

```
benchmark/     300 clusters x 6 conditions, split by source license
code/seam/     scorer (v2.4.3), statistics, paired tests, runner
code/tools/    dataset builders and the output-health audit
code/wild/     wild-corpus mining and judging (code only, see DATA_LICENSES.md)
code/tests/    regression tests for the scorer and builders
results/       per-model case-level labels (51 files), exclusions, statistics
docs/          scoring rules, manual-check log, result ledger
wild/          audit labels with message text removed (100 rows)
```

## Reproducing the numbers

Every rate, interval, and paired test in the paper regenerates from the saved
labels without new model calls:

```bash
pip install -r requirements.txt
(cd code && python3 -m pytest tests -q)   # run from code/ so `seam` and `tools` import
python3 code/seam/statistics.py --results-dir results/labels --out-dir results --check
```

`--check` recomputes every rate, interval, and test and diffs the result
against the committed `results/statistics.json`; drop it to write a fresh
`statistics.json` and `STATISTICS.md` into the chosen directory. The prose
ledger of what each number means is `docs/SCORES.md`.

Rescoring from raw model outputs is a separate step. The deterministic tier is
exact; the semantic tier is pinned to `transformers` 4.51.3 on CPU with
`deberta-large-mnli`:

```bash
python3 code/seam/score_cascade.py benchmark/seam_v4_permissive.jsonl <outputs>.jsonl \
    --output labels.cascade-full.jsonl        # add --no-nli for the lexical tier only
```

Rerunning inference is not expected to reproduce byte-identical responses.

## Running the benchmark on a new model

```bash
python3 code/seam/run_dataset.py benchmark/seam_v4_permissive.jsonl \
    --models <model-id> --parallel-requests 12 --output run.jsonl --dry-run
```

Drop `--dry-run` to issue real calls. Decoding settings, provider routes, and
the documented per-provider deviations are recorded in `docs/SCORES.md` and
`docs/MANUAL_CHECKS.md`.

## Scope

The benchmark is constructed, English, first-turn editing examples with equal
source weighting and repeated comment pools. It measures the unintended
inclusion of benign user speech in a returned artifact. It contains no
adversarial instructions and no executable payloads, and it does not establish
behavior for sensitive content, other languages, or later conversational turns.
