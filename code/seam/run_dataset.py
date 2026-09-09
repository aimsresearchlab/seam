"""Run a JSONL SEAM dataset through an OpenAI-compatible provider."""

import argparse
import concurrent.futures as cf
import datetime
import json
from pathlib import Path

from api_client import add_provider_arguments, make_client


def call(client, model, case, max_tokens, request_timeout, temperature=0.0,
         chat_template_kwargs=None, extra_body=None):
    messages = []
    if case.get("system_instruction"):
        messages.append({"role": "system", "content": case["system_instruction"]})
    messages.append({"role": "user", "content": case["message"]})
    request = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        request["max_tokens"] = max_tokens
    merged_extra = dict(extra_body or {})
    if chat_template_kwargs:
        merged_extra["chat_template_kwargs"] = chat_template_kwargs
    if merged_extra:
        request["extra_body"] = merged_extra
    try:
        request_client = (client.with_options(max_retries=0)
                          if hasattr(client, "with_options") else client)
        response = request_client.chat.completions.create(
            **request, timeout=request_timeout)
        finish_reason = response.choices[0].finish_reason
        row = {"model": model, "case_id": case["id"],
               "response": response.choices[0].message.content or "",
               "finish_reason": finish_reason, "error": None}
        if temperature != 0.0:
            row["temperature"] = temperature
        trace = {"case_id": case["id"], "request": request,
                 "response": response.model_dump()}
    except Exception as error:  # noqa: BLE001
        message = f"{type(error).__name__}: {error}"
        row = {"model": model, "case_id": case["id"], "response": "", "error": message}
        trace = {"case_id": case["id"], "request": request, "error": message}
    return row, trace


def completed_pairs(output: Path, trace_path: Path | None = None) -> set[tuple[str, str]]:
    """Pairs whose latest row is usable and did not finish by truncation.

    Older result files lack ``finish_reason``, so consult their companion trace
    file when available. Missing, errored, empty, and length-truncated results
    remain incomplete and are retried by ``--resume``.
    """
    latest = {}
    with output.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            latest[(row["model"], row["case_id"])] = row

    trace_finish = {}
    if trace_path and trace_path.exists():
        with trace_path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                trace = json.loads(line)
                request = trace.get("request") or {}
                response = trace.get("response") or {}
                choices = response.get("choices") or []
                finish = choices[0].get("finish_reason") if choices else None
                trace_finish[(request.get("model"), trace.get("case_id"))] = finish

    done = set()
    for pair, row in latest.items():
        finish = row.get("finish_reason", trace_finish.get(pair))
        if (not row.get("error") and row.get("response")
                and finish != "length"):
            done.add(pair)
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--models", nargs="+", default=["deepseek-v4-flash"])
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--parallel-requests", "--parallelism", dest="parallel_requests",
        type=int, default=12,
        help="Maximum number of API requests in flight at once (default: 12).",
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--temperature", type=float, default=0.0,
        help="Sampling temperature (default: 0.0). Non-zero values are "
             "recorded on each result row so deviations stay visible.",
    )
    parser.add_argument(
        "--chat-template-kwargs", type=json.loads, default=None,
        help="JSON object passed as extra_body chat_template_kwargs (e.g. "
             '\'{"enable_thinking": false}\' for Qwen3 non-thinking mode).',
    )
    parser.add_argument(
        "--extra-body", type=json.loads, default=None,
        help="JSON object merged into the request extra_body (e.g. OpenRouter "
             'provider pinning: \'{"provider": {"order": ["deepinfra"], '
             '"allow_fallbacks": false, "quantizations": ["bf16"]}}\'). '
             "Open-weight models are served at different quantizations by "
             "different providers; pin both so rows are comparable.",
    )
    parser.add_argument(
        "--request-timeout", type=float, default=300,
        help="Per-request timeout in seconds (default: 300).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--output", type=Path,
        help="Results JSONL path (default: seam/results/dataset-<ts>.jsonl). "
             "Rows are appended as calls complete, so a crashed run keeps "
             "everything already finished.",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Requires --output. Skip (model, case) pairs that already have a "
             "successful row in the output file; errored rows are retried and "
             "re-appended (readers keep the last row per case).",
    )
    add_provider_arguments(parser, default_provider="deepseek")
    args = parser.parse_args()
    if args.resume and not args.output:
        parser.error("--resume requires --output")
    if args.max_tokens < 0:
        parser.error("--max-tokens must be nonnegative (0 omits the cap)")
    if args.request_timeout <= 0:
        parser.error("--request-timeout must be positive")

    with args.dataset.open() as handle:
        cases = [json.loads(line) for line in handle]
    if args.limit is not None:
        cases = cases[:args.limit]
    calls = len(cases) * len(args.models)
    config = __import__("api_client").resolve_provider(args)
    print(f"provider={config.name}")
    print(f"base_url={config.base_url}")
    print(f"models={','.join(args.models)}")
    if args.parallel_requests < 1:
        parser.error("--parallel-requests must be at least 1")
    print(
        f"cases={len(cases)} calls={calls} "
        f"max_tokens={'provider-default' if args.max_tokens == 0 else args.max_tokens} "
        f"request_timeout={args.request_timeout:g}s "
        f"parallel_requests={args.parallel_requests} "
        f"temperature={args.temperature:g}"
    )
    if args.dry_run:
        print("dry_run=true; no API requests sent")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.output or (
        Path(__file__).parent / "results" / f"dataset-{timestamp}.jsonl")
    if output.exists() and not args.resume:
        raise SystemExit(f"{output} exists; pass --resume to continue it or "
                         "choose a different --output")
    trace_path = (output.with_suffix(".traces.jsonl") if args.output
                  else Path(__file__).parent.parent / "traces" / f"run-{timestamp}.jsonl")

    jobs = [(model, case) for model in args.models for case in cases]
    if args.resume and output.exists():
        done = completed_pairs(output, trace_path)
        skipped = len(jobs)
        jobs = [(m, c) for m, c in jobs if (m, c["id"]) not in done]
        skipped -= len(jobs)
        print(f"resume: {skipped} already complete, {len(jobs)} to run")

    client, _ = make_client(args)
    errors = 0
    trace_path.parent.mkdir(exist_ok=True)
    with output.open("a") as out_handle, trace_path.open("a") as trace_handle, \
            cf.ThreadPoolExecutor(max_workers=args.parallel_requests) as executor:
        futures = [executor.submit(call, client, model, case, args.max_tokens,
                                   args.request_timeout, args.temperature,
                                   args.chat_template_kwargs, args.extra_body)
                   for model, case in jobs]
        for future in cf.as_completed(futures):
            row, trace = future.result()
            errors += bool(row["error"])
            out_handle.write(json.dumps(row) + "\n")
            out_handle.flush()
            trace_handle.write(json.dumps(trace) + "\n")
            trace_handle.flush()
    print(f"saved={output} traces={trace_path} errors={errors}")


if __name__ == "__main__":
    main()
