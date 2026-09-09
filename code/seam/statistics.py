"""Confidence intervals and inferential statistics for the SEAM paper tables.

Computes, from the canonical ``*.cascade-full.jsonl`` labels:

1.  Wilson 95% CIs for every model-by-condition absorption rate (Table 2 /
    Figure 2), plus exact zero-cell upper bounds for the "observed zero
    floor" claim.
2.  The complete within-model exact McNemar table (all 20 models, all
    planned contrasts), each with a Newcombe method-10 95% CI on the
    paired rate difference -- this turns the whitespace and Llama-3.1-8B
    null results into bounded nulls.
3.  Holm correction within each contrast family across the panel.
4.  Cluster-bootstrap 95% CIs for the lever ratio (newline AR / boundary
    AR), seeded and deterministic.
5.  Genre-gradient rates re-aggregated to cluster level (any absorption
    over newline+blank, n=50 clusters per source) with Wilson CIs and
    Fisher exact tests between adjacent sources -- the case-level n=100
    overstates precision because each cluster contributes two correlated
    observations.
6.  Between-model cluster-paired McNemar tests for the capability and
    endpoint claims (Flash vs Pro, M2.5 vs M3, OLMo vs Llama-3.1-8B).
7.  Spearman rank correlations across the 19-model panel (newline vs
    blank; newline rate vs lever), permutation p-values.

Register (newline_R) rates apply the manual acted-on/FP adjudications
recorded in research/SCORES.md, which is how Table 5 reports them; the
Opus boundary residual adjustment (2.0% -> 1.3%) is reported as a
sensitivity line, not applied to the main table, matching the paper.

Everything is deterministic: fixed seeds, no timestamps, stdlib only.
The JSON output records the SHA-256 of every input label file, of this
script, and of its own payload, so a rerun on unchanged labels is
byte-identical and any label drift is visible as a hash change.

Usage:
    python3 seam/statistics.py            # writes research/statistics.json
                                          # and research/STATISTICS.md
    python3 seam/statistics.py --check    # recompute and diff against the
                                          # committed statistics.json

``--results-dir`` and ``--out-dir`` move both ends of that off the repository
layout, which is how the public release runs this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "seam" / "results"
Z95 = 1.959963984540054
BOOTSTRAP_RESAMPLES = 10_000
PERMUTATIONS = 20_000
SEED = 42

# Panel registry in Table 2 order: key, paper name, label file, optional
# separate register-condition label file.
MODELS = [
    ("claude-opus-4-8", "Claude-Opus-4.8", "dataset-claude-opus-4-8.cascade-full.jsonl", None),
    ("gpt-5.6-sol", "GPT-5.6-sol", "dataset-gpt-5.6-sol.cascade-full.jsonl", None),
    ("gemini-3.1-pro", "Gemini-3.1-Pro", "dataset-gemini-3.1-pro.cascade-full.jsonl", None),
    ("deepseek-flash", "DeepSeek-V4-Flash", "dataset-deepseek-flash.cascade-full.jsonl",
     "v4-newline-R-flash-final.cascade-full.jsonl"),
    ("deepseek-pro", "DeepSeek-V4-Pro", "dataset-deepseek-pro.cascade-full.jsonl",
     "dataset-deepseek-pro-v4nr.cascade-full.jsonl"),
    ("minimax-m25", "MiniMax-M2.5", "dataset-minimax-m25.cascade-full.jsonl",
     "dataset-minimax-m25-v4nr.cascade-full.jsonl"),
    ("minimax-m3", "MiniMax-M3", "dataset-minimax-m3.cascade-full.jsonl",
     "dataset-minimax-m3-v4nr.cascade-full.jsonl"),
    ("mimo-v25", "MiMo-v2.5", "dataset-mimo-v25.cascade-full.jsonl",
     "dataset-mimo-v25-v4nr.cascade-full.jsonl"),
    ("mimo-v25-pro", "MiMo-v2.5-Pro", "dataset-mimo-v25-pro.cascade-full.jsonl",
     "dataset-mimo-v25-pro-v4nr.cascade-full.jsonl"),
    ("mistral-small-32-24b", "Mistral-Small-3.2-24B",
     "dataset-mistral-small-32-24b.cascade-full.jsonl",
     "dataset-mistral-small-32-24b-v4nr.cascade-full.jsonl"),
    ("qwen3-8b", "Qwen3-8B", "dataset-qwen3-8b.cascade-full.jsonl",
     "dataset-qwen3-8b-v4nr.cascade-full.jsonl"),
    ("qwen3-32b", "Qwen3-32B", "dataset-qwen3-32b.cascade-full.jsonl",
     "dataset-qwen3-32b-v4nr.cascade-full.jsonl"),
    ("olmo2-32b", "OLMo-2-32B", "dataset-olmo2-32b.cascade-full.jsonl",
     "dataset-olmo2-32b-v4nr.cascade-full.jsonl"),
    ("gpt-oss-20b", "gpt-oss-20b", "dataset-gpt-oss-20b.cascade-full.jsonl",
     "dataset-gpt-oss-20b-v4nr.cascade-full.jsonl"),
    ("gpt-oss-120b", "gpt-oss-120b", "dataset-gpt-oss-120b.cascade-full.jsonl",
     "dataset-gpt-oss-120b-v4nr.cascade-full.jsonl"),
    ("llama31-8b", "Llama-3.1-8B", "dataset-llama31-8b.cascade-full.jsonl",
     "dataset-llama31-8b-v4nr.cascade-full.jsonl"),
    ("llama33-70b", "Llama-3.3-70B", "dataset-llama33-70b.cascade-full.jsonl",
     "dataset-llama33-70b-v4nr.cascade-full.jsonl"),
    ("gemma3-4b", "Gemma-3-4B", "dataset-gemma3-4b.cascade-full.jsonl",
     "dataset-gemma3-4b-v4nr.cascade-full.jsonl"),
    ("gemma3-12b", "Gemma-3-12B", "dataset-gemma3-12b.cascade-full.jsonl",
     "dataset-gemma3-12b-v4nr.cascade-full.jsonl"),
    ("gemma3-27b", "Gemma-3-27B", "dataset-gemma3-27b.cascade-full.jsonl",
     "dataset-gemma3-27b-v4nr.cascade-full.jsonl"),
]

CONDITIONS = ["newline", "blank", "boundary", "mitigation", "newline_R"]
CONTRASTS = [
    ("newline", "blank"),
    ("newline", "boundary"),
    ("blank", "boundary"),
    ("boundary", "mitigation"),
    ("newline", "newline_R"),
]

# Manual adjudications from research/SCORES.md: acted-on cases (the model
# executed a declarative register-matched aside as an instruction) and one
# mention-type FP, removed from AR in Table 5. Keyed by model, flipped to
# absorbed=False before any register statistic.
MANUAL_ADJUDICATIONS = {
    "deepseek-flash": [
        "commitpackft:c4103c00b51ddb9cb837d65b43c972505e533bdc:tilescraper.py:newline_R:ee32c0b97034",
        "stackexchange:11564110:newline_R:a275a4b0fb4c",
    ],
    "qwen3-32b": [
        "commitpackft:c4103c00b51ddb9cb837d65b43c972505e533bdc:tilescraper.py:newline_R:ee32c0b97034",
    ],
    # gpt-5.6-sol acted-on cases come from its handread-verdicts file.
}

# verdict=false_positive rows in these files that are still positive in the
# canonical labels. For GPT these are the 3 acted-on register cases
# (applied, matching Table 5); for Opus they are the 2 documented boundary
# scorer residuals (reported as a sensitivity line only, matching Table 2).
HANDREAD_VERDICTS = {
    "gpt-5.6-sol": "dataset-gpt-5.6-sol.handread-verdicts.jsonl",
    "claude-opus-4-8": "dataset-claude-opus-4-8.handread-verdicts.jsonl",
}
ADJUDICATION_APPLIED_CONDITIONS = {"newline_R"}

PANEL_EXTENSION_VERDICTS = "v4nr-panel-handread-verdicts.jsonl"
OLMO_VERDICTS = "olmo2-32b-v4nr-handread-verdicts.jsonl"
GEMINI_VERDICTS = "dataset-gemini-3.1-pro.author-verdicts.jsonl"

UNUSABLE_CASE_IDS = {
    "llama33-70b": {
        "canitedit:103:newline_R:e638d572f53b",
        "canitedit:45:newline_R:8f9f90387096",
    },
    "mimo-v25-pro": {
        "iterater:105134:revision-1:newline_R:e3e145ec2cd1",
    },
}

GENRE_MODELS = ["deepseek-flash", "deepseek-pro", "claude-opus-4-8", "gpt-5.6-sol"]
GENRE_ORDER = ["coedit", "iterater", "pararev", "stackexchange", "canitedit", "commitpackft"]
REGISTER_MODELS = ["deepseek-flash", "qwen3-32b", "claude-opus-4-8", "gpt-5.6-sol"]
BETWEEN_MODEL_TESTS = [
    ("deepseek-pro", "deepseek-flash", ["newline", "blank", "boundary"]),
    ("minimax-m3", "minimax-m25", ["newline", "blank", "boundary"]),
    ("llama31-8b", "olmo2-32b", ["newline"]),
]


# ---------------------------------------------------------------- statistics

def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def exact_zero_upper(n: int, alpha: float = 0.05) -> float:
    """Clopper-Pearson 95% upper bound for an observed 0/n (closed form)."""
    return 1.0 - (alpha / 2) ** (1.0 / n)


def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact McNemar p from discordant counts (binomial)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def newcombe_paired_diff_ci(e11: int, e10: int, e01: int, e00: int,
                            z: float = Z95) -> tuple[float, float]:
    """Newcombe (1998) method-10 95% CI for a paired difference p1 - p2.

    e10 counts cluster positive under condition 1 only, e01 under
    condition 2 only.
    """
    n = e11 + e10 + e01 + e00
    if n == 0:
        return (0.0, 0.0)
    a, b = e11 + e10, e11 + e01  # successes under each condition
    p1, p2 = a / n, b / n
    l1, u1 = wilson_ci(a, n, z)
    l2, u2 = wilson_ci(b, n, z)
    denom = a * (n - a) * b * (n - b)
    phi = (e11 * e00 - e10 * e01) / math.sqrt(denom) if denom > 0 else 0.0
    d = p1 - p2
    lo = d - math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    hi = d + math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return (max(-1.0, lo), min(1.0, hi))


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, order-preserving."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted


def fisher_exact(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher exact p for two independent binomials."""
    total_k, total = k1 + k2, n1 + n2

    def hyper(x: int) -> float:
        return (
            math.comb(n1, x) * math.comb(n2, total_k - x) / math.comb(total, total_k)
        )
    lo = max(0, total_k - n2)
    hi = min(n1, total_k)
    p_obs = hyper(k1)
    return min(1.0, sum(hyper(x) for x in range(lo, hi + 1) if hyper(x) <= p_obs * (1 + 1e-9)))


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float], rng: random.Random) -> tuple[float, float]:
    """Spearman rho with a seeded permutation two-sided p-value."""
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(rx)

    def pearson(a: list[float], b: list[float]) -> float:
        ma, mb = sum(a) / n, sum(b) / n
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        va = math.sqrt(sum((x - ma) ** 2 for x in a))
        vb = math.sqrt(sum((y - mb) ** 2 for y in b))
        return cov / (va * vb) if va > 0 and vb > 0 else 0.0

    rho = pearson(rx, ry)
    hits = 0
    perm = list(ry)
    for _ in range(PERMUTATIONS):
        rng.shuffle(perm)
        if abs(pearson(rx, perm)) >= abs(rho) - 1e-12:
            hits += 1
    return rho, (hits + 1) / (PERMUTATIONS + 1)


