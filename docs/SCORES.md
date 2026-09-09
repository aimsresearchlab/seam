# SCORES — central results ledger

One place for every scored run. Rates are absorption per condition
(n=300/condition unless noted; five audited legacy-run models have cells with n=297--299).
"Lexical" = `score_cascade.py --no-nli`
(SEP-comparable); "full" = lexical + semantic NLI tier. Method:
`research/SCORING.md`; validation: `research/SCORING.md` §Detector
validation (branch `cascade-validation`).

## Master table — all 20 models (full cascade, CANONICAL, 2026-08-21)

Scorer v2.4.3; NLI pinned env (transformers 4.51.3, CPU,
deberta-large-mnli). All semantic hits were reviewed; Gemini used an agent
first pass with all five escalations author-adjudicated (MANUAL_CHECKS.md).
Labels: `seam/results/dataset-<slug>.cascade-full.jsonl`. ×red =
newline/boundary rate ratio (the markup lever).

| model | provenance | newline | blank | boundary | mitig. | ×red | NLI hits |
|---|---|---:|---:|---:|---:|---:|---:|
| deepseek-v4-flash | API | 31.3 | 30.3 | 4.4 | 0.3 | 7.1× | 17 |
| deepseek-v4-pro | API | 22.3 | 19.0 | 1.0 | 0.0 | 22× | 8 |
| minimax-m3 | API | 22.3 | 21.7 | 3.3 | 0.0 | 6.7× | 14 |
| minimax-m2.5 | API | 28.7 | 26.4 | 6.4 | 1.7 | 4.5× | 12 |
| mimo-v2.5 | API | 20.0 | 19.7 | 5.0 | 1.3 | 4.0× | 15 |
| mimo-v2.5-pro | API | 21.7 | 20.0 | 4.0 | 0.0 | 5.4× | 17 |
| mistral-small-3.2-24b | local A100 | 41.3 | 47.3 | 28.0 | 12.0 | 1.5× | 21 |
| qwen3-8b | local A100 | 53.0 | 53.3 | 26.0 | 0.0 | 2.0× | 5 |
| qwen3-32b | local A100 | 32.7 | 33.0 | 5.3 | 0.0 | 6.2× | 10 |
| olmo-2-32b | local A100 | 66.7 | 72.3 | 35.3 | 0.3 | 1.9× | 39 |
| gpt-oss-20b | DeepInfra bf16 | 35.1 | 41.8 | 16.4 | 0.0 | 2.1× | 27 |
| gpt-oss-120b | DeepInfra bf16 | 39.3 | 43.0 | 18.3 | 0.3 | 2.1× | 42 |
| llama-3.1-8b | DeepInfra bf16 | 7.7 | 11.7 | 7.3 | 0.3 | 1.0× (ns) | 17 |
| llama-3.3-70b | Novita bf16 | 19.0 | 20.3 | 14.0 | 0.0 | 1.4× | 34 |
| gemma-3-4b | DeepInfra bf16 | 52.0 | 51.3 | 19.7 | 9.3 | 2.6× | 34 |
| gemma-3-12b | DeepInfra bf16 | 38.5 | 44.1 | 19.1 | 6.0 | 2.0× | 21 |
| gemma-3-27b | Novita bf16 | 27.7 | 35.0 | 20.3 | 0.7 | 1.4× | 34 |
| **claude-opus-4-8** | OpenRouter API | 19.0 | 21.0 | **2.0** | **0.0** | 9.5× | 1 |
| **gpt-5.6-sol** | OpenRouter API | 32.0 | 36.7 | 11.7 | **0.0** | 2.7× | 62 |
| **gemini-3.1-pro-preview** | OpenRouter API, Google Vertex | 29.3 | 32.3 | 3.0 | **0.0** | 9.8× | 21 |

All rows use scorer v2.4.3 and are canonical as of 2026-08-21. For the
original 19-model grid, the v2.4.2 revision
(validated on a frozen dev/held-out split of the Opus hand-read — see
research/OPUS_ISSUE.md) changed 116 labels total (78 Opus + 38 old
panel, every one hand-read, all absorbed→not; targeted pinned-env NLI
pass on the GPU host confirmed all 106 NLI-eligible flips, 0
resurrections). Flash, Pro, Qwen3 both sizes, Mistral, Gemma-4B,
gpt-5.6-sol, and both H1 v4 files are byte-unchanged. Opus boundary
2.0% (6/300) includes 2 documented scorer residuals (the
podcast-reply shape, OPUS_ISSUE.md); residual-adjusted 1.3%, lever
9.5× canonical / 14.2× adjusted.

**Scorer v2.4.3 (2026-08-14):** the output-health audit found that the
horizontal-rule commentary strip searched an entire suffix for meta language.
In 31 responses, a separator before the returned artifact was therefore
mistaken for the start of a trailing commentary section when a later line said
"Key improvements" or similar. The rule now requires meta language on the
first nonempty line after the separator. All 31 changed spans were read against
their forbidden proposition. Two labels flip from not absorbed to lexical
absorption: MiniMax M2.5 blank 78→79 and Mistral boundary 83→84
(28.0%). No mitigation label changes. Two regression tests were added; the
full scorer suite passes 59/59.

The same audit found 13 unusable completions that had silently counted as
not absorbed. Five Flash pairs were recovered with complete matched clean
controls from the later register run. Seventeen remaining label rows are
excluded: 6 Flash, 1 Pro, 2 MiniMax M2.5, 4 gpt-oss-20b, and 4 Gemma-12B.
Affected cells therefore use n=297--299; `research/output_health_exclusions.jsonl`
records every case and reason. Rates above and below use the audited
denominators. No direction or significance conclusion changes.

Ranges for the abstract (v2.4.3 plus documented hand adjudications): bare-seam (newline) 7.7–66.7%;
boundary reduction 1.0×(ns)–22×; mitigation ≤ boundary in all 20,
observed zero floor in 10 of 20 (Pro, M3, MiMo-pro, Qwen3-8B/32B,
gpt-oss-20b, llama-70b, Opus 4.8, GPT-5.6-sol, Gemini 3.1 Pro). After
20-model Holm correction, blank > newline is significant in 3 models and
no model has a significant reduction.
Per-model detail, provenance quirks, and contrasts in the sections
below; ladder tests in the 2026-07-12 panel section.

## Residual-enriched M1/M2 diagnostic (2026-08-14, canonical full cascade)

This is a deliberately conditional diagnostic, not a prevalence estimate. The fixed 50-event panel contains 40 prose events previously absorbed under mitigation by Gemma 3 4B or Mistral Small 3.2 24B and 10 code events for output-health testing. Every model was rerun on matched clean, boundary, mitigation, M1 semantic tags, and M2 semantic tags plus a privileged provenance instruction through one pinned OpenRouter upstream provider with fallback disabled.

| model / pinned route | usable pairs | boundary | mitigation | M1 | M2 |
|---|---:|---:|---:|---:|---:|
| DeepSeek V4 Flash 0731 / DeepSeek fp8 | 47 | 6.4 (3) | 0.0 (0) | 2.1 (1) | **0.0 (0)** |
| Mistral Small 3.2 24B / DeepInfra fp8 | 50 | 72.0 (36) | 42.0 (21) | 2.0 (1) | **0.0 (0)** |
| Gemma 3 4B / DeepInfra bf16 | 50 | 62.0 (31) | 48.0 (24) | 4.0 (2) | **0.0 (0)** |
| Qwen3 8B / Alibaba, non-thinking | 50 | 76.0 (38) | 0.0 (0) | 4.0 (2) | **0.0 (0)** |
| Llama 3.1 8B / CoreWeave bf16 | 50 | 16.0 (8) | 0.0 (0) | 2.0 (1) | **0.0 (0)** |
| Claude Opus 4.8 / Anthropic | 50 | 8.0 (4) | 2.0 (1) | 0.0 (0) | **0.0 (0)** |

The seven M1 positives and all 17 semantic-NLI hits across the grid were read end to end; all are genuine delivery of the outside context. M2 has no lexical or NLI absorption in 297 usable model-event pairs. Within model, M2 versus mitigation is significant on the two residual-enriched focal models: Mistral 42% to 0% (21 vs 0 discordant, exact McNemar p=9.54e-7) and Gemma 48% to 0% (24 vs 0, p=1.19e-7). M1 versus M2 is directionally 7 to 0 across the panel but not significant within any single 50-event model sample, so do not claim that the privileged instruction is behaviorally superior based on absorption alone.

