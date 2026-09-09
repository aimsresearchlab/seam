# Adjudication codebook — WildChat paste-then-continue sample

Current paper use, 2026-08-14: the reported ecological occurrence check uses a binary `genuine` versus `not_genuine` decision on 50 seeded candidates. The five-class scheme below documents the earlier first pass and remains useful for error analysis, but its model-assisted prevalence calculation is not a paper result. See `research/WILDCHAT_AUDIT_PAPER_GUIDANCE.md`.

Applies to `seam/results/wildchat-audit.adjudication.jsonl` (n=200, seed 42,
drawn from unique `paste_with_tail` flags). Each record gets exactly one
`label`. The published prevalence counts only `genuine` as a true positive;
`ambiguous` is reported under both strict (negative) and lenient (positive)
adjudication.

## The question being adjudicated

Did a real user paste (or otherwise embed) an artifact into the message and
then continue typing their own words after it, with no explicit boundary
markup between artifact and continuation?

An *artifact* is content the user did not compose in this message for this
conversation: code, an essay/story/paper, an email, a job posting, search
results, lyrics, a form definition, homework text, another AI's output.
*Continuation* is user-voice text after the artifact: a task instruction, a
question, a correction, or an aside.

## Labels

### `genuine`
The body is an artifact and the tail is user-voice continuation.
Signals: register shift (artifact formal/structured → tail casual/imperative);
tail refers to the artifact ("this code", "the above", "it"); tail is a task
("explain…", "fix…", "how can I…"); typos/informality in the tail absent
from the body.
Include: artifact preceded by a typed head AND followed by a typed tail;
tail in a different language than the artifact; tail that is an aside rather
than an instruction.

### `remnant_tail`
The flagged tail is actually the artifact's own ending — the segmenter cut
too early. Signals: tail continues the body's register/narrative seamlessly;
tail is the last list items of a pasted list; removing the tail truncates
the artifact mid-thought.
Decision rule: read body-end and tail together; if they form one continuous
text in one voice, it is `remnant_tail`.

### `typed_not_pasted`
No artifact: the whole message is user-composed for this conversation —
long creative specs, multi-paragraph task descriptions, worldbuilding
briefs. Signals: uniform voice throughout; body addresses the assistant
("I want you to…"); no content that plausibly existed before the chat.
Boundary rule: text the user obviously wrote *earlier elsewhere* and pasted
in (their own essay to edit) is an artifact → `genuine` if tailed.

### `roleplay_template`
Persona/jailbreak/system-prompt scaffolds and agent frameworks (DAN-style,
"You are X", AutoGPT remnants that slipped the spam filter). These are
pastes in a mechanical sense but not the benign composition pattern under
study; counted separately.

### `ambiguous`
Cannot decide between the above after reading the full message. Use
sparingly; note the competing labels in `rationale`.

## Procedure

1. Read `msg` in full (truncated at 2,000 chars — judge from what is there).
2. Assign one label + a one-sentence `rationale`.
3. Do not consider what the model replied, message quality, or topic.
4. First pass may be LLM-assisted; the published estimate requires human
   verification of the first-pass labels (spot-check all `genuine`/`ambiguous`
   plus a random slice of the rest, or full re-read).

## Historical five-class reporting

The original analysis computed strict and lenient candidate precision from the five-class labels. Do not multiply those values by the screen rate for the current paper. The current claim reports the binary human count only as evidence of occurrence and does not extrapolate it to WildChat prevalence.