# ------------------------------------------------------------------- loading

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_model_labels(key: str, main_file: str, register_file: str | None,
                      hashes: dict[str, str]) -> dict[tuple[str, str], bool]:
    """{(cluster, condition): absorbed} with manual adjudications applied."""
    labels: dict[tuple[str, str], bool] = {}
    adjudicated = set(MANUAL_ADJUDICATIONS.get(key, []))
    verdict_file = HANDREAD_VERDICTS.get(key)
    if verdict_file:
        path = RESULTS / verdict_file
        hashes[verdict_file] = sha256_file(path)
        for line in path.open():
            row = json.loads(line)
            if row["verdict"] == "false_positive":
                adjudicated.add(row["case_id"])
    panel_path = RESULTS / PANEL_EXTENSION_VERDICTS
    hashes[PANEL_EXTENSION_VERDICTS] = sha256_file(panel_path)
    for line in panel_path.open():
        row = json.loads(line)
        if row.get("model") == key and row["verdict"] == "flip":
            adjudicated.add(row["case_id"])
    if key == "olmo2-32b":
        path = RESULTS / OLMO_VERDICTS
        hashes[OLMO_VERDICTS] = sha256_file(path)
        for line in path.open():
            row = json.loads(line)
            if row["verdict"] == "flip":
                adjudicated.add(row["case_id"])
    if key == "gemini-3.1-pro":
        path = RESULTS / GEMINI_VERDICTS
        hashes[GEMINI_VERDICTS] = sha256_file(path)
        for line in path.open():
            row = json.loads(line)
            if row["verdict"] == "flip":
                adjudicated.add(row["case_id"])
    unusable = UNUSABLE_CASE_IDS.get(key, set())
    for fname in filter(None, [main_file, register_file]):
        path = RESULTS / fname
        hashes[fname] = sha256_file(path)
        for line in path.open():
            row = json.loads(line)
            if row.get("clean_missing") or row["case_id"] in unusable:
                continue
            absorbed = row["absorbed"]
            if absorbed and row["case_id"] in adjudicated and (
                    row["condition"] in ADJUDICATION_APPLIED_CONDITIONS or key == "olmo2-32b"):
                absorbed = False
            labels[(row["composition_event_id"], row["condition"])] = absorbed
    return labels


