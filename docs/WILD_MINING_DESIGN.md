# Scaled wild-prompt mining (WildChat + LMSYS) — design note

Status: historical design record, implemented 2026-08-30. Current results are
in `research/WILD_PASTE_AUDIT.md`. Read
`research/WILDCHAT_AUDIT_PAPER_GUIDANCE.md` first; it governs how the output may
be used in the paper.

## The one constraint that shapes everything

WildChat and LMSYS have **no clipboard/paste provenance**. We can recover the
*surface form* (an unmarked artifact followed by a typed instruction) but never
the ground-truth typed-vs-pasted boundary. Consequences, decided already:

- Mined prompts strengthen the **ecological-occurrence + task-diversity** claim.
- They **cannot become scored benchmark items** without instrumented provenance,
  because scoring absorption needs the true seam to build counterfactuals.

So the deliverable of this pipeline is *"N human-verified natural cases spanning
K task genres, retrieved by an auditable procedure"* — a stronger version of the
current 23/50 single-author occurrence check, not a test-set expansion.

## What the literature says about method (and where the coauthor's 3 options fit)

- **WildVis** (arXiv:2409.03753), the tool the coauthor linked, embeds only the
  *first user turn* with OpenAI `text-embedding-3-small`, then parametric UMAP
  **per language**. Two lessons: (1) embed the first turn, not the whole
  conversation — full-conversation embeddings clustered worse; (2) their
  embedding captures **topic/semantics**, which is exactly what we do *not*
  primarily need.
- **WILDTEAMING** (NeurIPS 2024, arXiv:2406.18510) is the right methodological
  template for mining a *pragmatic pattern* at scale: cheap screen over all
  single-turn messages → candidate pool → small-model filter → classifier
  verification → human spot-check. Recall from a cheap screen, precision from a
  model judge, ground-truth from a human sample.

Reading the coauthor's three options against this:

1. **Structure matching** — this is the *recall* stage and we already have it
   (`tools/wildchat_audit.py`: deterministic line-shape screen, 16,134 unique
   `paste_with_tail` candidates from 477k English WildChat first turns).
2. **Embedding search** — weak as the *primary* matcher, now confirmed
   empirically. Our target is a structural/pragmatic property (unmarked artifact
   + typed continuation); dense embeddings rank by *topic*. **Measured on the 50
   human labels (BGE-M3, leave-one-out kNN, `tools/wild_vector_eval.py`,
   2026-08-30): accuracy 0.480 vs 0.460 predict-all baseline, ROC-AUC 0.510** —
   i.e. chance. The vector detector does NOT separate genuine from not_genuine
   and does NOT earn a cascade slot. Legitimate residual uses only: task-genre
   coverage/stratification and near-duplicate collapse — not detection.
3. **Small local LLM** — this is the highest-value use of the A100: a structured
   judge over the candidate pool that (a) confirms embedded-artifact + typed-
   continuation, (b) confirms the continuation *operates on* the artifact, and
   (c) labels task genre. Replaces both the flaky heuristic tail detector and
   the unscalable single-author manual pass.

## Proposed pipeline (funnel)

```
[WildChat 1M + LMSYS 1M]                     both single-turn + multi-turn first user msg
   │  CPU, deterministic (extend wildchat_audit.py to LMSYS schema)
   ▼
Structural screen  → ~tens of k candidates   recall stage; already built for WildChat
   │  A100, vLLM small-LLM judge (Qwen3-8B/14B, already supported by box venv)
   ▼
LLM structural filter → high-precision pool  auditable JSON labels + genre tags
   │  embeddings (secondary): dedup + stratify by genre/topic for coverage
   ▼
Stratified human verification (WildTeaming-style)  → precision + final verified set
```

Only the middle stage needs the GPU. The screen is CPU-bound (the WildChat pass
was ~110 s on a laptop); LMSYS adds one more corpus of the same order.

**Screen run — WildChat-4.8M (2026-08-30, ~2 min on 128 cores):** 3.20M convs →
1.68M English first turns → **48,658 unique candidates** (40,164 paste_with_tail
+ 8,494 fence_trailing; 148k near-dups collapsed). Screen rate 2.4% of English
first turns. Adjudication sample of 300 drawn. Judge pool is therefore ~49k, so
the full judge pass is ~2 h (likely less). Corpus adapter added to
`tools/wildchat_audit.py` (`--parquet-glob`, `--id-col`); LMSYS smoke-tested
(3,907 candidates in shard 0 → ~23k projected) but not yet run in full.
Artifacts under `<work-dir>/wild/results/wildchat-4.8m-audit.*`.

## A100 box state (probed 2026-08-30)

- GPU free: 75 MiB / 80 GB used, 0 % util. Disk: 6.3 TB free on `<work-dir>`.
- **Corpus choice: `allenai/WildChat-4.8M`** (the largest release, ~4.8M convs,
  86 parquet, 15.3 GB, **un-gated**). Schema verified: `conversation_hash`,
  `language`, `conversation` present — `wildchat_audit.py` runs as-is by
  repointing the cache glob; no code change for WildChat. English first-turn
  pool scales ~4-5x over the 1M (477k → ~2M+), so the candidate pool and the
  LLM-judge cost scale with it (still cheap on the idle A100).
  - Caveat that matters for us: 4.8M is the **toxic-redacted** release — PII is
    replaced with placeholders, which can land *inside pasted artifacts*
    (redacted emails/names in a pasted document). Fine for structural mining;
    note it when we report artifact realism. Un-redacted `WildChat-4.8M-Full`
    exists but is gated:manual (needs approval) — only pursue if redaction
    proves to distort the artifacts.
