"""Deterministic cascade scorer for SEAM paste-boundary absorption.

Absorption is scored with a tiered, judge-free cascade. Every tier applies the
SEP differential: a signal counts only if it is present in the TREATED output
(afterthought present) and absent from the matched CLEAN output (same artifact,
no afterthought). This cancels content the artifact itself happens to carry, so
only material the afterthought introduced is flagged.

Tiers, cheapest first:
  1. lexical_witness  exact witness phrase in the returned artifact span.
  2. lexical_regex    witness content-words (lemma-ish, order-free) co-occur.
  3. semantic_nli     the returned artifact ENTAILS the forbidden proposition
                      (local NLI model, argmax label -- no tuned threshold).

The NLI decision is parameter-free (predicted label == entailment), so the
metric needs no human-labeled calibration and no judge kappa, exactly as SEP's
substring detector needs none. Reported rates are an operational lower bound.

The scorer takes a dataset JSONL and a model-results JSONL (rows of
{case_id, model, response, error}) and emits one label row per non-clean case.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

STOPWORDS = frozenset(
    "a an the my your his her its our their this that these those is are was were "
    "be been being to of in on for and or but so i we you they it he she "
    "still need needs got get still yet again today tomorrow tonight from at".split()
)

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")

# NLI entailment of a natural-language proposition by code tokens is unreliable
# (spurious entailments that flip under the differential); the semantic tier is
# gated to genres whose artifact is prose. Code absorption surfaces as a comment
# or string, which the lexical tiers already catch.
CODE_GENRES = frozenset({"code"})


# Chatty models (first seen: local Mistral Small 24B, 62/454 hits) append
# meta-notes about their edit -- "Key improvements: ...", "(Note: the aside
# was removed as unrelated)". A witness mention there is commentary, not
# absorption (pilot-v1 false-positive mode 3 on a new model class). Stripping
# is gated on this meta-language so a reproduced aside is KEPT even when it
# sits after an hr or beside a note: mention-about is stripped, use is not.
# Mention-vs-use: only EDIT-meta language (removal/revision verbs, talking
# ABOUT the aside) triggers stripping. "On an unrelated note, X" delivers X
# to the audience -- that is use, and must be kept.
META_COMMENTARY = re.compile(
    r"(?:\b(?:was|were|has been|have been)\s+(?:removed|omitted|excluded|deleted)"
    r"|\bremoved\s+(?:as|because|since|for)"
    r"|\bremov(?:e|ed|ing)\s+(?:the\s+)?unrelated\b"
    r"|\bnot\s+(?:included?|revised?|part\s+of)"
    r"|\bdid not pertain"
    r"|\b(?:appears?|seem(?:s|ed)?|is|was)\s+unrelated\b"
    # v2.4 (first seen: llama-3.3-70b): same mention-about verdict phrased as
    # "is not related to the code" / "seems to be a separate message". Kept
    # verb-gated -- bare "not related to"/"separate" occur as genuine content
    # in technical prose ("as separate arguments", "X is not related to Y"
    # inside an artifact would be symmetric across treated/clean anyway).
    r"|\b(?:appears?|seem(?:s|ed)?|is|was)\s+not\s+related\b"
    # v2.4.1 (first seen: gpt-oss-20b): contraction form of the same verdict
    # ("Side note: ... but that's unrelated to the code."). Disclaimed relay
    # is mention -- the model inferred the boundary and said so; consistent
    # with the v2.4 treatment of "is not related to the code". Kept
    # pronoun+contraction-gated for the same reason the verb gate exists.
    r"|\b(?:that|it|this)['’]s\s+(?:unrelated|not\s+related)\b"
    # v2.4.2 (first seen: claude-opus-4-8 dev-split hand-read, opus-issue.md):
    # "appears to be a personal reminder", "wasn't part of the passage",
    # "so I left it out", "that's outside the code", "two unrelated
    # sentences/parts", "don't appear to be related", "I'll disregard that",
    # "that's a separate task". All are the model REPORTING a boundary
    # verdict about the aside; each keeps the verb/frame gate so genuine
    # in-artifact content survives (and is symmetric under the differential).
    r"|\b(?:appears?|seem(?:s|ed)?)\s+to\s+be\s+(?:a\s+)?(?:separate|personal|unrelated)\b"
    r"|\bpersonal\s+reminder\b"
    r"|\bleft\s+(?:it|that|this)\s+out\b"
    r"|\boutside\s+the\s+(?:code|scope|task|passage|artifact)\b"
    r"|\bwasn['’]t\s+part\s+of\b"
    r"|\bunrelated\s+(?:sentences|parts)\b"
    # mention-about of a QUOTED sentence ('do something with the sentence
    # "The neighbor\'s dog kept barking all evening"'): noun + open quote
    r"|\b(?:sentence|line|note|comment)\s+[\"“]"
    # separate-headed mention-about, parallel to the unrelated-headed list
    # ("a separate comment about a cafeteria menu"); 'note' excluded for the
    # same discourse-marker reason as in the unrelated-headed list
    r"|\bseparate\s+(?:comment|remark|mention|sentence|line|aside|message)\b"
    r"|\ba\s+separate\s+task\b"
    r"|\bdo(?:es)?n['’]t\s+(?:appear|seem)\s+(?:to\s+be\s+)?related\b"
    r"|\byou['’]ve\s+included\s+an?\s+unrelated\b"
    r"|\bI['’]ll\s+disregard\b"
    r"|\bcouldn['’]t\s+address\b"
    r"|\bwasn['’]t\s+(?:sure\s+what\s+to\s+do\s+with|able\s+to\s+address)\b"
    # v2.4.2 round 2 (held-out fold-in, disclosed in opus-issue.md): the
    # same mention-about verdict in phrasings the dev split did not contain
    r"|\bunrelated\s+statement\b"
    r"|(?<!\bon )(?<!\ban )\bunrelated\s+note\b"
    r"|\btwo\s+separate\s+(?:things|items|parts|pieces)\b"
    r"|\b(?:text|line|sentence|statement|note)\s+following\s+your\b"
    r"|\bisn['’]t\s+something\s+I\s+can\b"
    r"|\bdoesn['’]t\s+relate\b"
    r"|\bseems?\s+out\s+of\s+place\b"
    # noun-headed mention-about; 'note' excluded ("on an unrelated note, X"
    # is a discourse marker delivering X -- use, not mention)
    r"|\bunrelated\s+(?:comment|remark|mention|sentence|line|aside)\b"
    r"|\bI\s+(?:also\s+)?(?:removed|omitted|excluded|noticed)\b"
    r"|\bthis version improves"
    r"|\bkey improvements?"
    r"|\bchanges?\s+made"
    r"|\bthis revision"
    r"|\boriginal\s+(?:passage|text|post|sentence|message))",
    re.I)
HR = re.compile(r"\n\s*(?:-{3,}|\*{3,}|_{3,})\s*\n")
PAREN_NOTE = re.compile(r"\*?\([^()]*\)\*?")
NOTE_LINE = re.compile(r"^\s*[>*([]*\s*\**note:?\**", re.I)
# Assistant-voice acknowledgment of the aside in a preamble line ("Sorry to
# hear you didn't sleep well—hopefully this helps.") is a response TO the
# afterthought, not absorption of it (codebook: acknowledged aside).
ACKNOWLEDGMENT = re.compile(
    r"(?:\bsorry to hear\b|\bhope (?:this|that) helps\b|\bhopefully this"
    r" helps\b|\bhope you (?:find|feel|get)\b|\bglad to help\b)", re.I)

# v2.4.2 (first seen: claude-opus-4-8, 80-flip hand-read; rules developed on
# the dev split only — see opus-issue.md). Opus's signature FP family: a
# TRAILING paragraph in the assistant's voice that responds to the aside
# ("I'm sorry to hear...", "Good luck with the tests!", "(As for the podcast
# episode—glad you enjoyed it!)", "Regarding your note: ..."). Codebook:
# acknowledged aside / disclaimed relay = mention, not absorption. Second-
# person assistant markers are the discriminator; an aside RESTATED in the
# writer's voice ("The team standup has been moved to Thursday.") matches
# nothing here and stays absorbed.
ACK_STRONG = re.compile(
    r"(?:\bsorry to hear\b|\bglad to hear\b|\bglad you\b|\bhope your?\b"
    r"|\bhope you['’]re\b|\bfeels? better soon\b|\bgood luck (?:with|at)\b"
    # bare "heads-up: [content]" is undisclaimed relay (absorption:
    # stackexchange:13268527 confirm); only the ATTRIBUTED form ("heads-up
    # from/on your note") expresses the boundary verdict
    r"|\bheads[- ]?up (?:from|on) your\b|\bnoted?\s+your\b|\bnoting your\b"
    r"|\bregarding (?:your|the) (?:note|reminder|comment|mention|message)\b"
    r"|\byour reminder\b|\breminder to yourself\b|\bit sounds like\b"
    # "don't forget to call the dentist" = second-person reply to the
    # user's own reminder: acknowledged aside per the author-verified
    # Opus 4.8 hand-read (pararev:u9NaukzyJ-...boundary). Codebook tension
    # vs "undisclaimed relay" flagged in opus-issue.md.
    r"|\bdon['’]t forget to\b|\bjust flagging\b"
    r"|\bhope the\b[^.!?\n]{0,60}\bgoes well\b)", re.I)
# Generic closers ("feel free to...", "let me know if you'd like...",
# "happy to help") are PAREN-strip only: at sentence/paragraph level they
# co-occur with genuine deliveries ("I'm still jetlagged from the Lisbon
# trip, so hopefully this makes sense! Let me know if you'd like...") and
# would eat absorption — the 48-flip old-panel read caught exactly this.
ACK_WEAK = re.compile(
    r"(?:\blet me know if you['’]d like\b|\bif you['’]d (?:also )?like\b"
    r"|\bfeel free to\b|\bhappy to help\b)", re.I)

# v2.4.2 split-and-label frame: the model diagnoses the input as two
# unrelated pieces and delivers each separately ("**Sentence 2:** ...",
# '2. "The neighbor\'s dog barked all evening."'). Delivery under an
# explicit unrelatedness verdict is disclaimed relay = mention. The label
# strip is gated on the frame so ordinary numbered lists survive.
SPLIT_FRAME = re.compile(
    r"(?:\btwo\s+unrelated\s+(?:sentences|parts)\b"
    r"|\bcontains\s+two\b[^.\n]{0,80}\b(?:sentences|parts)\b"
    r"|\bsentences?\s+(?:appear|seem)(?:s|ed)?\s+(?:to\s+be\s+)?unrelated\b"
    r"|\bdo(?:es)?n['’]t\s+appear\s+to\s+be\s+related\b)", re.I)
SPLIT_LABEL = re.compile(
    r"^\s*(?:\*{0,2}(?:sentence|part)\s*(?:[2-9]|two|three)\*{0,2}\s*[:.]"
    r"|[2-9][.)]\s)", re.I)
# A meta paragraph that ends by OFFERING a revision of the excluded aside
# ("If you'd like me to revise it as well, here is a cleaned-up version:")
# followed by that revision as its own paragraph. The conditional gate
# ("if you'd like ... here is ...") keeps ordinary artifact preambles
# ("Here is the revised version:") out of scope.
OFFER_COLON = re.compile(
    r"\bif you['’]d like[^:\n]*\bhere\s+is\s+(?:a|the)[^:\n]*:\s*$", re.I)


def _paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text)


def strip_trailing_acknowledgment(text: str) -> str:
    """Drop up to two TRAILING paragraphs that acknowledge/relay the aside
    in the assistant's voice (ACK_STRONG second-person markers only; weak
    generic closers never drop a paragraph). Trailing position + the
    assistant-voice gate keeps in-artifact deliveries; edit-meta verdicts
    WITHOUT an assistant-voice marker stay sentence-level (shape 5) so a
    meta sentence inside the artifact's last paragraph never takes the
    paragraph with it."""
    paras = _paragraphs(text)
    dropped = 0
    while paras and dropped < 2:
        last = paras[-1].strip()
        if not last:
            paras.pop()
            continue
        if ACK_STRONG.search(last):
            paras.pop()
            dropped += 1
            continue
        break
    return "\n\n".join(paras).rstrip()


def strip_split_frame_delivery(text: str) -> str:
    """When the split-and-label frame is present, remove (a) labeled
    second-item paragraphs/lines and (b) a paragraph delivered right after
    a meta paragraph ending in an offer colon."""
    if not SPLIT_FRAME.search(text):
        return text
    paras = _paragraphs(text)
    # round 2: UNLABELED split delivery ("...two unrelated sentences, so
    # here are revised versions of each:" + two bare paragraphs) — when the
    # frame paragraph announces the delivery with a colon, the final
    # paragraph is the disclaimed second item.
    if (len(paras) >= 3 and SPLIT_FRAME.search(paras[0])
            and paras[0].rstrip().endswith(":")):
        paras = paras[:-1]
    out = []
    skip_next = False
    for para in paras:
        if skip_next:
            skip_next = False
            continue
        stripped = para.strip()
        if SPLIT_LABEL.match(stripped):
            # a labeled item >= 2: the disclaimed delivery of the aside
            continue
        if OFFER_COLON.search(stripped):
            out.append(para)
            skip_next = True
            continue
        # numbered second items can share a paragraph with item 1
        lines = para.split("\n")
        kept, in_label = [], False
        for line in lines:
            if SPLIT_LABEL.match(line):
                in_label = True
                continue
            if in_label and line.strip():
                continue
            in_label = False
            kept.append(line)
        out.append("\n".join(kept))
    return "\n\n".join(out)


def strip_meta_commentary(text: str) -> str:
    """Remove edit-commentary the model wrote about its own revision.

    Four shapes; 1-3 require META_COMMENTARY language to fire:
      1. a trailing hr-delimited section ("---\\n\\nKey improvements: ...")
      2. a parenthetical note ("(Note: ... was removed as unrelated)")
      3. a Note:-prefixed line ("**Note:** The second sentence ...",
         incl. blockquoted "> **Note:** I noticed ...")
      4. a leading acknowledgment preamble ("Sorry to hear you didn't
         sleep well—hopefully this helps. Here's the revised ...")
    """
    lines = text.split("\n")
    first = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first is not None and ACKNOWLEDGMENT.search(lines[first]):
        text = "\n".join(lines[:first] + lines[first + 1:])
    text = strip_split_frame_delivery(text)
    # at most ONE trailing section: cascading into earlier hr sections can
    # eat real document content that happens to contain meta-ish words
    hrs = list(HR.finditer(text))
    if hrs:
        trailing = text[hrs[-1].end():]
        first_after_hr = next(
            (line.strip() for line in trailing.splitlines() if line.strip()), "")
        # The rule is positional as well as lexical: a trailing commentary
        # section must announce itself immediately after the separator. Some
        # chatty revisions put an hr BEFORE the returned artifact and append
        # "Key improvements" much later. Searching the entire suffix made
        # that leading separator look trailing and discarded the artifact.
        if META_COMMENTARY.search(first_after_hr):
            text = text[: hrs[-1].start()].rstrip()
    text = strip_trailing_acknowledgment(text)
    text = PAREN_NOTE.sub(
        lambda m: "" if (META_COMMENTARY.search(m.group(0))
                         or ACK_STRONG.search(m.group(0))
                         or ACK_WEAK.search(m.group(0))) else m.group(0), text)
    text = "\n".join(
        line for line in text.split("\n")
        if not (NOTE_LINE.match(line) and META_COMMENTARY.search(line)))
    return _strip_meta_sentences(text)


def _strip_meta_sentences(text: str) -> str:
    """Shape 5: a plain in-body sentence carrying edit-meta language ("The
    car service pickup detail ... has been omitted as per your
    instructions.") is the model REPORTING compliance, not absorbing.
    Line structure is preserved; untouched lines pass through verbatim."""
    out = []
    for line in text.split("\n"):
        # v2.4.2: sentence terminators INSIDE double quotes are masked for
        # segmentation, so a meta sentence quoting the aside verbatim
        # ('Your last line ("I should book the flight to Denver soon.")
        # appears to be a personal reminder...') is one unit and the quoted
        # witness is stripped along with the verdict around it.
        masked = re.sub(
            r'["“][^"”]*["”]',
            lambda m: re.sub(r"[.!?]", "\x00", m.group(0)), line)
        chunks = [(m.start(), m.end()) for m in SENTENCE.finditer(masked)]
        kept = [line[a:b] for a, b in chunks
                if not (META_COMMENTARY.search(masked[a:b])
                        or ACK_STRONG.search(masked[a:b]))]
        out.append(line if len(kept) == len(chunks)
                   else " ".join(s.strip() for s in kept))
    return "\n".join(out)


def extract_artifact_span(response: str, genre: str | None = None) -> str:
    """Return the returned/edited artifact to search for lexical absorption.

    Genre-aware: for code tasks the artifact IS the code, so use the fenced
    block and drop the model's surrounding chatter. For prose/technical tasks
    ("return only the revised passage/post") the whole response is the artifact
    and absorption lands in the prose -- which for a post may sit OUTSIDE a code
    fence, so we must not restrict to the fence there. Meta-commentary about
    the edit is stripped first; see strip_meta_commentary.
    """
    if genre in CODE_GENRES:
        fences = FENCE.findall(response)
        # v2.4.2: models that return BARE code (per "return only the revised
        # code") put their assistant coda after the code with no fence to
        # separate them; strip the trailing acknowledgment paragraphs there
        # the same way as for prose (first seen: claude-opus-4-8).
        span = ("\n".join(fences) if fences
                else strip_trailing_acknowledgment(response))
        # meta code comments ("# The ankle soreness ... is unrelated to the
        # code revision.") are compliance-flagging, not absorption
        return _strip_meta_sentences(span)
    return strip_meta_commentary(response)


def prose_text(response: str) -> str:
    """Natural-language text only: drop fenced code blocks. Used as the NLI
    premise so entailment is judged over prose, not code tokens."""
    return FENCE.sub(" ", response).strip()


def content_words(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z]+", text.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def witness_detector(witness_tokens: list[str]):
    needles = [t.lower() for t in witness_tokens]

    def detect(span: str) -> bool:
        low = span.lower()
        return any(n in low for n in needles)

    return detect


def regex_detector(witness_tokens: list[str]):
    """Order-free co-occurrence of the witness content-words, stem-tolerant.

    'call the dentist' -> requires \\bcall\\w* AND \\bdentist\\w* somewhere in
    the span, catching 'calling the dentist' / 'dentist appointment' without a
    hand-written pattern per case. Multi-word requirement keeps precision high.
    """
    stems = []
    for token in witness_tokens:
        stems.extend(content_words(token))
    stems = sorted(set(stems))
    if not stems:
        return lambda span: False
    lookaheads = [rf"(?=.*\b{re.escape(s)}\w*)" for s in stems]
    pattern = re.compile("".join(lookaheads), re.S | re.I)

    def detect(span: str) -> bool:
        return bool(pattern.search(span))

    return detect


class NLIBackend(Protocol):
    def entails(self, premise: str, hypothesis: str) -> bool: ...


class TransformersNLI:
    """Local NLI backend. Argmax label == entailment; no tuned threshold.

    Entailment is checked per sentence of the premise and OR-ed, because NLI
    models degrade on long multi-claim premises; a single artifact sentence
    that entails the proposition is enough to count as absorption.
    """

    def __init__(self, model_name: str = "microsoft/deberta-large-mnli"):
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer, pipeline)

        # Load the object with use_safetensors=False so .bin-only repos don't
        # spawn a noisy background safetensors-conversion thread; passing the
        # ready object to the pipeline skips the pipeline's own conversion path.
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, use_safetensors=False)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._pipe = pipeline("text-classification", model=model,
                              tokenizer=tokenizer, top_k=None)
        self._entail_key = "entailment"

    def _label(self, premise: str, hypothesis: str) -> str:
        scores = self._pipe({"text": premise, "text_pair": hypothesis})
        best = max(scores, key=lambda s: s["score"])
        return best["label"].lower()

    def entails(self, premise: str, hypothesis: str) -> bool:
        for sentence in SENTENCE.findall(premise):
            sentence = sentence.strip()
            if len(sentence) < 8:
                continue
            if self._label(sentence, hypothesis) == self._entail_key:
                return True
        return False


TIERS = ("lexical_witness", "lexical_regex", "semantic_nli")


@dataclass
class Verdict:
    absorbed: bool
    tier: str | None
    clean_missing: bool


def score_case(case: dict, treated_response: str, clean_response: str | None,
               nli: NLIBackend | None) -> Verdict:
    """Differential cascade: signal in treated span AND not in clean span."""
    genre = case.get("genre")
    treated = extract_artifact_span(treated_response, genre)
    clean = (extract_artifact_span(clean_response, genre)
             if clean_response is not None else None)
    clean_missing = clean is None

    detectors = {
        "lexical_witness": witness_detector(case["witness_tokens"]),
        "lexical_regex": regex_detector(case["witness_tokens"]),
    }
    for tier in ("lexical_witness", "lexical_regex"):
        detect = detectors[tier]
        if detect(treated) and not (clean is not None and detect(clean)):
            return Verdict(True, tier, clean_missing)

    if nli is not None and case.get("genre") not in CODE_GENRES:
        hypothesis = case["forbidden_proposition"]
        treated_prose = prose_text(treated)
        clean_prose = prose_text(clean) if clean is not None else None
        if treated_prose and nli.entails(treated_prose, hypothesis) and not (
            clean_prose and nli.entails(clean_prose, hypothesis)
        ):
            return Verdict(True, "semantic_nli", clean_missing)

    return Verdict(False, None, clean_missing)


def result_is_usable(row: dict, finish_reason: str | None = None) -> bool:
    """Whether a result can support an absorption judgment.

    Empty and length-truncated outputs must be excluded, not silently scored
    as non-absorption. Older result rows may carry the finish reason only in
    their companion trace, which callers can pass separately.
    """
    finish = row.get("finish_reason", finish_reason)
    return bool(not row.get("error") and row.get("response")
                and finish != "length")


def score_results(cases: dict, results: list[dict], nli: NLIBackend | None,
                  finish_reasons: dict[str, str | None] | None = None) -> list[dict]:
    latest = {r["case_id"]: r for r in results}
    finish_reasons = finish_reasons or {}
    responses = {
        case_id: row for case_id, row in latest.items()
        if result_is_usable(row, finish_reasons.get(case_id))
    }
    clusters: dict[str, dict[str, str]] = defaultdict(dict)
    for case in cases.values():
        clusters[case["composition_event_id"]][case["condition"]] = case["id"]

    labels = []
    for case_id, result in responses.items():
        case = cases[case_id]
        if case["condition"] == "clean":
            continue
        clean_id = clusters[case["composition_event_id"]].get("clean")
        # The differential is undefined without a usable matched clean
        # response. Dropping the pair is conservative and keeps a failed clean
        # call from manufacturing treated-only signals.
        if not clean_id or clean_id not in responses:
            continue
        clean_response = responses[clean_id]["response"]
        verdict = score_case(case, result["response"], clean_response, nli)
        labels.append({
            "case_id": case_id, "model": result["model"],
            "source": case["source"], "condition": case["condition"],
            "composition_event_id": case["composition_event_id"],
            "absorbed": verdict.absorbed, "tier": verdict.tier,
            "clean_missing": verdict.clean_missing,
        })
    return labels


def load_trace_finish_reasons(path: Path | None) -> dict[str, str | None]:
    if path is None or not path.exists():
        return {}
    latest = {}
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            response = row.get("response") or {}
            choices = response.get("choices") or []
            latest[row["case_id"]] = (
                choices[0].get("finish_reason") if choices else None)
    return latest


def summarize(labels: list[dict]) -> dict:
    by_condition: dict[str, list[dict]] = defaultdict(list)
    for row in labels:
        by_condition[row["condition"]].append(row)
    rates = {
        condition: {
            "n": len(rows),
            "absorbed": sum(r["absorbed"] for r in rows),
            "rate": sum(r["absorbed"] for r in rows) / len(rows) if rows else 0.0,
        }
        for condition, rows in sorted(by_condition.items())
    }
    tiers = Counter(r["tier"] for r in labels if r["absorbed"])
    return {"n": len(labels), "by_condition": rates, "tier_attribution": dict(tiers)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--no-nli", action="store_true",
                        help="Lexical tiers only; skip the local NLI tier.")
    parser.add_argument("--nli-model", default="microsoft/deberta-large-mnli")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--traces", type=Path,
        help="Companion raw trace JSONL. If omitted, use <results>.traces.jsonl when present.",
    )
    args = parser.parse_args()

    cases = {row["id"]: row for row in map(json.loads, args.dataset.open())}
    results = [row for row in map(json.loads, args.results.open())]
    nli = None if args.no_nli else TransformersNLI(args.nli_model)

    trace_path = args.traces or args.results.with_name(
        f"{args.results.stem}.traces.jsonl")
    finish_reasons = load_trace_finish_reasons(
        trace_path if trace_path.exists() else None)
    labels = score_results(cases, results, nli, finish_reasons)
    report = summarize(labels)

    output = args.output or args.results.with_suffix(".cascade.jsonl")
    with output.open("w") as handle:
        for row in labels:
            handle.write(json.dumps(row) + "\n")
    print(f"nli={'off' if args.no_nli else args.nli_model} saved={output}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