def condition_counts(labels: dict, condition: str) -> tuple[int, int]:
    hits = total = 0
    for (_, cond), absorbed in labels.items():
        if cond == condition:
            total += 1
            hits += absorbed
    return hits, total


def paired_table(labels_a: dict, labels_b: dict, cond_a: str, cond_b: str) -> tuple[int, int, int, int]:
    """(e11, e10, e01, e00) over clusters present in both conditions."""
    e11 = e10 = e01 = e00 = 0
    clusters_a = {c for (c, cond) in labels_a if cond == cond_a}
    clusters_b = {c for (c, cond) in labels_b if cond == cond_b}
    for cluster in clusters_a & clusters_b:
        a = labels_a[(cluster, cond_a)]
        b = labels_b[(cluster, cond_b)]
        e11 += a and b
        e10 += a and not b
        e01 += b and not a
        e00 += not a and not b
    return e11, e10, e01, e00


def contrast_stats(labels_a: dict, labels_b: dict, cond_a: str, cond_b: str) -> dict | None:
    e11, e10, e01, e00 = paired_table(labels_a, labels_b, cond_a, cond_b)
    n = e11 + e10 + e01 + e00
    if n == 0:
        return None
    lo, hi = newcombe_paired_diff_ci(e11, e10, e01, e00)
    return {
        "n_pairs": n,
        "rate_a": round((e11 + e10) / n, 4),
        "rate_b": round((e11 + e01) / n, 4),
        "discordant_a_only": e10,
        "discordant_b_only": e01,
        "p_mcnemar_exact": exact_mcnemar(e10, e01),
        "diff_pp": round(100 * (e11 + e10 - e11 - e01) / n, 2),
        "diff_ci95_pp": [round(100 * lo, 2), round(100 * hi, 2)],
    }