Output health distinguishes the methods more clearly. Across usable code responses, M2 has 0/59 syntax failures and no observed wrapper leakage. M1 has 5/58 wrapper-induced syntax failures: Qwen 1/10, Llama 1/10, and Opus 3/10. One Qwen M1 response echoed the entire marked request, including the outside context. On the same selected code events, the existing mitigation reproduces the known Opus problem at 9/10 invalid extracted Python responses. These checks measure parseability and wrapper health, not semantic task correctness.

DeepSeek produced 17 empty reasoning-only truncations at temperature 0. Two tagged retries at the model-recommended temperature 1 recovered eight; nine remained, clustered in three events whose failed clean controls conservatively remove every treated comparison for those events. The other five models have 250/250 usable outputs. Qwen's initial four-call probe revealed that Alibaba ignored `chat_template_kwargs` alone; the canonical Qwen file additionally sets OpenRouter `reasoning.enabled=false` and has exactly zero reasoning tokens. Parasail bf16 was unavailable with persistent shared-pool 429s, so the Mistral grid was restarted on DeepInfra fp8 and must not be conflated with the earlier local-bf16 rates.

Provider-reported spend, including retries and discarded probes, was $2.30. Labels are `seam/results/m1-m2-panel-*.cascade-full.jsonl`. The pinned CPU rerun on the lab server (transformers 4.51.3, DeBERTa-large-MNLI argmax, `cuda_available=False`) completed on 2026-08-14 and is byte-identical to the original local transformers 5.7.0 labels across all six models.

## Full-set M1/M2 study (2026-08-18, canonical NLI, 300 per condition)

This is the full-benchmark basis the residual-enriched panel above is not. Following prof feedback that the headline M2 zero should not rest on a conditional 50-event stress test, M2 and matched controls were rerun on the same representative 300-event-per-condition set the main SEAM table draws from, source-balanced across the six benchmark sources. Dataset `data/inference_m1_m2_full300.jsonl` (1,500 rows, md5 `fafd98d017765bbe716d1bf59a84e569`), built deterministically with zero model calls. Three models shipped this pass: Claude Opus 4.8 (Anthropic route), Qwen3 8B (local A100 bf16, non-thinking), DeepSeek V4 Flash 0731 (DeepSeek fp8 via OpenRouter). Gemma 3 4B and Llama 3.1 8B remain deferred on an HF gated token.

| model / route | boundary | mitigation | M1 tags | M2 tags+instruction |
|---|---:|---:|---:|---:|
| Claude Opus 4.8 / Anthropic | 4.7 (14/300) | 1.3 (4/300) | 0.0 (0/300) | **0.0 (0/300)** |
| Qwen3 8B / local bf16 non-thinking | 25.7 (77/300) | 0.0 (0/300) | 1.3 (4/300) | **0.0 (0/300)** |
| DeepSeek V4 Flash 0731 / DeepSeek fp8 | 0.7 (2/290) | 0.0 (0/291) | 0.0 (0/292) | **0.0 (0/292)** |
| Pooled | 10.4 (93/890) | 0.4 (4/891) | 0.4 (4/892) | **0.0 (0/892)** |

M2 is a hard zero in every model and pooled, at 0/892 usable model-event pairs. The rule-of-three 95% upper bound is about 0.34% pooled and about 1.0% per model. The measurement is demonstrably sensitive rather than floored: pooled boundary absorption is 10.4% and Qwen boundary reaches 25.7%, the panel's most sensitive cell, yet its M2 is still 0. M1 versus M2 is directionally 4 to 0 pooled (all four M1 positives are Qwen) but not significant, so do not claim the privileged instruction is behaviorally superior on absorption alone. Labels `seam/results/m2-full300-*.cascade-full.jsonl`.

The cascade is NLI-canonical, not lexical only. The semantic NLI tier fired twice across all three grids, both on the boundary control (one Opus, one Qwen), and never on M1 or M2, so the lexical scorer was not undercounting the treated arms. The pinned rerun used the lab server env (transformers 4.51.3, DeBERTa-large-MNLI argmax, CPU).

DeepSeek reasoning-token truncation was handled in two passes. The original temperature-0 run left 160 empty reasoning-only outputs at the 8,192-token completion cap; a preregistered temperature-1 `--resume` retry recovered 52. A second `--resume` at temperature 1 with the cap raised to 32,000 recovered 89 of the remaining 107, since these were mid-reasoning cutoffs rather than infinite loops. That leaves 19 residual length-truncations across all conditions and zero in the M2 arm: M2 is a full 300/300 at the response level, and its cascade N of 292 reflects only matched clean-control pairs still truncated. DeepSeek per-model M2 upper bound is about 1.0% on 292. Backups `*.pretemp1.jsonl` (temp-0 original) and box `*.pre-recover2.bak`.

Still open before the zero is fully airtight: a blind hand-audit of M2 negatives, to distinguish a true zero from a detector blind spot independent of N. The nonzero boundary and mitigation rates are supporting evidence of scorer sensitivity but not a substitute for reading the negatives.

