# Benchmark schema

One JSON object per line. A *cluster* is one composition event: the same task
instruction and pasted artifact under six conditions.

| field | meaning |
|---|---|
| `composition_event_id` | cluster identifier; rows sharing it are matched |
| `condition` | `clean`, `newline`, `blank`, `boundary`, `mitigation`, `newline_R` |
| `task_instruction` | typed instruction before the simulated paste |
| `artifact` | source material designated as pasted |
| `afterthought` | typed text after the paste; `null` in `clean` |
| `forbidden_proposition` | meaning that must not enter the returned artifact |
| `witness_tokens` | distinctive afterthought substrings, verified absent from the artifact, reference, and instruction; `null` in `clean` |
| `segments` | typed and pasted origins with exact character offsets |
| `reference` | upstream reference edit, where the source provides one |
| `source` | upstream corpus |
| `license` | source licensing metadata |

`newline_R` is called **artifact-native** in the paper: the trailing comment is
rewritten to fit the genre of the pasted text.

Conditions are compared within a cluster against that cluster's `clean` output,
so a signal counts only when it is absent from the model's own unprompted
output. A cluster is dropped when its `clean` output is unusable.
