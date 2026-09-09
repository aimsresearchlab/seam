"""LLM structural judge for wild paste-then-continue candidates (vLLM offline).

Stage 2 of the cascade in `research/WILD_MINING_DESIGN.md`. Given candidate
messages that already passed the deterministic screen, an open-weight judge
decides whether each is a genuine instance of the SEAM composition shape: an
UNMARKED embedded artifact (looks pasted / externally authored) combined with a
user-authored instruction or continuation that OPERATES ON that artifact.

The judge is validated against the 50 human labels before any full run
(`--gold` -> agreement report). Deterministic: temperature 0, thinking off.

Usage:
    python3 tools/wild_judge.py --model Qwen/Qwen3-14B \
        --in judge_gold.jsonl --out judge_out.jsonl --gold
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

INSTRUCTION = """You are labeling real chat messages for a linguistics study.

We are looking for ONE specific shape: a pasted ARTIFACT that comes FIRST (or is \
dropped in with no framing), FOLLOWED by a short typed user INSTRUCTION or \
continuation, with NO leading command and NO explicit boundary marker. The \
boundary between pasted and typed text is ambiguous. This is the target.

A message is POSITIVE only when ALL hold:
  (A) it contains an embedded ARTIFACT: a block that reads as pasted or externally \
authored -- a document, article, email, code file, dataset, transcript, etc.;
  (B) there is a user-authored INSTRUCTION or CONTINUATION that operates on it \
(fix it, translate it, reply to it, critique it, answer about it, continue it); AND
  (C) the artifact comes FIRST / unframed, and the instruction is NOT a leading \
command that introduces the artifact.

A message is NEGATIVE when any of these hold:
  - LEADING/MARKED instruction that introduces the artifact -- e.g. \
"Summarize this:", "translate the following:", "fix this code:", "please edit \
the following as an email:". A command up front + a colon/"the following" is a \
MARKED boundary, NOT our target. This is NEGATIVE even though it has an artifact \
and an instruction.
  - it is only a pasted artifact with no user instruction that operates on it;
  - the short leading/trailing text is actually part of the artifact itself \
(a title, a byline, a disclaimer, a signature, the article's own ending);
  - it is a single coherent prompt the user wrote themselves with no embedded \
external artifact (e.g. a long creative-writing brief, a roleplay setup);
  - it is template / agent / API scaffolding (CONSTRAINTS:/COMMANDS:, "You are a...").

Reply with ONE line of strict JSON and nothing else:
{"genuine": true|false, "confidence": 0.0-1.0, "genre": "code|email|document|qa|creative|academic|data|other", "reason": "<=15 words"}

MESSAGE:
<<<
%s
>>>"""

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def window(msg: str, max_chars: int) -> str:
    """Keep BOTH ends: the pattern is [artifact body][short typed tail], so
    front-truncation would drop the defining continuation. Preserve head +
    tail with the middle elided."""
    if len(msg) <= max_chars:
        return msg
    head = int(max_chars * 0.6)
    tail = max_chars - head
    return msg[:head] + "\n\n...[ARTIFACT BODY TRUNCATED]...\n\n" + msg[-tail:]


def parse_verdict(text: str) -> dict:
    m = JSON_RE.findall(text)
    if not m:
        return {"genuine": None, "confidence": None, "genre": None,
                "reason": "PARSE_FAIL", "raw": text[:200]}
    try:
        d = json.loads(m[-1])
        d["genuine"] = bool(d.get("genuine"))
        return d
    except Exception:
        return {"genuine": None, "confidence": None, "genre": None,
                "reason": "PARSE_FAIL", "raw": text[:200]}


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(x == y for x, y in zip(a, b)) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-14B")
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-chars", type=int, default=6000,
                    help="truncate artifact body fed to the judge")
    ap.add_argument("--gpu-mem-util", type=float, default=0.90)
    ap.add_argument("--max-model-len", type=int, default=16384)
    ap.add_argument("--gold", action="store_true",
                    help="input has a 'gold' field; emit agreement report")
    args = ap.parse_args()

    from vllm import LLM, SamplingParams
    from transformers import AutoTokenizer

    records = [json.loads(l) for l in open(args.inp) if l.strip()]
    tok = AutoTokenizer.from_pretrained(args.model)
    # Window by TOKENS, not chars: token-dense content (CJK/code/emoji) can
    # tokenize to far more tokens than chars and blow past max_model_len,
    # aborting the whole vLLM batch. Budget leaves room for the instruction
    # wrapper + 200 output tokens. Preserve head+tail (the pattern's tail is
    # the defining continuation).
    budget = args.max_model_len - 700

    def tok_window(msg: str) -> str:
        ids = tok.encode(msg, add_special_tokens=False)
        if len(ids) <= budget:
            return msg
        h = int(budget * 0.6)
        t = budget - h
        return (tok.decode(ids[:h]) +
                "\n\n...[ARTIFACT BODY TRUNCATED]...\n\n" +
                tok.decode(ids[-t:]))

    # vLLM 0.8.5 LLM.chat() has no chat_template_kwargs; apply the template
    # manually so Qwen3 thinking-mode stays off (non-thinking is our primary).
    prompts = [tok.apply_chat_template(
        [{"role": "user", "content": INSTRUCTION % tok_window(r["msg"])}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
        for r in records]

    llm = LLM(model=args.model, gpu_memory_utilization=args.gpu_mem_util,
              max_model_len=args.max_model_len, enforce_eager=False)
    sp = SamplingParams(temperature=0.0, max_tokens=200)

    t0 = time.time()
    outs = llm.generate(prompts, sp)
    dt = time.time() - t0

    gen_tok = sum(len(o.outputs[0].token_ids) for o in outs)
    results = []
    with open(args.out, "w") as fh:
        for r, o in zip(records, outs):
            v = parse_verdict(o.outputs[0].text)
            row = {"hash": r.get("hash"), **v}
            if "gold" in r:
                row["gold"] = r["gold"]
            results.append(row)
            fh.write(json.dumps(row) + "\n")

    print(f"\n=== throughput ===")
    print(f"{len(records)} records in {dt:.1f}s = {len(records)/dt:.2f} rec/s; "
          f"{gen_tok} gen tokens = {gen_tok/dt:.0f} tok/s")
    parse_fail = sum(1 for r in results if r["genuine"] is None)
    print(f"parse failures: {parse_fail}/{len(results)}")

    if args.gold:
        pairs = [(r["genuine"], r["gold"] == "genuine") for r in results
                 if r["genuine"] is not None]
        pred = [p for p, _ in pairs]
        gold = [g for _, g in pairs]
        n = len(pairs)
        tp = sum(p and g for p, g in pairs)
        tn = sum((not p) and (not g) for p, g in pairs)
        fp = sum(p and not g for p, g in pairs)
        fn = sum((not p) and g for p, g in pairs)
        acc = (tp + tn) / n if n else 0
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        print(f"\n=== judge vs human (n={n}) ===")
        print(f"accuracy {acc:.3f} | kappa {cohen_kappa(pred, gold):.3f}")
        print(f"precision(genuine) {prec:.3f} | recall {rec:.3f} | F1 {f1:.3f}")
        print(f"confusion: TP={tp} TN={tn} FP={fp} FN={fn}")


if __name__ == "__main__":
    main()