- LMSYS-Chat-1M (gated-auto, token has access, 6 parquet) still worth including
  for source diversity — needs a small schema adapter in the screen.
- `seam/venv`: torch 2.6.0+cu124, CUDA OK, vLLM 0.8.5.post1, transformers
  4.51.3 — supports Qwen3-8B/14B (the judge) out of the box. **No
  `sentence_transformers`** installed; embeddings need a separate venv (never
  upgrade the frozen seam venv in place — see `research/LOCAL_RUNS.md`).
- Box is shared (audio projects: writeguard/ace-step/demucs/stable-audio). GPU
  currently idle but coordinate before a long serve.

## Model choices (proposed, not final)

- **Judge:** Qwen3-14B bf16 via vLLM on :8399 (box already runs this family;
  non-thinking mode per LOCAL_RUNS convention). 14B > 8B for structural
  discrimination at trivial cost for ~tens of k candidates. Structured JSON
  output, temperature 0.
- **Embeddings (secondary):** BGE-M3 (MIT, 8192-ctx — matters for long paste
  bodies) in a fresh `venvs/embed` venv, or Qwen3-Embedding-8B if we want
  top-of-leaderboard. Decide only if we commit to the embedding stage.

## Judge validation — clean pass (2026-08-30)

First 50-label agreement run was **worse than chance (acc 0.40, κ = −0.20)**.
Root cause was the eval setup, not the judge:

1. **Truncation.** The gold was built from the audit's stored `msg`, capped at
   2000 chars — which cuts the *tail* (the defining typed continuation) on long
   pastes. Accuracy split 0.25 (capped/long) vs 0.59 (short/full). Fix: rebuilt
   gold from full corpus text by rejoining the 50 `conversation_hash`es against
   WildChat-4.8M (47/50 recovered; 3 not in the 4.8M release). Full messages run
   up to 116 KB.
2. **Head+tail windowing.** Even full text needs both ends fed to the judge —
   front-truncation drops the tail on huge pastes. `wild_judge.py` now keeps
   head(60%)+tail(40%) with the middle elided (`window()`).
3. **Residual definition gap** (secondary): the judge counted head-led
   "Summarize: <article>" as genuine; the human excluded marked/leading forms.
   Do NOT over-tune the rubric to one annotator's 50 labels — this argues for
   the multi-annotator re-annotation below, not prompt overfitting.

Agreement trajectory (Qwen3-14B judge vs the 47 recoverable human labels):

| version | fix | acc | Cohen κ | prec/rec |
|---|---|---:|---:|---|
| v0 | truncated gold (2000 chars) | 0.40 | -0.20 | 0.36/0.39 |
| v1 | full text + head/tail window | 0.57 | 0.18 | 0.52/0.76 |
| v2 | + construct-aligned rubric (reject leading/marked forms) | 0.68 | 0.36 | 0.64/0.67 |

**Stop point: κ = 0.36 (fair), balanced errors (FP 8 / FN 7).** Both fixes were
construct-correct, not annotator-tuning: (v1) the eval data was broken; (v2) the
rubric had to match the project's target (artifact-first, unmarked typed tail) —
verified that all 21 human-genuine cases are artifact-first and 0 are head-led,
so the rubric fix cost no true genuines. Further prompt-tuning against one
annotator's 47 labels would be overfitting. The real path to higher/known
agreement is the multi-annotator re-annotation below, which also gives a
human-human κ ceiling. The 8 FP + 7 FN are plausibly genuine boundary cases.

Judge throughput: **~7 rec/s at 8000-char windows** (v2, small-batch + load
overhead) → **~2-4 h for ~100k screened candidates**; real throughput higher at
scale (vLLM batches far more than 47 concurrently; these tiny runs are
overhead-dominated). Model load+compile ~1 min (cached).

LMSYS status: the box HF token is **not authorized** for lmsys-chat-1m data
files (403; the README HEAD gave a false 200). Needs an access request approved
for the project Hugging Face account before it can join the pipeline.

## Open decisions (for the coauthor / next session)

1. Confirm the paper framing: occurrence-strengthening only, not test-set
   inclusion. (Recommend yes — provenance wall unchanged.)
2. Do we even run the embedding stage, or is structural-screen + LLM-judge +
   human sample sufficient for the occurrence claim? (Recommend: skip embeddings
   for v1; add only for genre-coverage reporting.)
3. Judge model + prompt schema sign-off before the full run (W&B-logged).
4. Human-verification sample size and who annotates (>1 annotator this time, so
   we can report agreement — the current audit couldn't).

## Immediate next steps (safe, no commitments)

- [ ] Extend `tools/wildchat_audit.py` to also read the LMSYS-Chat-1M schema
      (`conversation` list, `language` field differ from WildChat).
- [ ] Push screen to box, download both corpora to `<work-dir>/wild/`.
- [ ] Draft + pin the LLM-judge prompt schema; dry-run on the existing 50
      human-labeled WildChat records to measure judge-vs-human agreement before
      any full run.
