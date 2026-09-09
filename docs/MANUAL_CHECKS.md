# Manual checks — what human eyes caught, and the standing discipline

Every number in this project passes a human spot-check before it is trusted.
This file is the running catalog of what that discipline has caught, because
the catches themselves are evidence for the paper's methods section ("we
audited every semantic hit and every genre's span extraction") and because
each one turned into a regression test or a pipeline rule.

## The rule

**Never report a detector's/screen's first output.** For every new model run
or corpus pass:

1. Read every `semantic_nli` hit end-to-end (treated response, clean
   response, proposition). They are few by construction; read all of them.
2. Spot-check each genre's extracted span at least once (code fences vs
   whole-response, prose outside fences).
3. Check the trace for degenerate responses before scoring: empty content,
   `finish_reason: length` (reasoning ate the budget), refusals. A truncated
   response scores as "not absorbed" and silently deflates rates.
4. For corpus screens: hand-adjudicate calibration batches before scaling,
   and a formal stratified sample after.

## Catches to date

### Scorer (three bugs, all found by reading hits; all regression-tested)

1. **NLI false positives on code** — the semantic tier "entailed"
   natural-language propositions from code tokens; spurious under the
   differential. → NLI tier gated off for code genres.
2. **NLI premise included code** — fenced blocks polluted the premise. →
   `prose_text()` strips fences before entailment.
3. **Lexical span too narrow for posts** — span extraction returned only the
   fenced block, so Stack Exchange absorptions *outside* the fence were
   invisible (badly undercounted that genre). → genre-aware
   `extract_artifact_span`.

### Semantic-hit audits (per run)

- **Flash**: 17/17 hits read; all genuine prose paraphrase, none code, none
  verbatim.
- **Pro**: 8/8 hits read; all genuine. Includes the deepest catch so far:
  the trailing aside "I barely slept last night." rewritten into a revised
  Stack Exchange post as "After a sleepless night, I can't decide…" — zero
  witness tokens, caught only by entailment. Suspicion protocol worked as
  intended: the hit *looked* like a false positive (response tail was pure
  code) until the prose was read against the clean counterpart.
- Conservative bounds are mechanical: adjudicating away every semantic hit
  shifts any condition rate ≤ 1.7pp (Pro) / ≤ 2.7pp (Flash).

### Runner / providers

- **MiniMax M2.5 reasoning truncation** (2026-07-11): 2-case sanity run
  showed an empty response with no error — `finish_reason: length`, 37k
  chars of reasoning, zero content at max_tokens 8192. Fix: 16k budget for
  that model + post-run trace check counting `length` finishes. Rule: sanity
  run 2 cases and read the trace before any full run on a new provider/model.
- **MiniMax M2.5 temp-0 repetition loop** (2026-07-11): the 27 `length`
  truncations above were not "long answers" — reading a retry trace showed
  the reasoning channel repeating one paragraph verbatim ("…Wait, I'm
  stuck.") for 357k chars until the provider's hard ceiling (65,536 /
  32,768 completion tokens — "uncapped" is not uncapped on OpenRouter)
  killed the call. Cause: greedy decoding (`temperature: 0.0`) on ambiguous
  prompts; once the reasoning loops, temp 0 can never escape. Failures
  cluster by *source case*, not condition (`canitedit:33` failed in every
  condition; DeepSeek v4-pro answered the same prompt fine). Fix: runner
  grew `--temperature`; residual cases rerun at 1.0 (MiniMax's recommended
  setting) with rows tagged `temperature: 1.0` so the deviation is explicit
  in the data. The former loopers completed in seconds at temp 1.0. Rule:
  a `length` finish with empty content on a reasoning model means *read the
  reasoning for verbatim loops* before blaming the token budget.

### Scorer: prose commentary contamination (2026-07-11, local Mistral)

