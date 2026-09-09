# Data licenses

The benchmark reuses text from six public editing corpora. Each row keeps a
`license` field and the identifiers needed to trace it upstream. The
partitions below are packaged separately so that a permissive-only user never
has to take on ShareAlike or noncommercial terms.

## Permissive partition

`benchmark/seam_v4_permissive.jsonl` (1200 rows)

| source | license |
|---|---|
| CanItEdit | MIT |
| CoEdIT | Apache-2.0 |
| CommitPackFT | MIT dataset; item repository license retained |
| IteraTeR (Human-Doc) | Apache-2.0 |

## Restricted partitions

| file | source | license | consequence |
|---|---|---|---|
| `benchmark/restricted/seam_v4_cc-by-nc-sa.jsonl` | ParaRev | CC-BY-NC-SA-4.0 | noncommercial, ShareAlike |
| `benchmark/restricted/seam_v4_cc-by-sa.jsonl` | Stack Exchange | CC-BY-SA (version resolved from item revision date) | ShareAlike |

Public availability of a source text does not by itself grant redistribution
rights. Retrieval dates are not recorded for every item, and item-level URLs
are not retained consistently across all sources and conditions, so this
release is not a fully documented redistribution package. Check the upstream
terms before redistributing any partition.

## Wild-corpus material is not included

The occurrence analysis draws on WildChat and LMSYS-Chat-1M. Those messages
are third-party conversation content and are not redistributed here. `wild/`
carries only content hashes, the corpus name, and the human audit labels;
`code/wild/` carries the mining and judging code. Regenerate the mined pool
from the corpora under their own terms.
