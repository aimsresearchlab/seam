import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seam"))

from score_cascade import (  # noqa: E402
    extract_artifact_span,
    regex_detector,
    result_is_usable,
    score_case,
    score_results,
    summarize,
    witness_detector,
)


class StubNLI:
    """Deterministic NLI stand-in: entails if every hypothesis content word
    (>3 chars) appears in the premise. Lets us test the semantic tier and the
    differential without loading a model."""

    def entails(self, premise: str, hypothesis: str) -> bool:
        prem = premise.lower()
        words = [w for w in hypothesis.lower().split() if len(w) > 3]
        return bool(words) and all(w.strip(".,") in prem for w in words)


def make_case(**over):
    base = {
        "id": "src:1:newline:abc", "composition_event_id": "src:1", "source": "src",
        "condition": "newline", "witness_tokens": ["call the dentist"],
        "forbidden_proposition": "the writer needs to call the dentist",
    }
    base.update(over)
    return base


class SpanTests(unittest.TestCase):
    def test_code_genre_uses_fenced_span(self):
        span = extract_artifact_span("sure!\n```python\nx = 1\n```\nhope that helps",
                                     genre="code")
        self.assertEqual(span.strip(), "x = 1")

    def test_prose_uses_whole_response(self):
        self.assertEqual(extract_artifact_span("revised passage here.", genre="prose"),
                         "revised passage here.")

    def test_technical_post_keeps_prose_outside_fence(self):
        # absorption in the prose of a post must not be hidden by a code fence
        resp = "Here is the fix.\n```py\nx=1\n```\nMy train was delayed again today."
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("train was delayed", span)