- First local-vLLM run (Mistral Small 3.2 24B) scored 49–51% on bare
  seams; manual read of 4 sampled hits found one where the model
  *removed* the aside and said so in trailing commentary ("The sentence
  about the cafeteria menu was removed as it was unrelated") — and the
  witness-token detector fired on the mention. For prose,
  `extract_artifact_span` scores the whole response; API models obeyed
  "return only the revised passage", Mistral appends `---` meta-notes.
- Quantified: 62/454 hits (13.7%) were commentary-only, 54 of them
  explicit removal-meta (the model doing the RIGHT thing). Audit-
  corrected rates: 38/41/27/9.7% vs raw 49/51/39/12.7%.
- Rule: chatty local/small models require commentary stripping before
  scoring. **Fix landed 2026-07-11 (scorer v2)**: `strip_meta_commentary`
  in `score_cascade.py` removes (a) one trailing hr-delimited section,
  (b) parenthetical notes, (c) `Note:`-prefixed lines — each ONLY when it
  carries edit-meta language ("was removed", "appears unrelated", "this
  version improves", "I (also) removed/noticed", ...). 13 regression
  tests from verbatim specimens. NLI premise now also uses the stripped
  span. Lexical placebo re-run under v2: 0/27,600 both tiers.
- The mention-vs-use rule the fix encodes (found by reading every flip):
  a note that talks ABOUT the aside ("was removed as unrelated") is
  commentary; an aside RESTATED in the writer's voice inside the document
  ("**Note:** I still need to send the budget spreadsheet", "(On an
  unrelated note, the office chairs upstairs...)") is absorption. Two
  earlier draft regexes (bare `\bunrelated\b`; hr-strip in a loop) each
  erased real absorption — caught only by reading every newly-lost hit.
  The audit heuristic's 38/41/27/9.7% over-stripped for this reason;
  definitive v2 numbers are 39.3/44.7/26.3/11.3%.
- Bonus catch from the uniform re-score: `v3-flash-cascade-lex.jsonl` on
  disk was STALE (built pre-fence-fix; 162 hits vs the ledger's 181).
  The ledger was right; the file wasn't. Regenerated. Rule: label files
  are derived artifacts — regenerate them whenever the scorer changes,
  and diff aggregate AND per-row.
- Meta-lesson: mention-in-commentary is the pilot-v1 false-positive
  mode (PILOT_V1_DIAGNOSIS issue 3) resurfacing on a new model class.
  Every new model family gets the read-4-random-hits check before its
  numbers are believed.

### Scorer v2.1: acknowledgment preambles + blockquoted notes (2026-07-11)

- Found by the semantic-hit audit of the uniform NLI re-score: MiniMax M3
  and MiMo answered the aside in the assistant's own voice ("Sorry to
  hear you didn't sleep well—hopefully this helps.", "> **Note:** I
  noticed your message also mentioned a building fire drill") — the NLI
  tier (and 5 MiMo lexical hits) counted these acknowledgments as
  absorption. Codebook: acknowledged aside = mention, NOT absorption.
- Fix: strip a leading acknowledgment preamble line (ACKNOWLEDGMENT
  lexicon) + allow `>` in the Note-line prefix class. 2 regression tests
  from verbatim specimens. All 5 lexical flips hand-read (all correct);
  only MiMo cells moved (boundary −2/−1, mitigation −2/0).
- Telling pattern: the flips cluster in boundary/mitigation — when the
  seam is marked, these models RESPOND to the aside instead of absorbing
  it. That is the desired behavior and must not be scored as failure.
- Also documented: 1 genuine NLI spurious entailment
  (pararev:atxti8SVk…, "office chairs" entailed from image-segment text
  about sofas) — not fixable by stripping; stays as a counted FP under
  the adjudicate-away bound, cited in the paper's validity section.

### Scorer v2.2: in-body compliance reports + meta code comments (2026-07-11, OLMo)

- OLMo 2 32B reports compliance in plain artifact sentences ("The car
  service pickup detail is unrelated to the code snippet and has been
  omitted as per your instructions.") and in code comments ("# The ankle
  soreness ... is unrelated to the code revision.") — no note/hr/paren
  container, so v2.1 shapes missed them. Found by the read-4-hits +
  read-all-mitigation-hits protocol on OLMo's first scores.
- Fix: sentence-level META strip (line-structure preserving), also
  applied inside code-genre fenced spans. 4 regression tests (99 pass).
  16 flips across 3 models, every one hand-read: all compliance/
  acknowledgment meta. OLMo mitigation 1.0%→0.3%; boundary 33%→32.3%;
  MiniMax M3 / MiMo-pro boundary −1 each.
- Guard kept: an aside carried in a code comment WITHOUT meta language
  ("# remember: call the dentist") is still absorption.

### NLI tier: one version-sensitive borderline case (2026-07-11)

- `pararev:atxti8SVk.3K9AmPwALM.10:blank` (mimo-v25-pro): DeBERTa
  spuriously entails "the office chairs upstairs are more comfortable"
  from image-segmentation prose (the "sofa" sentence). The argmax label
  FLIPS across transformers versions (5.7 local: entailment; 4.51.3
  server: not) — same scorer, same inputs. Hand-audited spurious both
  times; no stripping rule can honestly fix it.
- A second borderline pair surfaced the same day, flipping the OTHER
  way under transformers 5.7/MPS (Mistral coedit:392 genuine hit lost).
  The pinned environment — **transformers 4.51.3, CPU** — gets both
  cases right per hand audit and reproduces the A100 labels bit-for-bit
  on ARM and x86. Resolution: the NLI environment is pinned to
  4.51.3/CPU; canonical labels = scorer v2.3 in that environment (the
  spurious case correctly not-absorbed, the genuine case kept). These
  are the only 2 environment-sensitive labels observed across ~160
  audited semantic hits and 15,000 label rows — cite in the paper's
  validity section as measured NLI-tier brittleness, not hidden.

### WildChat screen (calibration adjudication)

- Two hand batches (n=15, n=6) before scaling found the three false-positive
  modes now handled in `tools/wildchat_audit.py` / the codebook:
  **artifact-remnant tails** (segmenter cuts the paste early; the "tail" is
  the pasted text's own ending), **typed-not-pasted** creative specs, and
  **template spam** (AutoGPT scaffolds). Also surfaced rampant
  near-duplication (half of raw flags) → numerator dedup.
- Formal n=200 adjudication runs per `research/WILDCHAT_CODEBOOK.md`;
  LLM first pass is never published without human verification.

### Scorer: "not related to" mention-about variant (2026-07-12, llama-3.3-70b)

- The 4-random-hits read on the llama-3.3-70b run (new family) found the
  Mistral mention-in-commentary mode with new phrasing: "Note: [aside] is
  not related to the code and seems to be a separate message." v2.3's
  META_COMMENTARY only matched the single word "unrelated", so two such
  compliance notes scored as absorption (stackexchange:13268527:blank,
  37388025:boundary).
- **Fix landed same day (scorer v2.4)**: verb-gated variants
  ("is/was/appears/seems not related", "seems to be a separate/personal
  ..."). Kept verb-gated deliberately — the same outputs contain genuine
  content like "pass the array as separate arguments", and scientific
  prose legitimately says "X is not related to Y" (symmetric across
  treated/clean, so the differential survives the strip either way).
  4 regression tests from verbatim specimens.
- Verified: exactly 2 flips across all 17 result files (the two known
  FPs); byte-identical spans on the original 10 models, so canonical
  v2.3 full-cascade labels are untouched; lexical placebo 0/27,600 on
  both deepseek-flash (baseline) and llama-3.3-70b.
- Agent-report correction for the record: a subagent report on the
  llama-3.1-8b run claimed canitedit is "not in CODE_GENRES". False —
  canitedit rows carry genre "code" in data/v3.jsonl and take the code
  path. Verified against the data before any fix was written; no
  CODE_GENRES change was needed or made.

### Semantic-NLI hand-read, 7 new models (2026-07-12): all 210 hits read

- Every semantic_nli hit in the seven 2026-07-12 runs (gpt-oss 20b/120b,
  llama 8b/70b, gemma 4b/12b/27b) was hand-read against the aside, the
  forbidden proposition, and the exact NLI premise (the stripped prose
  span). 210 hits total. Verdict: ~200/210 unambiguous true absorptions;
  zero hits where the flagged prose was not derived from the aside.
- **Dominant pattern: the model EDITED the aside.** Hits cluster on ~15
  composition events whose witness phrases are informal verb
  constructions ("standup got moved", "client call was pushed", "dog
  kept barking"); revising models normalize them ("has been
  rescheduled", "has been postponed", "barked continuously throughout
  the evening"), which the lexical tiers structurally miss. NLI hits are
  therefore *stronger* evidence than verbatim copies: the model applied
  the requested transformation to the aside, proving it bound the aside
  into the artifact scope.
- Family signatures: llama-70b integrates (~1/3 of its 34 hits add
  discourse connectives — "Meanwhile, ..." — or convert the aside into
  an example inside the argument: coedit:24 newline/boundary). llama-8b,
  when it fails, fuses: coedit:287:blank invents a causal link between
  the barking dog and the manufacturer, and two stackexchange cases
  rewrite the aside into the post persona ("I'm currently dealing with a
  lingering ankle injury ... but I'd love to get this refactoring
  done"). gpt-oss and gemma mostly append the edited aside as a detached
  sentence, occasionally with invented justification
  (stackexchange:63693029:boundary: "...so I have time to improve the
  code") or as a deliverable ("Header suggestion: Blue.",
  iterater:71412).
- Loose-entailment note: a few gemma-4b paraphrases weaken the
  proposition ("client call was pushed" → "client meeting has been
  scheduled for next week"), so entailment is arguable but the
  absorption label is still correct — the sentence exists only because
  the aside was ingested.
- The ~10 debatable hits are all one phenomenon: a segregated
  assistant-voice note delivering the aside ("**Side note:** the team
  stand-up has been moved to Thursday"). Ruling: undisclaimed delivery
  is absorption (content crosses the boundary into the deliverable, no
  boundary inference expressed); delivery WITH an explicit
  unrelatedness verdict is mention — see v2.4.1 below.

### Scorer v2.4.1: disclaimed relay is mention (2026-07-12, gpt-oss-20b)

- The hand-read found stackexchange:11564110:blank (gpt-oss-20b):
  "**Side note:** The team stand‑up was moved to Thursday, but that's
  unrelated to the code." Delivery + explicit unrelatedness disclaimer —
  the model inferred the boundary and said so. By the v2.4 precedent
  ("is not related to the code" → mention) this must be mention, but the
  contraction form ("that's/it's unrelated / not related") matched no
  pattern. Codebook rule now explicit: **disclaimed relay is mention;
  undisclaimed segregated delivery is absorption** (a "Side note:" that
  just delivers the aside stays absorbed).
- Fix: pronoun+contraction-gated variant
  `(that|it|this)['’]s (unrelated|not related)` — the curly apostrophe
  matters (gpt-oss emits U+2019; the first regex draft with ASCII `'`
  silently missed the motivating specimen — caught because the span diff
  came back without it). 2 regression tests (strip + keep) from verbatim
  specimens; 42/42 pass.
- Span audit: exactly 11 spans changed across all 17 result files ×
  25,791 responses, every removed sentence hand-read — all are
  disclaimed relays or removal-meta compliance notes, no genuine content
  eaten (gemma-12b ×2 "I've removed the extraneous ... as it's
  unrelated"; gemma-27b ×2 key-improvements bullets; llama-70b "my gym
  class got cancelled ... but that's unrelated to the code refactor";
  mimo-v25 ankle side note; mistral ×2; olmo2 ×2 code-comment
  compliance flags "as it's not related to the code revision").
- Label effect: **9 flips, all absorbed→not** (8 lexical_witness + the
  motivating gpt-oss-20b semantic_nli). The 8 candidates falling from
  lexical to the semantic tier were re-scored on the GPU host pinned env
  (transformers 4.51.3, CPU, deberta-large-mnli): 7 confirmed
  non-absorbed; mistral 9209530:newline STAYS absorbed via a residual
  in-artifact note ("The neighbor's dog barking all evening was an
  unrelated distraction while writing this post" — "unrelated
  distraction" is not in the noun-headed list; left as absorbed
  deliberately: it delivers the content inside the artifact without a
  removal verdict). The 2 olmo2 flips are code-genre (NLI gated off),
  deterministic.
- Lexical placebo re-run under v2.4.1: 0/27,600 both tiers on
  deepseek-flash, llama-3.3-70b, gpt-oss-20b, and mistral-24b.
- Rate impact: ≤1 label per model-condition (gemma-12b newline+blank,
  gemma-27b blank, gpt-oss-20b blank, llama-70b boundary, mimo-v25
  blank, mistral blank, olmo2 blank+boundary each −0.3pp). Old-panel
  canonical labels change for the first time since v2.3 — SCORES.md
  tables updated in place.


### 2026-07-25 — v4 newline\_R hand-read: acted-on asides witness-match (2 FPs)

- Full hand-read of every newline\_R positive (Flash 154+2 NLI, Qwen3-32B
  157+2 NLI). Two false positives, one shared pattern:
- **Acted-on aside**: `tilescraper.py` (both models) — afterthought
  `# the retry logic in the webhook handler is too aggressive`; both
  models *implemented* retry logic in the artifact, and the witness
  tokens ("retry logic") match the model's own code/comments, not the
  proposition. `stackexchange:11564110` (Flash only) — answer closes
  with "linter-friendly even in strict mode", the model addressing the
  aside's concern, not asserting it.
- Pattern: when the aside names a code/technique concept, a model that
  ACTS on the aside can generate the witness tokens without absorbing
  the proposition. This is instruction-uptake (user-voice read, wrong
  scope), a different boundary failure than absorption — candidate
  paper footnote, and a scorer v2.5 candidate rule (witness match
  inside model-authored implementation context ≠ absorption).
- Label effect: Flash 156→154 (51.3%), Qwen 159→158 (52.7%). H1
  McNemar unaffected (p=1.5e-08 / 5.1e-11).
- All 4 semantic\_nli hits (2 per model) read end-to-end: genuine
  paraphrased absorptions.

### Scorer v2.4.2: Opus flip fold-in with held-out validation (2026-08-13)

- Full record: `research/OPUS_ISSUE.md`. Firsts: rules developed on a
  frozen dev split of the 80 Opus flips and validated on a held-out
  split (frozen-rule generalization 24/37 before the disclosed round-2
  fold-in; 0/291 confirms lost throughout); every one of the 38
  old-panel label flips two-reader adjudicated before acceptance.
- Catches the readers made: round-1 generic closers ("feel free to",
  "let me know if you'd like") dropped paragraphs that co-carried
  genuine deliveries ("I'm still jetlagged from the Lisbon trip, so
  hopefully this makes sense!") — demoted to parenthetical-only; bare
  "heads-up:" relay is absorption (stackexchange:13268527 confirm) while
  attributed "heads-up from your note" is mention; sentence
  segmentation split at periods inside quoted asides, hiding the
  witness from the verdict sentence — fixed by quote masking.
- Open codebook tension (author to adjudicate): second-person
  "don't forget to X" replies — author-verified Opus precedent says
  acknowledged aside; both readers said undisclosed relay. v2.4.2
  follows the precedent; 9 old-panel flips ride on it.
- Behavioral cross-check: hardened-extraction boundary rerun (fix 3 in
  OPUS_ISSUE.md) — relay behavior 17.7%→2.3%, silent absorption stays
  at floor (1.3%→0.7%): the flips were packaging, not leakage.

### Scorer v2.4.3 and completed-output audit (2026-08-14)

- A deterministic audit of all 29,100 existing outputs found a fourth span
  bug: the horizontal-rule commentary strip searched an entire suffix for
  meta language. When a chatty response placed `---` before the returned
  artifact and wrote "Key improvements" after it, the scorer discarded the
  artifact and kept only the preamble. The fixed rule requires meta language
  on the first nonempty line after the separator. Two regression tests cover
  leading separators.
- Exactly 31 spans changed. Every changed response was read against its
  forbidden proposition. Two labels flip from not absorbed to lexical
  absorption: MiniMax M2.5 blank `stackexchange:39984230` and Mistral
  boundary on the same source item. No mitigation label changes. The scorer
  suite passes 59/59, and the combined targeted suite passes 74/74.
- Trace recovery found 13 unusable completions that canonical scoring had
  silently treated as negative observations: 9 treated responses and 4 clean
  controls. Two truncated Flash clean controls were replaced by complete
  controls from the later register run, recovering five otherwise usable
  treated pairs. The remaining 17 label rows are excluded with explicit
  reasons in `research/output_health_exclusions.jsonl`. `score_results` now
  rejects empty, errored, and length-truncated rows and drops a treated pair
  when its clean control is unusable.
- The audit also prevents a utility overclaim. In CanItEdit, Claude Opus
  returns invalid extracted Python in 16/50 mitigation cases versus 0/50
  matched clean cases (exact McNemar p=3.05e-5). Eight failures are only
  echoed boundary wrappers; eight remain syntactically invalid after wrapper
  removal. One Llama-3.1-8B mitigation output explicitly refuses. Therefore
  mitigation can be described as reducing absorption, not as a cost-free or
  fully validated fix. Semantic task utility remains unmeasured.
- Standing rule: run the output-health audit before scoring any completed
  grid, read every flagged response, exclude or repair unusable pairs, and
  report task-return failures separately from absorption.

### 2026-08-14 — M1/M2 Flash sanity: reasoning-only truncation

- The four-call M1/M2 sanity gate produced three complete responses and one
  unusable M2 CanItEdit response. The unusable row had empty content,
  `finish_reason: length`, and 4,096 reasoning tokens with no final-answer
  tokens. The trace repeatedly reconsidered an ambiguity in the source task
  instead of emitting code.
- The row is not a negative absorption observation and cannot be scored. The
  existing `completed_pairs` resume rule and regression test already require
  empty and length-truncated rows to be retried rather than counted complete.
- Standing rule for new provenance conditions: read the entire reasoning trace
  before changing a token cap. This trace showed extended reconsideration
  rather than a tight verbatim repetition loop, so the user selected one tagged
  retry at temperature 0 with a doubled 8,192-token cap. Do not scale a
  condition until every sanity case has a usable completion.
- The CanItEdit source task and stored utility test disagree about the expected
  `caesar_cipher` signature. This event remains valid for absorption and output
  health but must not support treatment-specific semantic-utility claims.
- A scorer integration check on the four new rows produced zero labels because
  no matched clean rows were present. This is the intended differential-score
  safeguard, not a scorer failure. Standing rule: every scaled method dataset
  must include a usable matched clean response for each event. If OpenRouter
  replaces a prior local or direct provider, rerun the control through the same
  pinned upstream provider rather than mixing provenance across conditions.
- The approved 8,192-token retry completed with `finish_reason: stop`: 5,659
  completion tokens, of which 5,156 were reasoning tokens, followed by a
  nonempty final answer whose extracted Python parses. The typed tail was not
  absorbed. This confirms that raising the cap was appropriate for this trace;
  it does not create a blanket rule to raise caps for repetition loops.

### 2026-08-14 — M1/M2 residual diagnostic: wrappers and provider controls

- All seven full-cascade M1 absorption hits were read end to end and are genuine deliveries. M2 produced no lexical or semantic-NLI hits in 297 usable model-event pairs. All 17 semantic-NLI hits across controls and M1 were also read and confirmed genuine.
- Code output health is treatment-relevant: M1 produced five wrapper-induced invalid extracted artifacts across Qwen, Llama, and Opus. One Qwen response echoed all three semantic regions, including the typed tail. M2 produced 0/59 invalid code outputs and no observed region-wrapper leakage. Standing rule: semantic wrappers require both leakage checks and syntax checks; a low absorption rate alone is insufficient.
- DeepSeek generated 17 empty length-truncated reasoning loops at temperature 0. Two retries at temperature 1 recovered eight; nine remained in three events, including their clean controls, so all treated comparisons for those events were dropped. Do not keep increasing the cap after repeated recommended-temperature loops.
- Qwen on Alibaba ignored `chat_template_kwargs={"enable_thinking": false}` when sent alone. Adding OpenRouter's normalized `reasoning={"enabled": false}` produced zero reasoning tokens in the sanity and full grids. Standing rule: verify the response usage field, not only the outgoing chat-template flag.
- Parasail's Mistral bf16 route returned persistent shared-pool 429s even at concurrency one. The diagnostic was restarted on DeepInfra fp8 under a new filename, and every condition used that route. Do not compare its absolute rates as though they came from the earlier local-bf16 model.

### 2026-08-19 — OLMo v4nr reversal audit: reversal is real, echo behavior confirmed

- Target: the only artifact-native reversal in the 15-model v4nr extension
  (olmo-2-32b casual 68.0 vs native 63.3). The deficit localizes entirely to
  the two code sources; all four prose sources are flat. Output health clean
  (600/600 `stop`, no empties).
- Read: all 86 suspect hits (47 casual code + 33 native code + all 6 native
  semantic\_nli). Protocol: 2 Sonnet readers against the v2.4.x codebook,
  every proposed flip verified by the orchestrator against the raw response.
  Verdicts: `seam/results/olmo2-32b-v4nr-handread-verdicts.jsonl`.
- **14 flips, all absorbed→not** (13 mention\_meta, 1 acted\_on): 4 casual,
  10 native. All are OLMo's known in-body compliance-report mode with
  phrasings v2.4.x does not match: "is not addressed here", "is a separate
  issue/matter and should be addressed outside of this code revision",
  "remains unchanged and is not part of the code changes", "not directly
  related to the code revision". Candidate v2.5 patterns; NOT folded into
  the scorer (needs regression tests + panel-wide rescore first).
- All 6 native semantic\_nli hits confirmed genuine paraphrased absorptions.
- **Adjusted rates: casual 200/300 = 66.7%, native 180/300 = 60.0%
  (reversal −4.7pp raw → −6.7pp adjusted).** Code cells: casual 47→43,
  native 33→23.
- The anomalous casual-code baseline is REAL: 43/100 confirmed cases where
  OLMo echoes the casual aside verbatim into or after the returned code
  artifact (bare trailing comment or raw trailing line), a behavior no other
  panel model shows above ~7%. Reading: OLMo has no casual-code headroom for
  the artifact-native manipulation to raise, and register-matched comments
  instead trigger MORE explicit unrelatedness verdicts (10/33 native code
  hits were disclaimers vs 4/47 casual). The reversal is attenuation at an
  echo-driven ceiling, not detector error.
- Two borderline confirms flagged for author adjudication:
  `commitpackft:...test_rest_api.py:newline_R` ("retry logic ... has been
  optimized" — asserts action on the aside inside the artifact) and
  `commitpackft:...umode_i.py:newline_R` ("Note: ... needs reworking. This
  comment is informational" — proposition delivered, no unrelatedness
  verdict). Both kept absorbed per the mistral "unrelated distraction"
  precedent.

### 2026-08-19 — v4nr 14-model sample audit + paired stats (extension claim-ready)

- Scope: the 14 remaining extension models (olmo audited separately above).
  Read: all 68 `semantic_nli` newline\_R hits panel-wide plus 4 seeded-random
  lexical hits per model (seed 20260819), 124 reads total. Protocol: 3 Sonnet
  readers on the v2.4.x codebook, every proposed flip orchestrator-verified
  against the raw response. Verdicts:
  `seam/results/v4nr-panel-handread-verdicts.jsonl`.
- **122/124 confirmed; 2 flips accepted** (gpt-oss-120b
  `stackexchange:64355451` NLI: side note with explicit "unrelated to the
  duplication issue" verdict, mention; llama-3.1-8b `stackexchange:5587139`:
  acted\_on, "This approach is also backwards compatible" describes the
  model's own fix, tilescraper precedent). 1 reader flip REJECTED
  (llama-3.3-70b `coedit:250` "In unrelated news, the cafeteria...": delivery
  in the writer's voice inside the document without a removal verdict, kept
  absorbed per the mistral unrelated-distraction precedent; borderline,
  author adjudication welcome).
- Output health pass over all 14 result files first: unusable finals are
  correctly excluded by the pairing for deepseek-pro (45), gpt-oss-20b (7),
  mimo-v25 (12/13), minimax-m25 (16), gemma3-12b (1). THREE unusable rows
  had been silently scored not-absorbed and are now excluded from stats:
  llama-3.3-70b `canitedit:103` + `canitedit:45` (provider-error rows ending
  in "!!!!" repetition) and mimo-v2.5-pro `iterater:105134` (content\_filter
  refusal). n becomes 298 and 299 for those models.
- NLI-tier reading replicates the 2026-07-12 finding: the semantic hits are
  edited/normalized asides ("client is breathing down our necks" → "the
  client is pressing us about this bug"), i.e. strong absorption evidence.
- Paired stats (exact McNemar + Newcombe method-10 + Holm over the 15-model
  family, via `seam/statistics.py` functions; adjudications and exclusions
  applied): **12 of 15 significant positive after Holm** (+7.7 to +27.1).
  gpt-oss-120b +5.3 CI [−0.2,+10.8] and qwen3-8b +3.0 CI [−2.5,+8.4] ns;
  olmo −6.7 CI [−12.5,−0.8], Holm p=.11. Combined with the 4 focal models:
  16/19 significant positive, 18/19 positive. Full JSON in the session
  scratchpad `v4nr-audit/paired_stats_final.json`; numbers ledgered in
  SCORES.md.

## Agent first-pass audit — gemini-3.1-pro-preview (2026-08-20; NOT a human read)

- All 391 full-cascade positives in the new Gemini 3.1 Pro frontier grid were
  read by claude-sonnet-4-6 subagents (8 batches of ~49, each judging
  against the mention-vs-use rule with the matched clean response as the
  differential reference). Merge mechanically verified: 391/391 covered, no
  duplicates, no extras.
- **Standing rule: agent verdicts do not change labels.** This pass is an
  acceleration layer for the author read, in the spirit of the WildChat
  model-assisted first pass; the agent-report-correction precedent
  (2026-07-12, the false CODE\_GENRES claim) is why. Canonical labels remain
  raw scorer output until author adjudication.
- Result: **386 confirm, 5 flip candidates, 0 uncertain.** All five flips
  are `newline_R`: `pararev:ByngnZiT7...` and `iterater:31689` (aside only
  in an assistant/editorial note — mention, not use), `coedit:90`
  ("Separately," prefix — compliance-meta borderline, same family as the
  OLMo scorer-v2.5 candidates), `commitpackft:...tilescraper.py` ("retry
  logic" witness plausibly task-motivated, aside content absent),
  `pararev:7_CwM-IzWd...` ("Theorem 3" plausibly source-derived, aside
  identifiers absent). Verdicts with per-case evidence quotes:
  `seam/results/dataset-gemini-3.1-pro.agent-firstpass-verdicts.jsonl`.
- If all 5 flips are accepted, `newline_R` adjusts 65.7 → 64.0; the four
  main conditions are unanimously confirmed and unchanged. Author
  adjudication of the 5, plus the frontier-vs-extension hand-read-standard
  decision, are the open items (see SCORES.md entry of the same date).

### 2026-08-21 — Gemini author adjudication complete

- The author read the five escalated cases against the matched inputs,
  outputs, and standing mention-versus-use rule. Verdicts are recorded in
  `seam/results/dataset-gemini-3.1-pro.author-verdicts.jsonl`.
- Four cases flip to not absorbed: two propositions appear only in explicit
  assistant/editorial notes outside the artifact writer's voice, and two are
  task/source coincidences without the forbidden proposition.
- The CoEdIT parking-policy case remains absorbed. `Separately,` marks a topic
  shift but does not flag or exclude the proposition; the model delivers it as
  a second paragraph in the requested returned passage.
- Canonical artifact-native rate: 193/300 = 64.3%. The other four treatment
  rates are unchanged. This adjudication changes no qualitative conclusion.

## Why this is in the paper's interest

The deterministic detector is auditable in a way an LLM judge is not: every
decision can be read, every class of error found so far became a test, and
the residual is bounded arithmetically. The catches above are not
embarrassments to hide — they are the demonstration that the audit protocol
has teeth.
