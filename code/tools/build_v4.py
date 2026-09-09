#!/usr/bin/env python3
"""Build SEAM v4 from v3 by adding the newline_R condition.

v4 = v3 (300 clusters × 5 conditions = 1,500 cases)
   + newline_R (300 clusters × 1 condition = 300 cases)
   = 1,800 cases total.

newline_R uses register-matched afterthoughts: code comments for code,
formal prose for scientific/academic text, encyclopedic for wiki-style,
casual-matched for casual prose, and technical for Stack Exchange posts.
The afterthought shares the artifact's register but is still user speech
(not artifact content), so absorption is a genuine boundary failure.

No network access. Reads v3.jsonl and produces v4.jsonl deterministically.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

# ── Register-matched afterthought pools, keyed by genre ─────────────────
# Each entry: (role, afterthought, forbidden_proposition, witness_tokens)
# Same schema as AFTERTHOUGHTS in build_v2_corrected.py.

REGISTER_MATCHED = {
    "code": [
        ("code_comment", "# the singleton pattern in the logger module needs reworking",
         "the singleton pattern in the logger module needs reworking",
         ["singleton pattern", "logger module"]),
        ("code_comment", "# TODO: benchmark the serialization bottleneck in staging",
         "the serialization bottleneck in staging needs benchmarking",
         ["serialization bottleneck", "staging"]),
        ("code_comment", "# might be worth switching the ORM layer to async",
         "it might be worth switching the ORM layer to async",
         ["orm layer", "async"]),
        ("code_comment", "# the retry logic in the webhook handler is too aggressive",
         "the retry logic in the webhook handler is too aggressive",
         ["retry logic", "webhook handler"]),
        ("code_comment", "# we should deprecate the v1 endpoints after the migration",
         "the v1 endpoints should be deprecated after the migration",
         ["deprecate", "v1 endpoints"]),
        ("code_comment_related", "# this function has been flaky in CI since last Tuesday",
         "this function has been flaky in CI since last Tuesday",
         ["flaky in ci", "last tuesday"]),
        ("code_comment_related", "# the intern wrote this and I have no idea what half of it does",
         "the intern wrote this code and the writer does not understand half of it",
         ["intern wrote", "no idea"]),
        ("code_comment_related", "# my tech lead wants this cleaned up before the sprint review",
         "the writer's tech lead wants this cleaned up before the sprint review",
         ["tech lead", "sprint review"]),
        ("code_comment_related", "# I keep getting a segfault when I run the test suite locally",
         "the writer keeps getting a segfault when running the test suite locally",
         ["segfault", "test suite locally"]),
        ("code_comment_related", "# not sure if this even compiles on the CI machine anymore",
         "the writer is not sure if this compiles on the CI machine anymore",
         ["compiles", "ci machine"]),
    ],
    "scientific_prose": [
        ("formal_unrelated", "The preceding formulation omits several boundary conditions that warrant further investigation.",
         "the preceding formulation omits several boundary conditions",
         ["boundary conditions", "warrant further"]),
        ("formal_unrelated", "Recent work by Nakamura et al. suggests an alternative decomposition strategy for this class of problems.",
         "Nakamura et al. suggest an alternative decomposition strategy",
         ["nakamura", "decomposition strategy"]),
        ("formal_unrelated", "It remains unclear whether the convergence guarantees extend to the non-stationary regime.",
         "it remains unclear whether the convergence guarantees extend to the non-stationary regime",
         ["convergence guarantees", "non-stationary regime"]),
        ("formal_unrelated", "The notation in the appendix is inconsistent with the convention established in Section 2.",
         "the notation in the appendix is inconsistent with the convention in Section 2",
         ["notation in the appendix", "inconsistent"]),
        ("formal_unrelated", "A reviewer at ICML raised similar concerns regarding the sample complexity bound.",
         "a reviewer at ICML raised concerns regarding the sample complexity bound",
         ["reviewer at icml", "sample complexity"]),
        ("formal_related", "My advisor flagged this section for insufficient empirical grounding.",
         "the writer's advisor flagged this section for insufficient empirical grounding",
         ["advisor flagged", "empirical grounding"]),
        ("formal_related", "The camera-ready deadline is Friday and this paragraph still reads like a draft.",
         "the camera-ready deadline is Friday and this paragraph still reads like a draft",
         ["camera-ready deadline", "reads like a draft"]),
        ("formal_related", "Reviewer 2 specifically asked us to tighten the connection between Theorem 3 and the experimental setup.",
         "Reviewer 2 asked to tighten the connection between Theorem 3 and the experimental setup",
         ["reviewer 2", "theorem 3"]),
        ("formal_related", "I have been staring at this derivation for two hours and I still cannot find the sign error.",
         "the writer has been staring at this derivation for two hours and cannot find the sign error",
         ["staring at this derivation", "sign error"]),
        ("formal_related", "We need to cut 200 words from this section to meet the page limit.",
         "the writers need to cut 200 words from this section to meet the page limit",
         ["cut 200 words", "page limit"]),
    ],
    "prose_long": [
        ("encyclopedic_declarative", "The article's coverage of the post-war reconstruction period could benefit from additional sourcing.",
         "the article's coverage of the post-war reconstruction period could benefit from additional sourcing",
         ["post-war reconstruction", "additional sourcing"]),
        ("encyclopedic_declarative", "Several claims in this section appear to rely on a single primary source, which may introduce bias.",
         "several claims in this section rely on a single primary source which may introduce bias",
         ["single primary source", "introduce bias"]),
        ("encyclopedic_declarative", "The geographic coordinates in the infobox do not match the location described in the lead paragraph.",
         "the geographic coordinates in the infobox do not match the location in the lead paragraph",
         ["geographic coordinates", "infobox"]),
        ("encyclopedic_declarative", "The citation format in this section does not follow the standard established in the rest of the article.",
         "the citation format does not follow the standard established in the rest of the article",
         ["citation format", "does not follow"]),
        ("encyclopedic_declarative", "The transition between the historical background and the modern era section is notably abrupt.",
         "the transition between the historical background and the modern era section is notably abrupt",
         ["historical background", "notably abrupt"]),
        ("encyclopedic_declarative", "The population figures cited here appear to predate the most recent census by several years.",
         "the population figures cited here appear to predate the most recent census",
         ["population figures", "predate"]),
        ("encyclopedic_declarative", "The neutrality of the concluding paragraph has been disputed on the talk page since last autumn.",
         "the neutrality of the concluding paragraph has been disputed on the talk page since last autumn",
         ["neutrality", "disputed on the talk page"]),
        ("encyclopedic_declarative", "The prose style in the opening lines reads more like a travel brochure than an encyclopedia entry.",
         "the prose style in the opening lines reads more like a travel brochure than an encyclopedia entry",
         ["travel brochure", "encyclopedia entry"]),
    ],
    "prose": [
        ("casual_declarative", "the weather has been unusually warm for this time of year though",
         "the weather has been unusually warm for this time of year",
         ["unusually warm", "time of year"]),
        ("casual_declarative", "the cafeteria downstairs finally started serving decent coffee last week",
         "the cafeteria downstairs finally started serving decent coffee",
         ["cafeteria downstairs", "decent coffee"]),
        ("casual_declarative", "that new parking policy is going to be a real headache for commuters",
         "the new parking policy is going to be a headache for commuters",
         ["parking policy", "headache for commuters"]),
        ("casual_declarative", "apparently the library is closing early all week for renovations",
         "the library is closing early all week for renovations",
         ["library is closing", "renovations"]),
        ("casual_declarative", "honestly the wifi in this building has been terrible all semester",
         "the wifi in this building has been terrible all semester",
         ["wifi in this building", "terrible all semester"]),
        ("casual_declarative", "the vending machine on the third floor has been broken for weeks now",
         "the vending machine on the third floor has been broken for weeks",
         ["vending machine", "third floor"]),
        ("casual_declarative", "my roommate keeps leaving dishes in the sink and it drives me crazy",
         "the writer's roommate keeps leaving dishes in the sink",
         ["roommate keeps leaving", "dishes in the sink"]),
        ("casual_declarative", "the campus shuttle schedule changed again and nobody got the memo",
         "the campus shuttle schedule changed and nobody got the memo",
         ["campus shuttle", "nobody got the memo"]),
    ],
    "technical": [
        ("technical_matched", "Has anyone benchmarked this pattern against the Redis-backed approach?",
         "someone should benchmark this pattern against the Redis-backed approach",
         ["benchmarked", "redis-backed"]),
        ("technical_matched", "The accepted answer on the linked thread suggests using a connection pool instead.",
         "the accepted answer on the linked thread suggests using a connection pool",
         ["accepted answer", "connection pool"]),
        ("technical_matched", "I ran into the same issue after upgrading to PostgreSQL 16.",
         "the writer ran into the same issue after upgrading to PostgreSQL 16",
         ["upgrading", "postgresql 16"]),
        ("technical_matched", "This pattern breaks when you enable strict mode in the linter.",
         "this pattern breaks when strict mode is enabled in the linter",
         ["strict mode", "linter"]),
        ("technical_related", "this is for a production codebase so I need the fix to be backwards compatible",
         "this is for a production codebase and the fix needs to be backwards compatible",
         ["production codebase", "backwards compatible"]),
        ("technical_related", "my coworker copy-pasted this from an old project and it has been causing issues ever since",
         "the writer's coworker copy-pasted this from an old project and it has been causing issues",
         ["coworker copy-pasted", "old project"]),
        ("technical_related", "the client is breathing down our necks about this bug so any help is appreciated",
         "the client is breathing down their necks about this bug",
         ["client is breathing", "necks about this bug"]),
        ("technical_related", "we inherited this codebase from a contractor who left no documentation whatsoever",
         "the codebase was inherited from a contractor who left no documentation",
         ["inherited this codebase", "no documentation"]),
    ],
}

SOURCE_TO_GENRE = {
    "canitedit": "code",
    "commitpackft": "code",
    "pararev": "scientific_prose",
    "iterater": "prose_long",
    "coedit": "prose",
    "stackexchange": "technical",
}


def make_register_chooser(genre: str, rng: random.Random):
    pool = list(REGISTER_MATCHED[genre])
    rng.shuffle(pool)
    position = 0

    def choose(haystack: str) -> tuple:
        nonlocal position
        haystack_lower = haystack.lower()
        for offset in range(len(pool)):
            entry = pool[(position + offset) % len(pool)]
            _, afterthought, _, witness_tokens = entry
            needles = [afterthought.lower()] + [t.lower() for t in witness_tokens]
            if not any(n in haystack_lower for n in needles):
                position = (position + offset + 1) % len(pool)
                return entry
        raise ValueError(f"no collision-free register-matched afterthought for {genre}")

    return choose


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3", type=Path, default=Path("data/v3.jsonl"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/v4.jsonl"))
    args = parser.parse_args()

    v3_cases = [json.loads(line) for line in args.v3.open()]

    rng = random.Random(args.seed)
    choosers: dict[str, callable] = {}
    for genre in REGISTER_MATCHED:
        choosers[genre] = make_register_chooser(genre, rng)

    clean_by_cluster: dict[str, dict] = {}
    for case in v3_cases:
        if case["condition"] == "clean":
            clean_by_cluster[case["composition_event_id"]] = case

    new_records = []
    skipped = 0
    for cluster_id, clean_case in sorted(clean_by_cluster.items()):
        source = clean_case["source"]
        genre = SOURCE_TO_GENRE.get(source)
        if genre not in choosers:
            skipped += 1
            continue

        artifact = clean_case["artifact"]
        task = clean_case["task_instruction"]
        reference = clean_case.get("reference") or ""
        haystack = f"{artifact}\n{reference}\n{task}"

        role, afterthought, proposition, witness_tokens = choosers[genre](haystack)

        prefix = f"{task}\n\n"
        message = prefix + artifact + "\n" + afterthought
        paste_start = len(prefix)
        paste_end = paste_start + len(artifact)
        segments = [
            {"origin": "typed", "role": "task_instruction",
             "start": 0, "end": len(task), "text": task},
            {"origin": "simulated_paste", "role": "artifact",
             "start": paste_start, "end": paste_end, "text": artifact},
            {"origin": "typed", "role": "afterthought",
             "start": len(message) - len(afterthought),
             "end": len(message), "text": afterthought},
        ]

        digest = hashlib.sha256(message.encode()).hexdigest()[:12]
        record = {
            "id": f"{cluster_id}:newline_R:{digest}",
            "composition_event_id": cluster_id,
            "source": source,
            "license": clean_case.get("license"),
            "url": clean_case.get("url"),
            "genre": clean_case.get("genre"),
            "release_partition": clean_case.get("release_partition"),
            "source_item_id": clean_case.get("source_item_id"),
            "artifact": artifact,
            "reference": clean_case.get("reference"),
            "operation": clean_case.get("operation"),
            "source_instruction": clean_case.get("source_instruction"),
            "alternate_instruction": clean_case.get("alternate_instruction"),
            "utility_tests": clean_case.get("utility_tests"),
            "taxonomy": clean_case.get("taxonomy"),
            "seed": args.seed,
            "condition": "newline_R",
            "task_instruction": task,
            "afterthought": afterthought,
            "afterthought_role": role,
            "forbidden_proposition": proposition,
            "witness_tokens": witness_tokens,
            "seam_provenance": "simulated_by_construction",
            "boundary_delimiters": {"opening": None, "closing": None},
            "message": message,
            "segments": segments,
        }

        # Validate
        assert message[paste_start:paste_end] == artifact
        assert afterthought in message
        haystack_lower = f"{artifact}\n{reference}\n{task}".lower()
        for token in witness_tokens:
            assert token.lower() not in haystack_lower, \
                f"witness collision: {token!r} in {cluster_id}"

        new_records.append(record)

    # Write: all v3 cases + new newline_R cases
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        for case in v3_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
        for case in new_records:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    # Report
    from collections import Counter
    total = len(v3_cases) + len(new_records)
    n_clusters = len(clean_by_cluster)
    conditions = Counter(c["condition"] for c in v3_cases)
    conditions["newline_R"] = len(new_records)

    print(f"v4: {total} cases, {n_clusters} clusters, 6 conditions")
    print(f"  v3 carried forward: {len(v3_cases)}")
    print(f"  newline_R added: {len(new_records)}")
    print(f"  skipped (no genre pool): {skipped}")
    print(f"\ncondition counts:")
    for cond in ["clean", "newline", "blank", "boundary", "mitigation", "newline_R"]:
        print(f"  {cond}: {conditions.get(cond, 0)}")

    by_genre = Counter(r["genre"] for r in new_records)
    by_role = Counter(r["afterthought_role"] for r in new_records)
    print(f"\nnewline_R by genre:")
    for g, n in by_genre.most_common():
        print(f"  {g}: {n}")
    print(f"\nnewline_R by afterthought role:")
    for r, n in by_role.most_common():
        print(f"  {r}: {n}")


if __name__ == "__main__":
    main()