def lever_bootstrap_ci(labels: dict, rng: random.Random) -> dict:
    """Cluster-bootstrap 95% percentile CI for newline AR / boundary AR."""
    clusters = sorted({c for (c, cond) in labels if cond == "newline" and (c, "boundary") in labels})
    pairs = [(labels[(c, "newline")], labels[(c, "boundary")]) for c in clusters]
    k_newline = sum(a for a, _ in pairs)
    k_boundary = sum(b for _, b in pairs)
    point = (k_newline / k_boundary) if k_boundary else math.inf
    ratios = []
    n = len(pairs)
    for _ in range(BOOTSTRAP_RESAMPLES):
        kn = kb = 0
        for _ in range(n):
            a, b = pairs[rng.randrange(n)]
            kn += a
            kb += b
        ratios.append(kn / kb if kb else math.inf)
    ratios.sort()
    lo = ratios[int(0.025 * BOOTSTRAP_RESAMPLES)]
    hi = ratios[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    fmt = lambda r: None if math.isinf(r) else round(r, 2)  # noqa: E731
    return {
        "point": fmt(point),
        "ci95": [fmt(lo), fmt(hi)],
        "unbounded_upper": math.isinf(hi) or math.isinf(point),
        "n_clusters": n,
        "events": [k_newline, k_boundary],
    }


# -------------------------------------------------------------------- report

def build_payload() -> dict:
    hashes: dict[str, str] = {}
    labels_by_model = {
        key: load_model_labels(key, main, reg, hashes)
        for key, _, main, reg in MODELS
    }
    paper_names = {key: name for key, name, _, _ in MODELS}
    rng_boot = random.Random(SEED)
    rng_perm = random.Random(SEED)

    # 1. Wilson CIs per model x condition.
    rates: dict[str, dict[str, dict]] = {}
    for key, labels in labels_by_model.items():
        rates[key] = {}
        for cond in CONDITIONS:
            k, n = condition_counts(labels, cond)
            if n == 0:
                continue
            lo, hi = wilson_ci(k, n)
            cell = {
                "k": k, "n": n, "rate_pct": round(100 * k / n, 1),
                "wilson_ci95_pct": [round(100 * lo, 2), round(100 * hi, 2)],
            }
            if k == 0:
                cell["exact_upper_pct"] = round(100 * exact_zero_upper(n), 2)
            rates[key][cond] = cell

    # 2. Full within-model contrast table with difference CIs.
    contrasts: dict[str, dict[str, dict]] = {}
    for key, labels in labels_by_model.items():
        contrasts[key] = {}
        for cond_a, cond_b in CONTRASTS:
            stats = contrast_stats(labels, labels, cond_a, cond_b)
            if stats is not None:
                contrasts[key][f"{cond_a}_vs_{cond_b}"] = stats

    # 3. Holm correction per contrast family across the panel.
    holm_families: dict[str, dict[str, dict]] = {}
    for cond_a, cond_b in CONTRASTS:
        name = f"{cond_a}_vs_{cond_b}"
        keys = [key for key, _, _, _ in MODELS if name in contrasts[key]]
        raw = [contrasts[key][name]["p_mcnemar_exact"] for key in keys]
        adj = holm(raw)
        holm_families[name] = {
            key: {"p_raw": raw[i], "p_holm": adj[i], "significant_holm_05": adj[i] < 0.05}
            for i, key in enumerate(keys)
        }

    # 4. Lever ratio bootstrap CIs.
    levers = {key: lever_bootstrap_ci(labels_by_model[key], rng_boot)
              for key, _, _, _ in MODELS}

    # 5. Genre gradient at cluster level (pooled newline+blank, any absorption).
    genre: dict[str, dict] = {}
    for key in GENRE_MODELS:
        labels = labels_by_model[key]
        per_source: dict[str, dict] = {}
        cluster_hits: dict[str, list[bool]] = {}
        for (cluster, cond), absorbed in labels.items():
            if cond in ("newline", "blank"):
                cluster_hits.setdefault(cluster, []).append(absorbed)
        by_source: dict[str, list[bool]] = {}
        for cluster, hits in cluster_hits.items():
            by_source.setdefault(cluster.split(":")[0], []).append(any(hits))
        for source in GENRE_ORDER:
            flags = by_source.get(source, [])
            k, n = sum(flags), len(flags)
            lo, hi = wilson_ci(k, n)
            per_source[source] = {
                "clusters_absorbed": k, "n_clusters": n,
                "rate_pct": round(100 * k / n, 1) if n else None,
                "wilson_ci95_pct": [round(100 * lo, 2), round(100 * hi, 2)],
            }
        adjacent = {}
        for s1, s2 in zip(GENRE_ORDER, GENRE_ORDER[1:]):
            a, b = per_source[s1], per_source[s2]
            p = fisher_exact(a["clusters_absorbed"], a["n_clusters"],
                             b["clusters_absorbed"], b["n_clusters"])
            adjacent[f"{s1}_vs_{s2}"] = float(f"{p:.3g}")
        genre[key] = {"per_source": per_source, "adjacent_fisher_p": adjacent}

    # 6. Between-model cluster-paired tests.
    between: dict[str, dict] = {}
    for key_a, key_b, conds in BETWEEN_MODEL_TESTS:
        for cond in conds:
            stats = contrast_stats(labels_by_model[key_a], labels_by_model[key_b], cond, cond)
            if stats is not None:
                between[f"{key_a}_vs_{key_b}:{cond}"] = stats

    # 7. Panel-level Spearman correlations.
    panel_keys = [key for key, _, _, _ in MODELS]
    newline_rates = [rates[key]["newline"]["rate_pct"] for key in panel_keys]
    blank_rates = [rates[key]["blank"]["rate_pct"] for key in panel_keys]
    lever_points = [levers[key]["point"] for key in panel_keys]
    rho_wb, p_wb = spearman(newline_rates, blank_rates, rng_perm)
    rho_lv, p_lv = spearman(newline_rates, lever_points, rng_perm)
    correlations = {
        "newline_vs_blank": {"rho": round(rho_wb, 3), "p_perm": round(p_wb, 5), "n": len(panel_keys)},
        "newline_vs_lever": {"rho": round(rho_lv, 3), "p_perm": round(p_lv, 5), "n": len(panel_keys)},
    }

    # Sensitivity: Opus boundary with the 2 documented scorer residuals removed.
    opus = labels_by_model["claude-opus-4-8"]
    k_ob, n_ob = condition_counts(opus, "boundary")
    lo, hi = wilson_ci(k_ob - 2, n_ob)
    sensitivity = {
        "opus_boundary_residual_adjusted": {
            "k": k_ob - 2, "n": n_ob, "rate_pct": round(100 * (k_ob - 2) / n_ob, 1),
            "wilson_ci95_pct": [round(100 * lo, 2), round(100 * hi, 2)],
            "note": "2 documented scorer residuals removed (Appendix cascade); "
                    "main tables keep the raw 2.0% per the paper.",
        },
    }

    return {
        "script": "seam/statistics.py",
        "seed": SEED,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "permutations": PERMUTATIONS,
        "input_sha256": dict(sorted(hashes.items())),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "paper_names": paper_names,
        "rates_with_wilson_ci": rates,
        "within_model_contrasts": contrasts,
        "holm_by_family": holm_families,
        "lever_ratio_bootstrap": levers,
        "genre_cluster_level": genre,
        "between_model_paired": between,
        "panel_correlations": correlations,
        "sensitivity": sensitivity,
    }


def fmt_p(p: float) -> str:
    if p >= 0.001:
        return f"{p:.3f}".rstrip("0").rstrip(".")
    return f"{p:.1e}"


def render_markdown(payload: dict) -> str:
    names = payload["paper_names"]
    lines = [
        "# SEAM statistics: CIs and exact tests",
        "",
        "Generated deterministically by `seam/statistics.py` (seed "
        f"{payload['seed']}) from the canonical cascade-full labels; input "
        "SHA-256 hashes are in `research/statistics.json`. Register rates "
        "apply the SCORES.md acted-on adjudications (Table 5 convention).",
        "",
        "## Absorption rates with Wilson 95% CIs (Table 2 / Fig 2)",
        "",
        "| model | newline | blank | boundary | mitigation |",
        "|---|---|---|---|---|",
    ]
    for key in names:
        cells = []
        for cond in CONDITIONS[:4]:
            cell = payload["rates_with_wilson_ci"][key].get(cond)
            if cell is None:
                cells.append("--")
                continue
            lo, hi = cell["wilson_ci95_pct"]
            text = f"{cell['rate_pct']} [{lo}, {hi}]"
            if "exact_upper_pct" in cell:
                text += f" (exact ub {cell['exact_upper_pct']})"
            cells.append(text)
        lines.append(f"| {names[key]} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Zero cells additionally report the exact Clopper-Pearson 95% upper "
        "bound: 'observed zero' means absorption below ~1.3% at n=300.",
        "",
        "## Within-model contrasts: exact McNemar + Newcombe 95% CI on the difference",
        "",
        "| model | contrast | AR_a/AR_b | a/b only | diff pp [95% CI] | p | p (Holm) |",
        "|---|---|---|---|---|---|---|",
    ]
    for key in names:
        for cname, stats in payload["within_model_contrasts"][key].items():
            holm_cell = payload["holm_by_family"].get(cname, {}).get(key)
            holm_text = fmt_p(holm_cell["p_holm"]) if holm_cell else "--"
            lo, hi = stats["diff_ci95_pp"]
            lines.append(
                f"| {names[key]} | {cname.replace('_vs_', ' vs ')} "
                f"| {stats['rate_a']:.3f}/{stats['rate_b']:.3f} "
                f"| {stats['discordant_a_only']}/{stats['discordant_b_only']} "
                f"| {stats['diff_pp']:+.1f} [{lo:+.1f}, {hi:+.1f}] "
                f"| {fmt_p(stats['p_mcnemar_exact'])} | {holm_text} |"
            )
    lines += [
        "",
        "The newline-vs-blank rows are the bounded nulls: the CI gives the "
        "largest whitespace effect the data allow. Negative diff means the "
        "second condition absorbs more.",
        "",
        "## Lever ratio (newline AR / boundary AR), cluster bootstrap 95% CI",
        "",
        "| model | lever | 95% CI | events (newline/boundary) |",
        "|---|---|---|---|",
    ]
    for key in names:
        lever = payload["lever_ratio_bootstrap"][key]
        point = lever["point"] if lever["point"] is not None else "inf"
        lo, hi = lever["ci95"]
        hi_text = "inf" if hi is None else hi
        lo_text = "inf" if lo is None else lo
        events = lever["events"]
        lines.append(f"| {names[key]} | {point} | [{lo_text}, {hi_text}] | {events[0]}/{events[1]} |")
    lines += [
        "",
        "Ratios with single-digit boundary event counts have very wide or "
        "unbounded upper CIs; cite the discordant counts, not the ratio "
        "magnitude, where the CI is unbounded.",
        "",
        "## Genre gradient at cluster level (pooled newline+blank, any absorption)",
        "",
        "| model | " + " | ".join(GENRE_ORDER) + " |",
        "|---|" + "---|" * len(GENRE_ORDER),
    ]
    for key in GENRE_MODELS:
        per_source = payload["genre_cluster_level"][key]["per_source"]
        cells = []
        for source in GENRE_ORDER:
            cell = per_source[source]
            lo, hi = cell["wilson_ci95_pct"]
            cells.append(f"{cell['rate_pct']} [{lo}, {hi}]")
        lines.append(f"| {names[key]} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Rates are % of clusters (n=50 per source) absorbing in newline or "
        "blank; adjacent-source Fisher exact p-values are in the JSON.",
        "",
        "## Between-model cluster-paired contrasts",
        "",
        "| contrast | AR_a/AR_b | a/b only | diff pp [95% CI] | p |",
        "|---|---|---|---|---|",
    ]
    for cname, stats in payload["between_model_paired"].items():
        lo, hi = stats["diff_ci95_pp"]
        lines.append(
            f"| {cname} | {stats['rate_a']:.3f}/{stats['rate_b']:.3f} "
            f"| {stats['discordant_a_only']}/{stats['discordant_b_only']} "
            f"| {stats['diff_pp']:+.1f} [{lo:+.1f}, {hi:+.1f}] "
            f"| {fmt_p(stats['p_mcnemar_exact'])} |"
        )
    corr = payload["panel_correlations"]
    sens = payload["sensitivity"]["opus_boundary_residual_adjusted"]
    lines += [
        "",
        "## Panel correlations (Spearman, permutation p)",
        "",
        f"- newline vs blank rates across {len(names)} models: rho = "
        f"{corr['newline_vs_blank']['rho']}, p = {corr['newline_vs_blank']['p_perm']}",
        f"- newline rate vs lever ratio: rho = "
        f"{corr['newline_vs_lever']['rho']}, p = {corr['newline_vs_lever']['p_perm']}",
        "",
        "## Sensitivity",
        "",
        f"- Opus boundary, residual-adjusted: {sens['rate_pct']}% "
        f"[{sens['wilson_ci95_pct'][0]}, {sens['wilson_ci95_pct'][1]}] "
        f"({sens['k']}/{sens['n']}). " + sens["note"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    global RESULTS
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="recompute and diff against the committed statistics.json")
    parser.add_argument("--results-dir", type=Path, default=RESULTS,
                        help="directory holding the *.cascade-full.jsonl label files")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "research",
                        help="directory to read or write statistics.json and STATISTICS.md")
    args = parser.parse_args()

    RESULTS = args.results_dir

    payload = build_payload()
    body = json.dumps(payload, indent=1, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(body.encode()).hexdigest()

    json_path = args.out_dir / "statistics.json"
    md_path = args.out_dir / "STATISTICS.md"
    if args.check:
        committed = json.loads(json_path.read_text())
        committed.pop("payload_sha256", None)
        committed.pop("script_sha256", None)
        fresh = json.loads(body)
        fresh.pop("script_sha256", None)
        if committed == fresh:
            print(f"OK: {json_path} matches recomputation")
        else:
            raise SystemExit(f"MISMATCH: recomputed statistics differ from {json_path}")
        return

    json_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    md_path.write_text(render_markdown(payload))
    print(f"wrote {json_path} and {md_path}")
    print(f"payload sha256: {payload['payload_sha256']}")


if __name__ == "__main__":
    main()