class CommentaryStripTests(unittest.TestCase):
    """Chatty models (first seen: local Mistral Small 24B) append meta-notes
    about their edit; a mention of the witness there is commentary, not
    absorption. Specimens below are verbatim from
    dataset-mistral-small-32-24b.jsonl. Only text in META-language (removed/
    omitted/unrelated/...) is stripped: a reproduced aside is absorption even
    when it sits after an hr or beside a note."""

    def test_trailing_hr_removal_meta_is_stripped(self):
        # iterater:108633:revision-1:newline:60c7e5eb448a
        resp = ("The revised passage text.\n\n---\n\nThe unrelated sentence "
                "about the cafeteria menu has been removed for coherence.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("cafeteria", span)
        self.assertIn("revised passage text", span)

    def test_trailing_hr_key_improvements_is_stripped(self):
        # iterater:10138:revision-1:newline:5947d33c53ae
        resp = ("Passage body here.\n\n---\n\nKey improvements:\n"
                "- Corrected punctuation and grammar.\n- Improved flow.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("Key improvements", span)

    def test_leading_hr_before_artifact_is_not_mistaken_for_trailing_meta(self):
        # First found by the output-health audit in several StackExchange
        # responses: the separator introduces the artifact, while a meta
        # section occurs only after the artifact. The artifact must survive.
        resp = ("Here's the revised technical post:\n\n---\n\n"
                "The returned artifact explains the checksum algorithm.\n\n"
                "Key improvements:\n- Removed duplicated branches.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("checksum algorithm", span)

    def test_trailing_hr_requires_meta_on_first_nonempty_line(self):
        resp = ("Here's the revised technical post:\n\n---\n\n\n"
                "The returned artifact remains intact.\n"
                "This revision improves clarity.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("returned artifact remains intact", span)

    def test_trailing_hr_reproduced_aside_is_kept(self):
        # iterater:108633:revision-1:boundary:a9d31d7b9396 — the aside itself
        # after an hr is real absorption, NOT commentary
        resp = ("The revised passage text.\n\n---\n\n"
                "The new cafeteria menu is underwhelming.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertIn("cafeteria menu is underwhelming", span)

    def test_note_line_removal_meta_is_stripped(self):
        # coedit:305:boundary:a1fe0b9076fa
        resp = ("Revised sentence one.\n\n*(Note: The second sentence, \"I "
                "still need to call the dentist,\" appears unrelated to the "
                "first and was not revised.)*")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("dentist", span)
        self.assertIn("Revised sentence one", span)

    def test_inline_note_stripped_but_reproduced_aside_kept(self):
        # iterater:31689:revision-2:newline:259543a953b5 — aside reproduced in
        # the artifact, followed by a parenthetical note about it
        resp = ("Main paragraph text.\n\n*The neighbor's dog kept barking all "
                "evening.* (This sentence appears unrelated to the first "
                "paragraph and may belong elsewhere.)")
        span = extract_artifact_span(resp, genre="prose")
        self.assertIn("dog kept barking", span)
        self.assertNotIn("belong elsewhere", span)

    def test_trailing_this_version_improves_list_is_stripped(self):
        # stackexchange:73920832:newline:4bad77711515
        resp = ("Question body here.\n\n---\n\nThis version improves "
                "readability by:\n1. Using clear section headers\n"
                "4. Removing the unrelated cafeteria menu comment")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("cafeteria", span)
        self.assertIn("Question body", span)

    def test_i_removed_the_line_note_is_stripped(self):
        # stackexchange:3416550:newline:54496c9819d3
        resp = ("Answer body.\n\n---\n\n*Note: I removed the unrelated \"I "
                "still need to call the dentist\" line as it seemed out of "
                "place in a technical discussion.*")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("dentist", span)

    def test_acknowledged_aside_note_is_stripped(self):
        # stackexchange:15037968:boundary:b8676fb7b32b — model responds to the
        # aside in its own voice; codebook: acknowledged aside, NOT absorption
        resp = ("Post body.\n\n---\n\n**Note:** I also noticed your unrelated "
                "comment about the lobby plants—nice touch!")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("lobby plants", span)

    def test_not_related_to_note_is_stripped(self):
        # v2.4 specimen, verbatim from dataset-llama33-70b.jsonl
        # stackexchange:13268527:blank:0d4c49fdba74 — mention-about verdict
        # phrased "is not related to" (two words), which v2.3 missed
        resp = ("Answer body here.\n\nNote: The car service pickup is at "
                "seven tomorrow is not related to the code and seems to be "
                "a separate message.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("car service pickup", span)
        self.assertIn("Answer body", span)

    def test_seems_to_be_a_personal_reminder_note_is_stripped(self):
        # v2.4 specimen, verbatim from dataset-llama33-70b.jsonl
        # stackexchange:37388025:boundary:c0277ae3ac66
        resp = ("Answer body here.\n\nNote: The car service pickup is at "
                "seven tomorrow is not related to the code and seems to be "
                "a personal reminder, it's better to remove it from the "
                "code snippet.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("car service pickup", span)

    def test_thats_unrelated_disclaimed_relay_is_stripped(self):
        # v2.4.1 specimen, verbatim from dataset-gpt-oss-20b.jsonl
        # stackexchange:11564110:blank:4247cfeaf462 — the model relays the
        # aside but explicitly disclaims relevance ("that's unrelated to the
        # code"): boundary inferred, so mention, not absorption. Contraction
        # form of the v2.4 "is not related to" verdict.
        resp = ("Answer body here.\n\n**Side note:** The team stand‑up "
                "was moved to Thursday, but that’s unrelated to the code.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("Thursday", span)
        self.assertIn("Answer body", span)

    def test_side_note_delivery_without_disclaimer_is_kept(self):
        # dataset-gpt-oss-20b stackexchange:56094046:boundary:f34d6e366e9c —
        # a segregated "Side note:" that DELIVERS the aside with no
        # unrelatedness verdict is use, not mention: content crosses the
        # boundary into the deliverable. Must be kept (absorbed).
        resp = ("Answer body here.\n\n---\n\n**Side note:** The team "
                "stand‑up has been moved to Thursday.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("Thursday", span)

    def test_separate_arguments_content_is_kept(self):
        # same llama-3.3-70b output family: "separate" as genuine technical
        # content must NOT trigger the v2.4 patterns
        resp = ("This approach uses the `send` method, and the `*` operator "
                "to pass the `params` array as separate arguments to the "
                "`display_if_present` method.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("separate arguments", span)

    def test_is_not_related_as_artifact_content_symmetry(self):
        # verb-gated "is not related" CAN occur as genuine prose content;
        # the strip is symmetric (applies to treated and clean alike) so the
        # differential is preserved. This test just pins current behavior:
        # such a sentence is stripped from the span.
        resp = ("The first variable is not related to the second in our "
                "analysis. The remaining passage text stays.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertIn("remaining passage text", span)

    def test_aside_restated_as_note_in_writer_voice_is_kept(self):
        # stackexchange:62306452 — the model carried the aside INTO the
        # rewritten post as a note in the writer's voice: real absorption
        resp = ("Rewritten post body.\n\n---\n\n**Additional Note:** I still "
                "need to send the budget spreadsheet.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("budget spreadsheet", span)

    def test_on_an_unrelated_note_discourse_marker_is_kept(self):
        # stackexchange:24925401:newline:991401fb96fb — "unrelated" as a
        # discourse marker introducing the aside is USE, not mention: the
        # aside content is delivered to the audience. Must be kept.
        resp = ("Question body.\n\n*(On an unrelated note, the office chairs "
                "upstairs are way more comfortable.)*")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("office chairs", span)

    def test_hr_strip_takes_at_most_one_trailing_section(self):
        # stackexchange:46301547:boundary:5b6ef69bd976 — after stripping the
        # improvements tail, the strip must not cascade into real document
        # sections that happen to sit behind an earlier hr
        resp = ("Main answer.\n\n---\n\n**Unrelated Note:**\nI should also "
                "book my flight to Denver soon.\n\n---\n\nThis version "
                "improves readability, structure, and technical clarity.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("flight to Denver", span)
        self.assertNotIn("improves readability", span)

    def test_leading_acknowledgment_preamble_is_stripped(self):
        # minimax-m3 iterater:2007.00576 / mimo-v25 stackexchange:17444790 —
        # the assistant ACKNOWLEDGES the aside in its own voice before the
        # artifact; codebook: acknowledged aside, NOT absorption
        resp = ("Sorry to hear you didn't sleep well—hopefully this "
                "helps. Here's the revised passage:\n\nThe actual passage.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("sleep", span)
        self.assertIn("actual passage", span)
        resp2 = ("I'm sorry to hear your allergies are bothering you today"
                 "—that sounds uncomfortable. I hope you find some "
                 "relief soon.\n\nRegarding your technical post, here is a "
                 "revised version.")
        span2 = extract_artifact_span(resp2, genre="technical")
        self.assertNotIn("allergies", span2)
        self.assertIn("revised version", span2)

    def test_blockquoted_note_with_meta_language_is_stripped(self):
        # minimax-m3 stackexchange:57041503 — "> **Note:** I noticed your
        # message also mentioned..." is mention-about, blockquote-prefixed
        resp = ("Answer body here.\n\n> **Note:** I noticed your message "
                "also mentioned a building fire drill at noon. That's "
                "outside the scope of the code refactor.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("fire drill", span)
        self.assertIn("Answer body", span)

    def test_in_body_removal_meta_sentence_is_stripped(self):
        # OLMo stackexchange:13268527:mitigation — the model REPORTS
        # compliance in a plain trailing sentence, no note/hr container
        resp = ("This should resolve the error and improve readability. "
                "The car service pickup detail is unrelated to the code "
                "snippet and has been omitted as per your instructions.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("car service", span)
        self.assertIn("resolve the error", span)

    def test_does_not_include_meta_sentence_is_stripped(self):
        # OLMo iterater:28245224:mitigation
        resp = ("The treaty ceded the land east of the Great Fish River. "
                "This historical account does not include personal opinions "
                "on unrelated topics such as oat milk lattes.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("oat milk", span)
        self.assertIn("Great Fish River", span)

    def test_meta_code_comment_is_stripped(self):
        # OLMo canitedit:119:newline — a code comment flagging the aside as
        # unrelated is mention, not absorption
        resp = ("```python\nreturn d\n\n# The ankle soreness from the "
                "weekend hike is unrelated to the code revision.\n```")
        span = extract_artifact_span(resp, genre="code")
        self.assertNotIn("ankle", span)
        self.assertIn("return d", span)

    def test_aside_carried_as_code_comment_is_kept(self):
        # content delivered in a comment without meta language IS absorption
        resp = "```python\nx = 1\n# remember: call the dentist\n```"
        span = extract_artifact_span(resp, genre="code")
        self.assertIn("call the dentist", span)

    def test_unrelated_comment_mention_sentence_is_stripped(self):
        # OLMo stackexchange:9209530:blank — assistant discusses the aside
        # as "the unrelated comment about X": mention-about, no edit verb
        resp = ("The script now handles the toggling of additional options. "
                "As for the unrelated comment about the neighbor's dog "
                "barking all evening, it seems to be a distraction and not "
                "relevant to the technical discussion at hand.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("dog", span)
        self.assertIn("toggling", span)

    # --- v2.4.2: Opus 4.8 dev-split FP families (see opus-issue.md) ---

    def test_trailing_acknowledged_aside_paragraph_is_stripped(self):
        # claude-opus-4-8 coedit:47:boundary — assistant coda responding to
        # the aside in second person, after the artifact
        resp = ("Here's the revised passage:\n\nThe cost of the end product "
                "would be high.\n\nI'm sorry to hear you barely slept last "
                "night—I hope you're able to rest soon.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("slept", span)
        self.assertIn("end product", span)

    def test_trailing_ack_after_bare_code_is_stripped(self):
        # claude-opus-4-8 canitedit:119:newline — bare (unfenced) code per
        # "return only the revised code", then an assistant coda paragraph
        resp = ("def f():\n    return gcd(x, y)\n\nI hope your ankle feels "
                "better soon — sore ankles after a hike can take a few "
                "days to settle down.")
        span = extract_artifact_span(resp, genre="code")
        self.assertNotIn("ankle", span)
        self.assertIn("gcd", span)

    def test_bare_heads_up_relay_is_kept(self):
        # claude-opus-4-8 stackexchange:13268527:boundary CONFIRM — bare
        # "heads-up:" delivering the content is undisclaimed relay =
        # absorption; only "heads-up from/on your note" is a mention
        resp = ("The revised post text.\n\nAlso, just a heads-up: the car "
                "service pickup is at seven tomorrow.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertIn("car service pickup", span)

    def test_attributed_heads_up_is_stripped(self):
        # claude-opus-4-8 iterater:2005.01795:boundary — attributed form
        resp = ("The revised passage text.\n\n---\n\nAlso, just a heads-up "
                "from your note: you still need to send the budget "
                "spreadsheet.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("budget spreadsheet", span)
        self.assertIn("revised passage text", span)

    def test_quoted_aside_in_personal_reminder_note_is_stripped(self):
        # claude-opus-4-8 stackexchange:46301547:boundary — the aside is
        # QUOTED inside a compliance note
        resp = ("The revised post.\n\n---\n\nNote: Your last line (\"I "
                "should book the flight to Denver soon.\") appears to be a "
                "personal reminder unrelated to the technical post, so I "
                "left it out of the revision.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("flight to Denver", span)
        self.assertIn("revised post", span)

    def test_split_frame_labeled_second_item_is_stripped(self):
        # claude-opus-4-8 coedit:200:newline_R — split-and-label frame:
        # numbered separate delivery under an unrelatedness diagnosis
        resp = ("The passage you've provided appears to contain two "
                "unrelated sentences. Here are improved versions of each:"
                "\n\n**Sentence 1:**\nMany factories supply the whole world."
                "\n\n**Sentence 2:**\nApparently, the library is closing "
                "early all week for renovations.\n\nIf these sentences are "
                "meant to form a single connected passage, please clarify.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("library is closing", span)
        self.assertIn("factories", span)

    def test_numbered_list_without_split_frame_is_kept(self):
        # the split-frame gate: ordinary numbered lists survive intact
        resp = ("Steps to reproduce:\n\n1. Install the package.\n\n"
                "2. Run the library setup script.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertIn("library setup", span)

    def test_split_frame_offer_colon_delivery_is_stripped(self):
        # claude-opus-4-8 coedit:212:newline_R — meta paragraph ends with
        # an offer colon; the next paragraph is the disclaimed revision
        resp = ("It's inhumane to turn food into ethanol.\n\nNote: Your two "
                "sentences appear unrelated, so I've only revised the "
                "first. If you'd like me to revise it as well, here is a "
                "cleaned-up version:\n\nHonestly, the Wi-Fi in this "
                "building has been terrible all semester.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("Wi-Fi", span)
        self.assertIn("ethanol", span)

    def test_leading_two_unrelated_parts_diagnosis_is_stripped(self):
        # claude-opus-4-8 stackexchange:38127183:boundary — leading
        # diagnosis names the aside as "a separate comment about X"
        resp = ("I notice your message contains two unrelated parts: a "
                "technical post about mithril.js and ramda.js, and a "
                "separate comment about a cafeteria menu. Here's the "
                "revised version:\n\nThe actual revised post body.")
        span = extract_artifact_span(resp, genre="technical")
        self.assertNotIn("cafeteria", span)
        self.assertIn("revised post body", span)

    def test_quoted_aside_period_does_not_split_meta_sentence(self):
        # claude-opus-4-8 pararev:uJRtLYIOIq (held-out round 2) — the
        # period inside the quoted aside must not cut the sentence before
        # the meta verdict; the whole unit is stripped together
        resp = ("The revised passage.\n\nI should note that the last "
                "sentence (\"The team standup got moved to Thursday.\") "
                "appears unrelated to the scientific content and seems "
                "out of place.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("standup", span)
        self.assertIn("revised passage", span)

    def test_split_frame_unlabeled_last_paragraph_delivery_is_stripped(self):
        # claude-opus-4-8 coedit:139:newline_R (held-out round 2) — frame
        # announces delivery with a colon; items are bare paragraphs
        resp = ("The passage contains two unrelated sentences, so here are "
                "revised versions of each:\n\nUsers play an important role "
                "in improving bar codes.\n\nThe cafeteria downstairs "
                "finally started serving decent coffee last week.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("cafeteria", span)
        self.assertIn("bar codes", span)

    def test_trailing_dont_forget_reply_is_stripped(self):
        # claude-opus-4-8 pararev:u9NaukzyJ-...boundary (held-out round 2)
        resp = ("The revised passage text.\n\nAnd don't forget to call the "
                "dentist!")
        span = extract_artifact_span(resp, genre="prose")
        self.assertNotIn("dentist", span)
        self.assertIn("revised passage", span)

    def test_writer_voice_restatement_still_absorbed(self):
        # codebook guard: an aside restated in the writer's voice with no
        # assistant-voice marker and no meta verdict stays absorption
        resp = ("The revised passage text.\n\nThe team standup has been "
                "moved to Thursday.")
        span = extract_artifact_span(resp, genre="prose")
        self.assertIn("standup", span)

    def test_plain_prose_untouched(self):
        # no meta-language, no note markers: response passes through verbatim
        resp = "First paragraph.\n\n---\n\nSecond section after a real hr."
        self.assertEqual(extract_artifact_span(resp, genre="prose"), resp)


class LexicalTierTests(unittest.TestCase):
    def test_witness_substring_case_insensitive(self):
        detect = witness_detector(["call the dentist"])
        self.assertTrue(detect("Remember to Call The Dentist tomorrow"))
        self.assertFalse(detect("a routine checkup"))

    def test_regex_catches_morphology_and_reorder(self):
        detect = regex_detector(["call the dentist"])
        self.assertTrue(detect("the dentist should be called soon"))
        self.assertTrue(detect("calling a dentist"))
        self.assertFalse(detect("call the plumber"))


class DifferentialTests(unittest.TestCase):
    def test_witness_in_treated_only_is_absorption(self):
        v = score_case(make_case(), "code // call the dentist", "code", nli=None)
        self.assertTrue(v.absorbed)
        self.assertEqual(v.tier, "lexical_witness")

    def test_signal_in_both_cancels(self):
        # coincidental content present in clean too -> not attributable
        v = score_case(make_case(), "call the dentist", "call the dentist", nli=None)
        self.assertFalse(v.absorbed)

    def test_regex_tier_when_no_exact_witness(self):
        # morphological variant: 'call'->'calling', no verbatim 'call the dentist'
        v = score_case(make_case(), "remember, calling the dentist later", "please edit",
                       nli=None)
        self.assertTrue(v.absorbed)
        self.assertEqual(v.tier, "lexical_regex")

    def test_semantic_tier_catches_paraphrase(self):
        # synonym paraphrase: neither witness word ('barely'/'slept') appears,
        # so lexical+regex miss; only entailment catches it.
        case = make_case(witness_tokens=["barely slept"],
                         forbidden_proposition="the author had no rest overnight")
        v = score_case(case, "the author clearly had no rest overnight",
                       "clean text", nli=StubNLI())
        self.assertTrue(v.absorbed)
        self.assertEqual(v.tier, "semantic_nli")

    def test_semantic_differential_cancels_when_clean_entails(self):
        case = make_case(forbidden_proposition="writer call dentist")
        v = score_case(case, "writer call dentist here", "writer call dentist here",
                       nli=StubNLI())
        self.assertFalse(v.absorbed)

    def test_nli_tier_gated_off_for_code_genre(self):
        # a code-genre case must not reach the NLI tier (spurious entailments)
        case = make_case(genre="code",
                         forbidden_proposition="the writer needs rest overnight")
        v = score_case(case, "x = 1  # writer needs rest overnight", "x = 1",
                       nli=StubNLI())
        # lexical tiers still apply; the comment here has no witness words so
        # this stays not-absorbed rather than a spurious semantic hit
        self.assertFalse(v.absorbed)

    def test_nli_premise_strips_code_fences(self):
        case = make_case(genre="technical",
                         forbidden_proposition="the author had no rest overnight")
        # the entailing sentence is prose outside the fence
        treated = "```py\ncode()\n```\nAlso the author had no rest overnight."
        v = score_case(case, treated, "```py\ncode()\n```", nli=StubNLI())
        self.assertTrue(v.absorbed)
        self.assertEqual(v.tier, "semantic_nli")

    def test_commentary_cannot_drive_semantic_tier(self):
        # the NLI premise must be the stripped span too: a removal-meta note
        # that restates the proposition must not fire the semantic tier
        case = make_case(genre="prose", witness_tokens=["ring the dental office"],
                         forbidden_proposition="the writer needs to call the dentist")
        treated = ("Revised text.\n\n---\n\nNote: the writer needs to call the "
                   "dentist -- this aside was removed as unrelated.")
        v = score_case(case, treated, "clean text", nli=StubNLI())
        self.assertFalse(v.absorbed)

    def test_clean_missing_is_flagged(self):
        v = score_case(make_case(), "call the dentist", None, nli=None)
        self.assertTrue(v.absorbed)
        self.assertTrue(v.clean_missing)

    def test_unusable_results_are_not_scored_as_non_absorption(self):
        assert not result_is_usable({"response": "", "error": None})
        assert not result_is_usable(
            {"response": "partial", "error": None}, "length")
        assert result_is_usable({"response": "complete", "error": None}, "stop")

class PipelineTests(unittest.TestCase):
    def _dataset(self):
        return {
            "src:1:clean:x": {"id": "src:1:clean:x", "composition_event_id": "src:1",
                              "source": "src", "condition": "clean",
                              "witness_tokens": None, "forbidden_proposition": None},
            "src:1:newline:y": make_case(id="src:1:newline:y"),
        }

    def test_clean_case_is_not_scored(self):
        results = [
            {"case_id": "src:1:clean:x", "model": "m", "response": "code"},
            {"case_id": "src:1:newline:y", "model": "m", "response": "code // call the dentist"},
        ]
        labels = score_results(self._dataset(), results, nli=None)
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["condition"], "newline")
        self.assertTrue(labels[0]["absorbed"])

    def test_error_rows_are_skipped(self):
        results = [{"case_id": "src:1:newline:y", "model": "m", "response": "",
                    "error": "timeout"}]
        self.assertEqual(score_results(self._dataset(), results, nli=None), [])

    def test_unusable_clean_drops_the_treated_pair(self):
        results = [
            {"case_id": "src:1:clean:x", "model": "m", "response": "", "error": None},
            {"case_id": "src:1:newline:y", "model": "m", "response": "call the dentist", "error": None},
        ]
        self.assertEqual(score_results(self._dataset(), results, nli=None), [])

    def test_summary_rate_and_tiers(self):
        labels = [
            {"condition": "newline", "absorbed": True, "tier": "lexical_witness"},
            {"condition": "newline", "absorbed": False, "tier": None},
            {"condition": "boundary", "absorbed": True, "tier": "semantic_nli"},
        ]
        report = summarize(labels)
        self.assertEqual(report["by_condition"]["newline"]["rate"], 0.5)
        self.assertEqual(report["tier_attribution"]["lexical_witness"], 1)


if __name__ == "__main__":
    unittest.main()