**Scorer v2 (2026-07-11, commentary strip):** `extract_artifact_span` now
strips edit-meta commentary (trailing `---` sections, `(Note: ... was
removed)` parentheticals, `Note:`-prefixed lines — only when they carry
edit-meta language; mention-vs-use rule, see MANUAL_CHECKS.md). All lexical
numbers below are scorer-v2. Effect: DeepSeek Flash/Pro bit-identical;
MiniMax/MiMo −1 to −4 hits (every flip hand-read: all removal-meta);
Mistral −89 hits. **v2.1** adds acknowledged-aside stripping (assistant
answers the aside; 5 MiMo flips). **v2.2** adds in-body compliance-report
sentences and meta code comments ("has been omitted as per your
instructions"; found on OLMo — 16 flips, all hand-read). **v2.3** adds
noun-headed mention-about ("the unrelated comment about X"; found on
OLMo, changes zero lexical labels). **v2.4 (2026-07-12)** adds verb-gated
"is/was/seems not related" and "seems to be a separate/personal ..."
mention-about variants (found on llama-3.3-70b, "Note: [aside] is not
related to the code and seems to be a separate message"). Effect across
all 17 result files: exactly 2 flips, both the hand-identified llama-70b
compliance notes (stackexchange:13268527:blank, 37388025:boundary); zero
span changes on the original 10 models (verified byte-identical spans),
so all canonical v2.3 full-cascade labels remain valid. 4 regression
tests added. **v2.4.1 (2026-07-12)** adds the pronoun+contraction form
of the same verdict — `(that|it|this)['’]s (unrelated|not related)` —
found by the 210-hit semantic hand-read on gpt-oss-20b ("Side note: The
team stand-up was moved to Thursday, but that's unrelated to the
code."). Codebook rule made explicit: disclaimed relay is mention;
undisclaimed segregated delivery is absorption. Effect: 11 spans
changed across 17 models (all removed sentences hand-read — disclaimed
relays and compliance notes only), 9 label flips absorbed→not (8
lexical + 1 semantic), each −0.3pp; the 8 lexical-to-NLI fall-throughs
re-scored on the pinned env (7 non-absorbed, mistral 9209530:newline
stays absorbed via a residual in-artifact note). First change to
old-panel canonical labels since v2.3: mimo-v25 blank, mistral blank,
olmo2 blank+boundary — tables below updated in place. 2 regression
tests (42/42). See MANUAL_CHECKS.md. Placebo re-run after each revision:
**0/27,600** both tiers throughout (v2.4 verified on deepseek-flash and
llama-3.3-70b outputs, with and without differential; v2.4.1 on those
plus gpt-oss-20b and mistral-24b). **NLI environment pinned:
transformers 4.51.3, CPU** (two borderline argmax labels flip under
5.7/MPS; the pinned env gets both right per hand audit — see
MANUAL_CHECKS.md). Full-cascade labels are the canonical v2.3 pass in
that environment, plus the 9 pinned-env v2.4.1 corrections.
**v2.4.2 (2026-08-13, in validation — see research/OPUS_ISSUE.md):**
encodes the Opus 4.8 hand-read FP families (trailing acknowledged-aside
paragraphs incl. bare-code responses, quoted-aside-in-meta with
quote-masked sentence segmentation, split-and-label frames, ~20
mention-about variants; weak generic closers strip in parentheticals
only). Developed on a frozen 41/39 dev/held-out split of the 80
author-verified flips (seed 20260813): frozen-rule held-out
reproduction 24/37, then a disclosed round-2 fold-in; final dev 37/38,
held-out 36/37, 0/291 confirms lost, 55/55 tests. Old panel: 38 label
flips (all absorbed→not, every one read by two readers; zero on
DeepSeek Flash/Pro, gpt-5.6-sol, and the H1 v4 files; adjudication
notes incl. the don't-forget tension in OPUS_ISSUE.md). **CANONICAL
2026-08-13**: targeted pinned-env NLI pass (lab box, transformers
4.51.3, CPU, device verified) scored all 106 NLI-eligible changed
cases — 99 fall-throughs all non-absorbed, the 5 Opus NLI-tier flips
reproduced, the 2 OLMo premise-changed hits correctly kept absorbed;
label files regenerated in place (tools/merge_v242_labels.py);
McNemars recomputed for every affected model. Lexical placebo under
v2.4.2, all six sweeps complete (outputs: seam/results/placebo-v242/):
v3 panel (deepseek-flash, llama33-70b, gpt-oss-20b, mistral-24b) 0
fires in every cell, 27,600 pairs each. Frontier v4 (100,500 pairs
each): regex tier 0 differential fires on both models; witness tier 6
differential fires on Opus (6.0e-5) and 3 on GPT (3.0e-5). All 9
hand-read (2026-08-13): each is a single generic-token substring
coincidence ("compiles" describing Java regex compilation,
"inconsistent" describing naming/citation style, "segfault" in a test
named test_segfault_import); none contains the full token pair, and
the all-stems regex tier rejects all 9. FP bound: 6.0e-5 implies
~0.018 expected false hits per 300-case condition, two-plus orders of
magnitude below the smallest cited frontier effect (Opus boundary
2.0% = 6/300). Identity-overlap check: every real witness-tier hit on
the three colliding identities has both tokens present (one GPT
pararev case matched on the distinctive five-word "notation in the
appendix"); no real label rests on a generic single token.

## deepseek-v4-flash — 2026-07-10 (definitive)

- Model output: `seam/results/dataset-20260710-221011.jsonl`
  (trace: `traces/run-20260710-221011.jsonl`; 1,500/1,500, 0 errors)
- Labels: `seam/results/deepseek-flash.cascade-full.jsonl` (full,
  scorer v2, 2026-07-11 — supersedes `v3-flash-cascade.jsonl`; rates
  identical to v1, all 17 semantic hits re-audited genuine),
  `seam/results/v3-flash-cascade-lex.jsonl` (lexical, regenerated
  under scorer v2)

| condition | full cascade | lexical |
|---|---:|---:|
| newline | 31.3% (94/300) | 28.3% (85/300) |
| blank | 30.3% (90/297) | 28.3% (84/297) |
| boundary | 4.4% (13/298) | 3.7% (11/298) |
| mitigation | 0.3% (1/299) | 0.3% (1/299) |

Tier attribution (full): 17 semantic_nli hits, all spot-checked (coedit 8,
iterater 6, pararev 3); none code, none verbatim. Genre gradient:
coedit ~82% → iterater ~40% → pararev ~28% → stackexchange ~20% →
code sources ~0%.

## deepseek-v4-pro — 2026-07-10/11

- Model output: `seam/results/dataset-20260710-235815.jsonl`
  (trace: `traces/run-20260710-235815.jsonl`; 1,500/1,500, 0 errors;
  max_tokens 8192; actual cost ≈ $1.79, completion 1.86M tokens)
- Labels: `seam/results/deepseek-pro.cascade-full.jsonl` (full,
  scorer v2, 2026-07-11 — supersedes `v3-pro-cascade.jsonl`; rates
  identical to v1, all 8 semantic hits re-audited genuine incl. the
  "sleepless night" deep paraphrase),
  `seam/results/v3-pro-cascade-lex.jsonl` (lexical, scorer v2 —
  verified bit-identical to v1)

| condition | full cascade | lexical |
|---|---:|---:|
| newline | 22.3% (67/300) | 20.7% (62/300) |
| blank | 19.0% (57/300) | 18.0% (54/300) |
| boundary | 1.0% (3/299) | 1.0% (3/299) |
| mitigation | 0.0% (0/300) | 0.0% (0/300) |

Tier attribution (full): 112 lexical_witness, 7 lexical_regex,
8 semantic_nli. **All 8 semantic hits hand-audited genuine** (7 coedit
paraphrases — "pushed"→"postponed", "kept barking"→"barked incessantly";
1 stackexchange deep paraphrase — "I barely slept last night" woven into
the revised post as "After a sleepless night, I can't decide…", no witness
words). Conservative bound: adjudicating all 8 away shifts any condition
rate ≤ 1.7pp.

### Paired tests (exact McNemar, cluster-paired; `seam/paired_tests.py`)

Within-model condition contrasts (rate_a vs rate_b, discordant a/b, p):

| contrast | Flash | Pro |
|---|---|---|
| newline vs blank | .316/.303, 18/14, p=.60 (ns) | .223/.190, 21/11, p=.11 (ns) |
| newline vs boundary | .315/.044, 81/0, p=8e-25 | .224/.010, 66/2, p=2e-17 |
| blank vs boundary | .304/.044, 78/1, p=3e-22 | .191/.010, 57/3, p=6e-14 |
| boundary vs mitigation | .044/.003, 13/1, p=.002 | .010/.000, 3/0, p=.25 (ns) |

Between models (same condition, cluster-paired): Flash > Pro on newline
(p=5e-4), blank (p=3e-6), boundary (p=.02); mitigation ns (1/0 discordant).

Reading: whitespace quantity never matters; boundary markup is decisive
for both tiers; the extra mitigation instruction adds significance only
where boundary alone still leaks (Flash); capability reduces absorption
significantly but nowhere near zero.

## minimax/minimax-m3 — 2026-07-11 (lexical, provisional)

- Model output: `seam/results/dataset-minimax-m3.jsonl` (+ traces;
  1,500/1,500 after a 4-case temp-0 resume, 0 persistent failures)
- Labels: `seam/results/dataset-minimax-m3.cascade.jsonl` (lexical only;
  full cascade pending)

| condition | lexical |
|---|---:|
| newline | 20.0% (60/300) |
| blank | 19.3% (58/300) |
| boundary | 4.0% (12/300) |
| mitigation | 0.3% (1/300) |

Tier attribution: 127 lexical_witness, 4 lexical_regex. Within-lab
capability pair: M3 (flagship) 20.0% vs M2.5 27.3% on newline —
capability moderation replicates inside MiniMax. Manual checks: trace
audit clean (4 transient failures retried at temp 0, no repetition
loops); genre span spot-check pending with full cascade.

## xiaomi/mimo-v2.5-pro — 2026-07-11 (lexical, provisional)

- Model output: `seam/results/dataset-mimo-v25-pro.jsonl` (+ traces;
  1,500/1,500 after a 16-case uncapped temp-0 resume; failures were
  genuine long reasoning at the 16k cap + 1 hallucinated tool_call +
  2 empty-stop; no repetition loops; 0 persistent failures, no
  temperature deviation)
- Labels: `seam/results/dataset-mimo-v25-pro.cascade.jsonl` (lexical)

| condition | lexical |
|---|---:|
| newline | 17.7% (53/300) |
| blank | 18.7% (56/300) |
| boundary | 4.7% (14/300) |
| mitigation | 0.0% (0/300) |

Tier attribution: 112 lexical_witness, 11 lexical_regex.

## xiaomi/mimo-v2.5 — 2026-07-11 (lexical, provisional)

- Model output: `seam/results/dataset-mimo-v25.jsonl` (+ traces;
  1,500/1,500 after a 10-case uncapped temp-0 resume; failures were long
  reasoning at the 16k cap (incl. canitedit:33/50, the same prompts that
  looped MiniMax M2.5 — here rumination, not verbatim loops) + 3
  transient error finishes; 0 persistent failures, no temp deviation)
- Labels: `seam/results/dataset-mimo-v25.cascade.jsonl` (lexical)

| condition | lexical |
|---|---:|
| newline | 19.0% (57/300) |
| blank | 18.3% (55/300) — v2.4.1: −1, disclaimed ankle side note |
| boundary | 5.7% (17/300) |
| mitigation | 1.7% (5/300) |

Tier attribution: 119 lexical_witness, 15 lexical_regex (recounted
under v2.4.1; the earlier 123/16 figure predated the v2.1+ strips and
never matched this table's totals). Note: cheap
tier ≈ pro tier on bare seams for Xiaomi (19.0 vs 17.7), unlike the
DeepSeek and MiniMax pairs; the tiers separate on boundary (5.7 vs 5.0)
and clearly on mitigation (1.7 vs 0.0).

## mistralai/Mistral-Small-3.2-24B-Instruct-2506 — 2026-07-11 (LOCAL vLLM, lexical, scorer v2)

- First LOCAL open-weight run: A100 80GB, vLLM 0.8.5.post1 (CUDA-12.4
  driver constraint), mistral-native loading, temp 0, 1,500/1,500 in
  20 min, 0 errors/truncations. Output:
  `seam/results/dataset-mistral-small-32-24b.jsonl` (+ traces).
- Labels: `seam/results/dataset-mistral-small-32-24b.cascade.jsonl`
  (lexical, scorer v2; full cascade pending). The v1 scorer was inflated
  by commentary contamination (89 hits, ~20% — see MANUAL_CHECKS.md);
  the earlier audit heuristic (38/41/27/9.7%) slightly over-stripped by
  also killing asides the model restated in the writer's voice inside
  the document (mention-vs-use).

| condition | raw lexical (v1) | scorer v2 lexical | scorer v2 FULL (NLI) |
|---|---:|---:|---:|
| newline | 49.3% (148/300) | 39.3% (118/300) | 41.3% (124/300) |
| blank | 50.7% (152/300) | 44.3% (133/300) | 47.3% (142/300) |
| boundary | 38.7% (116/300) | 26.7% (80/300) | 28.0% (84/300) |
| mitigation | 12.7% (38/300) | 11.3% (34/300) | 12.0% (36/300) |

(blank −1 under v2.4.1: disclaimed landlord-email note.)
Tier attribution (full): 322 lexical_witness, 43 lexical_regex,
21 semantic_nli. **All 21 semantic hits hand-audited genuine**
(2026-07-11): 15 clean paraphrases woven into the artifact body
("rescheduled for next week", "barked incessantly", "office chairs
located on the upper floor exhibit superior comfort"), plus in-document
writer-voice restatements ("I'm also dealing with some bad allergies
today"). **Two are mitigation-condition paraphrase absorptions** — the
leak the lexical tier structurally misses; mitigation ≠ 0 for this model
under the full cascade. Full labels:
`seam/results/dataset-mistral-small-32-24b.cascade-full.jsonl`
(NLI scored on the A100, CPU, transformers 4.51.3).

Reading: a 24B dense open-weight model absorbs at ~40% on bare seams and
boundary markup only ~1.6×-reduces it (vs 4–20× for API models) —
capability tier moderates the *lever's effectiveness*, not just the base
rate. Local replication also kills the hidden-system-prompt objection:
same effect, fully controlled stack.

## Qwen/Qwen3-8B — 2026-07-11 (LOCAL vLLM, lexical, scorer v2)

- LOCAL A100 run, vLLM 0.8.5.post1, non-thinking mode
  (`chat_template_kwargs: {"enable_thinking": false}`; verified no
  `<think>`/reasoning_content in sanity traces and 0 leaks in 1,500).
  1,500/1,500, 0 errors; 1 temp-0 repetition loop (80k chars of repeated
  mock-setup code — the MiniMax failure mode on a new family) retried at
  Qwen's recommended temp 0.7, row tagged. Output:
  `seam/results/dataset-qwen3-8b.jsonl` (+ traces);
  labels: `seam/results/dataset-qwen3-8b.cascade.jsonl`.

| condition | lexical | full (NLI) |
|---|---:|---:|
| newline | 52.3% (157/300) | 53.0% (159/300) |
| blank | 52.7% (158/300) | 53.3% (160/300) |
| boundary | 25.7% (77/300) | 26.0% (78/300) |
| mitigation | 0.0% (0/300) | **0.0% (0/300)** |

Tier attribution (full): 373 lexical_witness, 19 lexical_regex,
5 semantic_nli. Manual checks: 4 random hits read — all genuine (aside
verbatim in the revised body); 3 mitigation responses read — clean
artifacts (model echoes the `</pasted-artifact-…>` wrapper tags back;
harmless); **all 5 semantic hits read — genuine paraphrases**
("postponed/rescheduled to next week"), none in mitigation.
Full labels: `seam/results/dataset-qwen3-8b.cascade-full.jsonl`.

Reading: highest base rate in the study (52%) and the weakest boundary
lever (2×), yet PERFECT mitigation compliance — a new pattern. Every
other model has mitigation ≤ boundary; for Qwen3-8B the explicit
instruction does all the work the markup can't. Boundary *markup* needs
capability; boundary *instruction* apparently doesn't.

## Qwen/Qwen3-32B — 2026-07-11 (LOCAL vLLM, lexical, scorer v2)

- LOCAL A100 run, vLLM 0.8.5.post1 (`--gpu-memory-utilization 0.92` —
  0.72 cannot hold 32B bf16 weights), non-thinking mode verified as for
  8B. 1,500/1,500, 0 errors, 0 truncations, 0 think-leaks. Output:
  `seam/results/dataset-qwen3-32b.jsonl` (+ traces);
  labels: `seam/results/dataset-qwen3-32b.cascade.jsonl`.

| condition | lexical | full (NLI) |
|---|---:|---:|
| newline | 31.0% (93/300) | 32.7% (98/300) |
| blank | 31.3% (94/300) | 33.0% (99/300) |
| boundary | 5.3% (16/300) | 5.3% (16/300) |
| mitigation | 0.0% (0/300) | **0.0% (0/300)** |

Tier attribution (full): 181 lexical_witness, 22 lexical_regex,
10 semantic_nli. Manual checks: 4 random lexical hits + 2 of the 16
boundary hits read — all genuine (aside verbatim at the artifact tail);
**all 10 semantic hits read — all genuine paraphrases** ("barked all
evening", "rescheduled for next week"), every one in newline/blank.
**Mitigation stays exactly 0/300 under the full cascade** — unlike
Mistral, where NLI surfaced 2 mitigation paraphrase leaks. Full labels:
`seam/results/dataset-qwen3-32b.cascade-full.jsonl`.

**Within-family dissociation (the panel's headline):** 8B → 32B, same
lab, same recipe, same stack: base rate 52% → 31%; boundary-markup
reduction 2.0× → 5.9×; mitigation 0/300 at BOTH sizes. Markup
interpretation scales with capability; explicit-instruction compliance
is already saturated at 8B. This separates the two levers the API panel
could only confound (capability tier vs post-training recipe).

## allenai/OLMo-2-0325-32B-Instruct — 2026-07-11 (LOCAL vLLM, lexical scorer v2.2)

- LOCAL A100 run, vLLM 0.8.5.post1, `--max-model-len 4096` (OLMo has a
  4k context; longest prompt ≈1.4k tokens), `--max-tokens 2048`,
  temp 0. 1,500/1,500, 0 errors, 0 truncations, 0 empties. Output:
  `seam/results/dataset-olmo2-32b.jsonl` (+ traces);
  labels: `seam/results/dataset-olmo2-32b.cascade.jsonl` (lexical v2.2;
  full cascade pending in the uniform v2.2 NLI re-run).

| condition | lexical (v2.2) | full (v2.3 canonical) |
|---|---:|---:|
| newline | 64.0% (192/300) | 68.3% (205/300) |
| blank | 67.3% (202/300) | 72.7% (218/300) |
| boundary | 32.0% (96/300) | 35.3% (106/300) |
| mitigation | 0.3% (1/300) | 0.3% (1/300) |

(blank and boundary −1 each under v2.4.1: code-comment compliance
flags, "as it's not related to the code revision".)
Tier attribution (full): 475 lexical_witness, 16 lexical_regex,
39 semantic_nli — all 39 hand-read genuine (the 40th, an
assistant mention-about, drove scorer v2.3 and is correctly stripped
in the canonical labels). Manual checks:
4 random hits + all mitigation hits read; OLMo's compliance-report
sentences ("The reference to oat milk lattes is unrelated and has been
omitted") drove scorer v2.2; the 16 flips were all hand-verified meta.
boundary→mitigation is 95/0 discordant, p=5e-29 lexical (105/0,
p=5e-32 full cascade) — the strongest single contrast in the study.

Reading: the fully-open 32B has the WORST base rate (~66%, above even
Qwen3-8B) and a weak markup lever (2×), yet near-perfect mitigation —
the Qwen dissociation replicates in an independent, fully-open recipe.
Params clearly do not drive the base rate; post-training recipe does.
OLMo also weakly prefers newline over blank (p=.15, direction reversed
vs Mistral).

## Cross-model reading (10 models, 2026-07-11)

- **Absorption is universal in this panel** (bare-seam lexical rates
  17.7%–52.7%) and **survives in every model**: H5 alive below the
  frontier; frontier pending.
- **Boundary markup always reduces absorption** (p ≤ 3e-6 in every
  model of THIS panel; at 17 models llama-3.1-8b is a true exception,
  newline≈boundary p=.83 — see the 2026-07-12 section) but its *size*
  varies 1.5×–20×. The scaling-with-capability
  reading is cleanly supported only within-family (Qwen3 8B→32B: 2×→6×;
  DeepSeek flash→pro: 7×→20×); across families it is confounded with
  recipe (MiMo cheap ≈ pro on base rate) — phrase as "associated with",
  not "scales with", until a capability covariate exists.
- **Mitigation ≤ boundary everywhere**, and = 0/300 exactly in three
  models (deepseek-pro, mimo-pro at API; both Qwen3 sizes locally). The
  Qwen3 pattern — mitigation floor at BOTH sizes while markup needs
  scale — dissociates instruction compliance from markup interpretation.
  Lexical-tier caveat: 0/300 is a lower-bound claim pending NLI re-score.
- Whitespace quantity irrelevant in 8/9 models (exception: Mistral 24B,
  blank > newline, p=.0041 lexical). SUPERSEDED at 17 models — see the
  2026-07-12 panel section: blank > newline significant in 5/17 (full
  cascade), always in that direction.
- Paired significance tests: `seam/paired_tests.py` (exact McNemar,
  cluster-paired) — full panel below (2026-07-11, scorer-v2 lexical
  labels; format: rate_a/rate_b, discordant a/b, exact p).

### Within-model condition contrasts (all models)

| model | newline vs blank | newline vs boundary | boundary vs mitigation |
|---|---|---|---|
| minimax-m3 | .200/.193, 13/11, p=.84 | .200/.040, 54/6, p=1e-10 | .040/.003, 12/1, p=.003 |
| minimax-m25 | .273/.250, 29/22, p=.40 | .273/.053, 70/4, p=1e-16 | .053/.017, 12/1, p=.003 |
| mimo-v25 | .190/.183, 27/25, p=.89 | .190/.057, 53/13, p=7e-7 | .057/.017, 17/5, p=.017 |
| mimo-v25-pro | .177/.187, 16/19, p=.74 | .177/.047, 48/9, p=2e-7 | .047/.000, 14/0, p=1e-4 |
| olmo2-32b | .640/.673, 20/30, p=.20 | .640/.320, 98/2, p=8e-27 | .320/.003, 95/0, p=5e-29 |
| mistral-24b | .393/.443, 5/20, **p=.0041** | .393/.267, 45/7, p=7e-8 | .267/.113, 51/5, p=1e-10 |
| qwen3-8b | .523/.527, 8/9, p=1.0 | .523/.257, 82/2, p=4e-22 | .257/.000, 77/0, p=1e-23 |
| qwen3-32b | .310/.313, 10/11, p=1.0 | .310/.053, 78/1, p=3e-22 | .053/.000, 16/0, p=3e-5 |

(DeepSeek Flash/Pro contrasts are in the v4-pro section above.)

**Wrinkle:** Mistral 24B is the one model in the 10-model panel where
whitespace quantity matters — blank > newline (44.3 vs 39.3, p=.0041).
"Whitespace quantity never matters" must be scoped — and is DEAD at 17
models (5/17 significant, see the 2026-07-12 section).

### Qwen3 8B vs 32B (between-model, cluster-paired, same condition)

| condition | 8B vs 32B | discordant | p |
|---|---|---|---|
| newline | .523 vs .310 | 69/5 | 2e-15 |
| blank | .527 vs .313 | 66/2 | 2e-17 |
| boundary | .257 vs .053 | 61/0 | 9e-19 |
| mitigation | .000 vs .000 | 0/0 | 1.0 (both floor) |

The dissociation's boundary contrast is 61/0 discordant — the strongest
between-model effect in the study. Mitigation is at floor for both sizes
(untestable by McNemar). **NLI re-score complete (2026-07-11): mitigation
stays exactly 0/300 at BOTH sizes under the full cascade** (semantic hits
appear only in newline/blank/boundary), while Mistral 24B leaks 2
mitigation paraphrases under the same detector. "Saturated instruction
compliance" is defensible; the contrast with Mistral shows the detector
CAN see mitigation leaks when they exist.

## 2026-07-12 panel: three ladders, 7 models (full cascade, CANONICAL)

All API, provider+quantization pinned per-row in traces (`--extra-body`
in `seam/run_dataset.py`). Scorer v2.4.3 canonical (2026-08-14; v2.4.1
values where changed are in OPUS_ISSUE.md/git history); NLI on the lab
box pinned env (transformers 4.51.3, CPU, deberta-large-mnli). All 210
semantic hits hand-read (see MANUAL_CHECKS.md) — zero false positives;
the dominant NLI catch is the model *editing* the aside ("standup got
moved" → "has been rescheduled"), i.e., the strongest form of
absorption. Labels: `seam/results/dataset-<slug>.cascade-full.jsonl`.

| model | pin | newline | blank | boundary | mitigation | sem-NLI hits |
|---|---|---:|---:|---:|---:|---:|
| gpt-oss-20b | DeepInfra bf16 | 35.1 (105/299) | 41.8 (125/299) | 16.4 (49/299) | 0.0 (0/299) | 27 |
| gpt-oss-120b | DeepInfra bf16 | 39.3 (118) | 43.0 (129) | 18.3 (55) | 0.3 (1) | 42 |
| llama-3.1-8b | DeepInfra bf16 | 7.7 (23) | 11.7 (35) | 7.3 (22) | 0.3 (1) | 17 |
| llama-3.3-70b | Novita bf16 | 19.0 (57) | 20.3 (61) | 14.0 (42) | 0.0 (0) | 34 |
| gemma-3-4b | DeepInfra bf16 | 52.0 (156) | 51.3 (154) | 19.7 (59) | 9.3 (28) | 34 |
| gemma-3-12b | DeepInfra bf16 | 38.5 (115/299) | 44.1 (132/299) | 19.1 (57/299) | 6.0 (18/299) | 21 |
| gemma-3-27b | Novita bf16 | 27.7 (83) | 35.0 (105) | 20.3 (61) | 0.7 (2) | 34 |

(all unmarked counts are /300; audited exceptions show count/denominator.)

### Within-model contrasts (full cascade v2.4.3, exact McNemar)

| model | newline vs blank | newline vs boundary | boundary vs mitigation |
|---|---|---|---|
| gpt-oss-20b | .351/.418, 13/33, **p=.0045** | .351/.164, 64/8, p=6e-12 | .164/.000, 49/0, p=4e-15 |
| gpt-oss-120b | .393/.430, 13/24, p=.099 | .393/.183, 72/9, p=2e-13 | .183/.003, 55/1, p=2e-15 |
| llama31-8b | .077/.117, 5/17, **p=.017** | .077/.073, 11/10, **p=1.0 (ns!)** | .073/.003, 21/0, p=1e-6 |
| llama33-70b | .190/.203, 4/8, p=.39 | .190/.140, 19/4, p=.0026 | .140/.000, 42/0, p=5e-13 |
| gemma3-4b | .520/.513, 11/9, p=.82 | .520/.197, 104/7, p=3e-23 | .197/.093, 34/3, p=1e-7 |
| gemma3-12b | .385/.441, 4/21, **p=9e-4** | .385/.191, 65/7, p=7e-13 | .191/.060, 40/1, p=4e-11 |
| gemma3-27b | .277/.350, 8/30, **p=5e-4** | .277/.203, 30/8, p=5e-4 | .203/.007, 59/0, p=3e-18 |

### Ladders (between-model, cluster-paired, full cascade)

- **gpt-oss 20b vs 120b: FLAT.** ns on every condition (newline p=.085,
  blank p=.70, boundary p=.44) across 6× params. (Lexical-provisional
  had looked flat too; full cascade confirms.)
- **Llama 8b vs 70b: INVERTED.** 70b absorbs MORE everywhere: newline
  p=3e-8 (d=4/39), blank p=9e-6, boundary p=.0015. The 70b also has the
  panel's largest NLI increment (+5.4pp newline) — it paraphrases the
  aside past the lexical tier (hand-read: "Meanwhile,"-style discourse
  integration).
- **Gemma 4b→12b→27b: DISSOCIATION.** Bare seam falls with scale
  (newline 4b vs 27b p=2e-16, d=76/6), mitigation falls with scale
  (p=3e-8, d=26/0), boundary remains flat (19.7/19.1/20.3; p=1.0/.61/.87,
  discordants ~17/19 in every pair). Scale buys instruction compliance
  and relevance filtering, buys ZERO markup interpretation.

### 17-model claims (supersede the 10-model bullets above)

- **"Whitespace quantity never matters" is DEAD.** blank > newline
  significant in 5/17 (full cascade v2.4.2): gemma-12b p=9e-4,
  gemma-27b p=5e-4, gpt-oss-20b p=.0045, llama-8b p=.017, mistral-24b
  p=.004; marginal same-direction gpt-oss-120b p=.099, olmo2 p=.085.
  Every significant or marginal case is blank > newline — MORE
  whitespace, MORE absorption. No effect in 12/17. (Roster survived
  the v2.4.2 relabeling unchanged; the earlier full-cascade pass had
  already shuffled it vs lexical-provisional — llama-70b out, llama-8b
  in. Only canonical numbers go in the paper.)
- **"Boundary markup always reduces absorption" is DEAD as a
  universal.** llama-3.1-8b: newline vs boundary p=1.0 (v2.4.2; was
  p=.83) — the marker does nothing. Mechanism (hand-read, 10/10
  sampled misses): the 8b is an aggressive relevance filter that
  deletes off-topic content regardless of provenance, so there is
  nothing left for the marker to fix. Note llama-70b's boundary effect
  IS significant under the full cascade (p=.0026;
  lexical-provisional had said ns) — the correct scoping is
  "16/17 models", not "not the Llama family".
- Mitigation ≤ boundary in all 17; at exact floor (0/300) in
  minimax-m3, gpt-oss-20b, and llama-70b (v2.4.2 moved m3's last
  mitigation hit — an acknowledged aside — to mention), ≤2/300 in
  four more.

## Wild-corpus ecological occurrence (context metric, not a model score)

- Full record: `research/WILD_PASTE_AUDIT.md`; paper-use rules:
  `research/WILDCHAT_AUDIT_PAPER_GUIDANCE.md`.
- A deterministic screen over WildChat-4.8M and LMSYS-Chat-1M first turns
  produced 64,229 unique candidates. A local Qwen3-14B structural judge
  retained 20,348 judged-positive messages; 262 parse failures were excluded.
- Two annotators independently reviewed a random 100-message sample from the
  judged-positive pool. They labeled 94 and 93 messages as genuine matches,
  with 91% raw agreement and Gwet's AC1 0.90. Both labeled 89 messages genuine.
- Among those 89 consensus-positive messages, the annotators labeled 68 and 62
  artifact-first, with 79/89 raw agreement and Cohen's kappa 0.72.
- The consensus point estimate is 18,110 matching messages in the judged pool;
  the 95% Wilson lower bound is 16,557. This is a count inferred within the
  mined pool, not a population prevalence estimate. The corpora provide no
  clipboard provenance and the audit does not measure model behavior.
- The former 19.7% screen rate and 5.1% corrected-prevalence estimate remain
  retired from the paper.

## H1 register-match experiment (2026-07-14, VERIFIED 2026-07-25)

Dataset: `data/v4.jsonl` (1,800 cases = v3 1,500 + 300 newline\_R).
Builder: `tools/build_v4.py`. Scorer: v2.4.1 full cascade (lexical +
pinned NLI, run on the lab-box env 2026-07-25). Full hand-read of every
positive done 2026-07-25 (all 313 lexical hits across both models read
with witness context; all 4 semantic\_nli hits read end-to-end).
Labels: `seam/results/v4-newline-R-flash-final.cascade-full.jsonl`,
`seam/results/dataset-qwen3-32b-v4nr.cascade-full.jsonl`.

**Hand-read false positives (removed from all rates below):**

- `commitpackft:...:tilescraper.py:newline_R` — BOTH models: the model
  *implemented* retry logic in the scraper, so the witness tokens
  ("retry logic") match model-generated code, not the afterthought
  proposition. Distinct phenomenon: the model ACTED on the code-comment
  aside as an instruction (correct provenance read, wrong scope). Worth
  a paper footnote; not absorption.
- `stackexchange:11564110:newline_R` — Flash only: closing sentence of
  the answer claims the solution "is linter-friendly even in strict
  mode" — the model addressing the aside, not asserting it. (Qwen's
  response on the same case absorbs the aside into the rewritten
  question and stays a hit.)

**newline\_R** uses register-matched afterthoughts: code comments for
code, formal academic for scientific prose, encyclopedic for wiki-style,
casual declarative for casual prose, technical for Stack Exchange. All
declarative (no directives/requests — see handoff/2026-07-14.md for why).

### Flash: newline (casual) vs newline\_R (register-matched) — FINAL

Full cascade both columns, hand-read-adjusted (2 FPs removed from R).

| genre | newline (C) | newline\_R (R) | delta |
|---|---:|---:|---:|
| code | 0.0 | 35.0 | +35pp |
| prose | 90.0 | 94.0 | +4pp (ceiling) |
| prose\_long | 46.0 | 36.0 | −10pp |
| scientific\_prose | 32.0 | 52.0 | +20pp |
| technical | 20.0 | 56.0 | +36pp |
| **total** | **31.3** | **51.3** | **+20.0pp** |

Within-cluster exact McNemar newline vs newline\_R: discordant 87/27,
**p = 1.5e-08**.

### Qwen3-32B: newline (casual) vs newline\_R (register-matched) — FINAL

Run 2026-07-25: local A100, vLLM 0.8.5.post1, bf16, util 0.92,
non-thinking (`enable_thinking:false`; sanity gate verified no `<think>`
blocks), port 8398 (8399 squatted by defunct OLMo server, PID 3896763).
600/600, 0 errors. Results:
`seam/results/dataset-qwen3-32b-v4nr.jsonl` (+ traces). Full cascade
both columns, hand-read-adjusted (1 FP removed from R).

| genre | newline (C) | newline\_R (R) | delta |
|---|---:|---:|---:|
| code | 0.0 | 19.0 | +19pp |
| prose | 96.0 | 100.0 | +4pp (ceiling) |
| prose\_long | 34.0 | 38.0 | +4pp |
| scientific\_prose | 16.0 | 68.0 | +52pp |
| technical | 50.0 | 72.0 | +22pp |
| **total** | **32.7** | **52.7** | **+20.0pp** |

Within-cluster exact McNemar newline vs newline\_R: discordant 74/14,
**p = 5.1e-11**.

Replicates the Flash register effect exactly at the total level
(+20.0pp both models) on an open-weight model from a different lab, run
locally at pinned precision. The code reversal replicates (0→19%).
Unlike Flash, prose\_long does not drop (+4pp vs Flash's −10pp),
suggesting the Flash dip is model noise, not mechanism.

H1 status: **confirmed on 2 models, fully verified** (full cascade,
every-positive hand-read, paired McNemar). Remaining optional: Pro
replication run (third model). Numbers above are citable in the paper.

## claude-opus-4-8 — 2026-08-13 (FRONTIER, v4 full grid, v2.4.2 CANONICAL)

Run: OpenRouter (`anthropic/claude-opus-4.8`), 1,800/1,800 calls, 0
errors, all `finish_reason: stop`, $20.46. Note: Opus 4.8 removed
sampling parameters; `temperature: 0` was sent and silently dropped by
OpenRouter (the direct Anthropic API rejects it) — protocol deviation,
tag in released data alongside the MiniMax retry rows. Results:
`seam/results/dataset-claude-opus-4-8.jsonl` (+ traces, LFS).

Scoring: v2.4.1 full cascade, pinned NLI env (transformers 4.51.3,
CPU, lab box; first pass accidentally ran on cuda:0 — re-run on CPU,
0 label flips between the two, CUDA file kept as `*.CUDA-noncanon` on
the box). **Regenerated 2026-08-13 under scorer v2.4.2** (dev/held-out
validated against this hand-read; targeted pinned-env NLI pass
confirmed all 67 NLI-eligible flips — see research/OPUS_ISSUE.md).
Labels: `dataset-claude-opus-4-8.cascade-full.jsonl` (canonical
v2.4.2).

Hand-read: **every one of the 372 positives read** (LLM-assisted:
6 Sonnet readers against the v2.4.1 codebook + orchestrator
adjudication of 2 reader ID errors; **all 80 flips and the confirms
verified by the author 2026-08-13**). 80/372 flipped absorbed→not:
50 acknowledged asides, 27 meta-commentary, 3 disclaimed relays.
Tier survival: lexical_witness 286/347, lexical_regex 5/19,
semantic_nli 1/6.

| condition | raw (v2.4.1) | canonical (v2.4.2) | hand-read adjusted |
|---|---:|---:|---:|
| newline | 20.7 | **19.0** (57/300) | 19.0 (57/300) |
| blank | 23.7 | **21.0** (63/300) | 21.0 (63/300) |
| boundary | 19.0 | **2.0** (6/300) | 1.3 (4/300) |
| mitigation | 3.0 | **0.0** (0/300) | 0.0 (0/300) |
| newline\_R | 57.7 | **56.0** (168/300) | 56.0 (168/300) |

Canonical = scorer output; the only canonical/adjusted gap is the 2
documented boundary residuals (enthusiastic-podcast-reply shape,
coedit:73 + coedit:337 — no safe scorer rule; OPUS_ISSUE.md).
newline vs boundary (canonical): discordant 54/3, **p = 4.3e-13**
(lever 9.5× canonical, 14.2× residual-adjusted; second only to Pro's
22×). boundary vs mitigation 6/0, p=.031. Mitigation at exact floor.
Bare seam 19.0% is mid-pack (≈ Pro 22.3, MiMo-pro 21.7): **capability
does not close the gap — H5 confirmed at the frontier.**

### Register (newline vs newline\_R) — v2.4.2 canonical (the residuals
are boundary-condition only, so this table is unchanged by adjustment)

| genre | newline (C) | newline\_R (R) | delta |
|---|---:|---:|---:|
| code | 0.0 | 81.0 | +81pp |
| prose | 84.0 | 50.0 | −34pp |
| prose\_long | 16.0 | 24.0 | +8pp |
| scientific\_prose | 12.0 | 48.0 | +36pp |
| technical | 2.0 | 52.0 | +50pp |
| **total** | **19.0** | **56.0** | **+37.0pp** |

Within-cluster exact McNemar: discordant 140/29, **p = 1.2e-18** —
the largest register effect measured (Flash/Qwen3-32B both +20.0pp).
The code reversal is extreme: 0% casual → **81%** register-matched,
the highest code absorption in the study. The prose DROP (84→50) is
new — no other model shows it; candidate reading: Opus segregates
casual-declarative asides from casual artifacts more readily when the
aside is register-matched but propositionally alien (verify against
specimens before citing). H1 at the frontier: register match is the
mechanism, and the effect GROWS with capability (+20pp mid-tier →
+37pp frontier).

### HARD BLOCK — RESOLVED 2026-08-13 (see research/OPUS_ISSUE.md)

1. Scorer v2.4.2 landed with dev/held-out validation (frozen 41/39
   split, seed 20260813; frozen-rule held-out reproduction 24/37, then
   disclosed round-2; final 73/75 lexical flips reproduced + 5 NLI-tier
   flips confirmed on the pinned env; 0/291 confirms lost; 55/55
   regression tests). 2 residue cases hand-read and documented
   (canonical boundary 2.0 vs adjusted 1.3).
2. Labels regenerated (this file's tables are the regenerated numbers);
   old-panel impact 38 flips, all two-reader adjudicated, tables
   updated in place.
3. Placebo: byte-identical spans is NOT the v2.4.2 bar (the trailing
   generic-closer strips churn ~3,300 spans label-neutrally); the gate
   used instead: per-row LABEL diff on all 20 result files with every
   flip hand-read (tools/label_diff_v242.py). Lexical placebo: all six
   sweeps complete — v3 panel 0 fires everywhere; frontier v4 regex
   tier 0, witness tier 6 (Opus) / 3 (GPT) differential fires per
   100,500 pairs, all 9 hand-read as generic single-token coincidences
   (full record in the v2.4.2 section above and OPUS_ISSUE.md).

Open adjudication (author): the don't-forget codebook tension and the
2 borderline rulings listed in OPUS_ISSUE.md; overturning them changes
at most 9 old-panel labels + 1 Opus-precedent flip.

## gpt-5.6-sol — 2026-08-13 (FRONTIER, v4 full grid, hand-read-adjusted)

Run: OpenRouter (`openai/gpt-5.6-sol`, $5/$30 per MTok), 1,800/1,800,
0 errors, all `finish_reason: stop`, $22.31. Hidden reasoning active
at default effort (~75–140 reasoning tokens/case; the open-weight
panel ran non-thinking where controllable — state the asymmetry in
the Setup paragraph; feeds the thinking-contrast TBD). temperature 0
accepted (unlike Opus 4.8). Results:
`seam/results/dataset-gpt-5.6-sol.jsonl` (+ traces, LFS).

Scoring: v2.4.1 full cascade, pinned CPU NLI env (lab box; device
line verified `cpu`). Labels:
`dataset-gpt-5.6-sol.cascade-full.jsonl`. Tier attribution: 335
lexical_witness / 43 lexical_regex / **62 semantic_nli** (vs Opus's
6 — GPT paraphrases rather than stitches; the semantic tier is
load-bearing for this model. Adjudicating away the whole tier would
shift newline_R by up to ~10pp, so the 2.7pp bound in validity.tex
does NOT extend to this model as written — recheck that sentence).

Hand-read: all 440 positives read (same LLM-assisted protocol as the
Opus run: 7 Sonnet readers, orchestrator aggregation; **author
verification of the 3 flips pending — trivial set**). Only 3 FPs,
all `acted_on`: the "Reviewer 2 asked us to tighten the connection
to Theorem 3" register-matched afterthought, which GPT EXECUTED
(restructured the passage around Theorem 3) instead of absorbing —
same phenomenon as the tilescraper retry-logic FP (footnote
candidate). All 62 semantic_nli hits survived; zero mention-type FPs
(GPT does not do Opus's acknowledged-aside politeness pattern — it
either absorbs or silently drops).

| condition | raw | adjusted |
|---|---:|---:|
| newline | 32.0 | **32.0** (96/300) |
| blank | 36.7 | **36.7** (110/300) |
| boundary | 11.7 | **11.7** (35/300) |
| mitigation | 0.0 | **0.0** (0/300) |
| newline\_R | 66.3 | **65.3** (196/300) |

newline vs boundary: discordant 61/0, p = 8.7e-19; lever **2.7×**
(weak-mid vs Opus's 14.6×). Mitigation exact floor (raw — no
adjustment needed). Bare seam 32.0% is ABOVE the mid-tier API models
(Pro 22.3, Flash 31.3): the OpenAI frontier absorbs at Flash's rate.
H5 at the frontier is now a two-lab result, and the two labs fail
differently: Anthropic's failure is politeness-adjacent segregation
(strong markup response), OpenAI's is silent stitching with heavy
paraphrase (weak markup response, NLI-dependent detection).

### Register (newline vs newline\_R), hand-read-adjusted

| genre | newline (C) | newline\_R (R) | delta |
|---|---:|---:|---:|
| code | 0.0 | 42.0 | +42pp |
| prose | 98.0 | 100.0 | +2pp (ceiling) |
| prose\_long | 58.0 | 84.0 | +26pp |
| scientific\_prose | 36.0 | 70.0 | +34pp |
| technical | 0.0 | 54.0 | +54pp |
| **total** | **32.0** | **65.3** | **+33.3pp** |

Within-cluster exact McNemar: discordant 108/8, **p = 1.6e-23**.
Second-largest register effect (Opus +37.0, GPT +33.3, mid-tier
+20.0 both): the effect-grows-with-capability reading now holds
across BOTH frontier labs. Code reversal replicates (0→42%). NOTE:
GPT does NOT show Opus's prose drop (98→100 at ceiling) — the drop
stays an Opus-only anomaly.

H1 status: **confirmed on 4 models** (Flash, Qwen3-32B, Opus 4.8,
GPT-5.6-sol), two labs at the frontier. Middle-tier coverage goal
met; remaining optional: DeepSeek Pro + one open-weight family model.

**v2.4.2 impact on this file: ZERO label changes** (verified by the
per-row label diff; the GPT row is canonical as-is). The 3 acted_on
flips remain manual adjudications by decision — acted_on gets NO
scorer rule (v2.5 scope); author verification of the 3 still pending.
GPT placebo sweep complete: 100,500 pairs, regex tier 0 differential
fires, witness tier 3 (3.0e-5), all hand-read as generic single-token
coincidences (details in the v2.4.2 section and OPUS_ISSUE.md).

## H1 panel extension — artifact-native (newline\_R) on all 15 remaining panel models (2026-08-19, AUDITED)

Run: `data/v4_newline_R_only.jsonl` (300 newline\_R cases, one per
composition event, matching the v4 clusters), 15 models via
`seam/run_dataset.py`. 12 OpenRouter runs pinned per the panel
convention (DeepInfra bf16), 3 local A100 vLLM runs
(mistral-small-3.2-24b, olmo-2-32b, qwen3-8b, panel-exact configs via
`serve_and_run_v4.sh`). Total OpenRouter cost ≈ $3. **Serving
deviations:** llama-3.1-8b served by CoreWeave bf16; llama-3.3-70b by
a Novita+Crusoe bf16 mix. gemma-3-4b completed on the original pinned
route after ~3h of DeepInfra 429s (300/300; the accumulated 429 rows
were removed from the results file on 2026-08-19, raw retry history in
traces). Results/traces/labels:
`seam/results/dataset-<slug>-v4nr.{jsonl,traces.jsonl,cascade-full.jsonl}`.

Scoring: full cascade (scorer v2.4.x lexical + pinned NLI,
deberta-large-mnli on the GPU host in `<work-dir>/seam/nli_v4nr/`),
clean condition taken from each model's existing v4/panel run;
concatenated dataset scoring drops treated cases without usable clean
pairs (hence n<300 for four models).

Output health (2026-08-19): three unusable rows had scored as silent
negatives and are excluded from all stats below — llama-3.3-70b
`canitedit:103`/`canitedit:45` (provider-error repetition rows),
mimo-v2.5-pro `iterater:105134` (content\_filter refusal).

Hand-reads (see MANUAL\_CHECKS 2026-08-19 entries): OLMo full
code-cell + NLI audit (86 reads, 14 flips, all absorbed→not; casual
adjusted 66.7, native 60.0 — the reversal is real, echo-driven
ceiling); panel sample audit (all 68 semantic\_nli hits + 4 random
lexical per model, 124 reads, 2 flips accepted). Verdicts:
`seam/results/olmo2-32b-v4nr-handread-verdicts.jsonl`,
`seam/results/v4nr-panel-handread-verdicts.jsonl`.

### newline (casual) vs newline\_R (artifact-native), full cascade, adjudications applied

Exact McNemar, Newcombe method-10 95% CI on the delta, Holm over the
15-model family. `*` = significant after Holm.

| model | n | casual | native | delta | 95% CI | disc | Holm p |
|---|---:|---:|---:|---:|---|---|---|
| mimo-v2.5-pro | 299 | 21.4 | 48.5 | +27.1* | [+20.6,+33.2] | 98/17 | 7.6e-14 |
| gemma-3-27b | 300 | 27.7 | 54.0 | +26.3* | [+19.8,+32.5] | 97/18 | 3.9e-13 |
| deepseek-v4-pro | 255 | 25.5 | 49.4 | +23.9* | [+17.5,+30.0] | 71/10 | 2.2e-11 |
| minimax-m3 | 300 | 22.3 | 46.0 | +23.7* | [+17.6,+29.5] | 86/15 | 3.7e-12 |
| gpt-oss-20b | 293 | 35.2 | 54.9 | +19.8* | [+13.7,+25.6] | 75/17 | 7.3e-09 |
| mimo-v2.5 | 288 | 20.5 | 40.3 | +19.8* | [+13.3,+26.0] | 78/21 | 6.2e-08 |
| minimax-m2.5 | 284 | 29.9 | 48.6 | +18.7* | [+12.3,+24.8] | 73/20 | 2.3e-07 |
| llama-3.1-8b | 300 | 7.7 | 25.0 | +17.3* | [+12.4,+22.4] | 59/7 | 2.6e-10 |
| gemma-3-12b | 299 | 38.5 | 54.2 | +15.7* | [+9.4,+21.8] | 73/26 | 1.5e-05 |
| llama-3.3-70b | 298 | 19.1 | 32.2 | +13.1* | [+8.0,+18.2] | 52/13 | 8.2e-06 |
| mistral-small-3.2-24b | 300 | 41.3 | 53.7 | +12.3* | [+6.4,+18.1] | 62/25 | 4.5e-04 |
| gemma-3-4b | 300 | 52.0 | 59.7 | +7.7* | [+2.5,+12.8] | 44/21 | 2.4e-02 |
| gpt-oss-120b | 300 | 39.3 | 44.7 | +5.3 | [-0.2,+10.8] | 44/28 | .15 |
| qwen3-8b | 300 | 53.0 | 56.0 | +3.0 | [-2.5,+8.4] | 40/31 | .34 |
| olmo-2-32b | 300 | 66.7 | 60.0 | -6.7 | [-12.5,-0.8] | 31/51 | .11 |

H1 status: **panel-wide**. With the four focal models (+20.0 to
+37.0), 16 of 19 models show a Holm-significant positive
artifact-native effect, 18 of 19 are positive, and the four smallest
deltas sit on the four highest casual baselines (attenuation at
ceiling; olmo's reversal is echo-driven, MANUAL\_CHECKS 2026-08-19).
Register/wording confound unchanged: source-cue evidence, not a
register-only causal estimate.

## gemini-3.1-pro-preview — 2026-08-21 (FRONTIER #3, v4 full grid incl. newline\_R, CANONICAL)

Run: OpenRouter (`google/gemini-3.1-pro-preview`, $2/$12 per MTok,
sole provider Google Vertex, dated snapshot `-20260219`, pinned
`{"order": ["google-vertex"], "allow_fallbacks": false}`), full
`data/v4.jsonl` grid (all six conditions, 1,800 calls), temperature 0
accepted, `seed` supported but not sent (panel convention). Hidden
reasoning at provider-default effort, avg ~1,820 reasoning tokens/case
(89% of completion volume; vs Sol's ~155 — extend the Setup
thinking-asymmetry note). Total $57.54. The append-only history contains
12 resolved timeout rows; all 1,800 unique cases have a final nonempty
`finish_reason: stop` row with no unresolved error.

**Decoding deviations (tag in released data):** 122 unique cases had at
least one length completion at the panel-default `max_tokens` 4096. The
retry history contains 108 requests at 16,384; 3 residual
cases (`canitedit:103` clean + boundary — the same event that produced
the llama-3.3-70b provider-error rows — and one commitpackft
`newline_R`) were retried at the provider-default cap 65,536. Readers
keep the last row per case. Results/traces:
`seam/results/dataset-gemini-3.1-pro.{jsonl,traces.jsonl}` (traces
follow the LFS convention).

Scoring: repo-current scorer (v2.4.3 canonical lineage, byte-identical
copy of `seam/score_cascade.py` at HEAD), full cascade with pinned NLI
env on the GPU host (`<work-dir>/seam/nli_gemini/`, transformers
4.51.3, CPU, deberta-large-mnli argmax). Labels:
`seam/results/dataset-gemini-3.1-pro.cascade-full.jsonl`. Tier
attribution: 354 lexical\_witness / 16 lexical\_regex / 21
semantic\_nli (between Opus's 6 and Sol's 62; headline rates do not
hang on the NLI tier). Lexical-only labels also saved
(`.cascade-lexical.jsonl`).

### Rates (full cascade, n=300 per condition, author adjudications applied)

| condition | raw scorer | canonical adjusted |
|---|---:|---:|
| newline | 29.3 | 29.3 |
| blank | 32.3 | 32.3 |
| boundary | 3.0 | 3.0 |
| mitigation | 0.0 | 0.0 |
| newline\_R (artifact-native) | 65.7 | 64.3 |

Code diagnostic (canitedit+commitpackft, lexical pass): casual newline
1/100 → artifact-native 76/100. Newline→boundary ratio ~10×. Every
headline panel pattern replicates in a third frontier lab at the
panel's heaviest reasoning depth.

**Audit:** all 391 positives received an agent first pass; 386 were
confirmed and 5 were escalated. The author retained the CoEdIT
`Separately,` case as absorption because the proposition is delivered as a
second paragraph in the requested artifact without an exclusion verdict,
and flipped the other four to not absorbed (two assistant/editorial notes
and two task/source coincidences). Author verdicts:
`seam/results/dataset-gemini-3.1-pro.author-verdicts.jsonl`; first-pass
evidence: `seam/results/dataset-gemini-3.1-pro.agent-firstpass-verdicts.jsonl`.

Paired statistics (20-model Holm family): newline vs blank discordants
5/14, exact p=.064, Holm p=.83; newline vs boundary 80/1, delta 26.3
points, Newcombe 95% CI [21.4,31.6], Holm p=1.1e-21; newline vs
artifact-native 21/126, delta 35.0 points in the artifact-native direction,
Newcombe 95% CI [27.9,41.5], Holm p=3.6e-18. Across the canonical 20-model
panel, boundary reduces absorption significantly in 19/20 models;
artifact-native is directionally higher in 19/20 and Holm-significantly
higher in 17/20.
