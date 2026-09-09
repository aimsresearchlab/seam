# Public Dataset Survey for SEAM-bench v2

Status: active research draft. Last checkpoint: 2026-07-10 04:34 CDT.

## Evaluation criteria

Each source is assessed on:

1. **Authenticity** — naturally authored content or interaction.
2. **Seam provenance** — whether pasted and typed spans are known exactly.
3. **Edit utility** — whether a source/target revision or functional outcome
   exists independently of absorption.
4. **Licensing** — whether examples can be transformed and redistributed.
5. **Privacy** — PII, employer/client material, and takedown requirements.
6. **Diversity** — genre, register, author, topic, and interaction setting.
7. **Contamination risk** — likelihood that tested models trained on the source.

## Provisional source registry

| Source | Material | Provenance | License/access | Candidate role | Status |
|---|---|---|---|---|---|
| SWE-chat | Real Claude Code, Codex, Gemini CLI and other coding-agent sessions | Final turns; clipboard provenance not documented | Dataset files gated; repository code MIT; dataset license needs clarification | Mine natural prompt shapes and coding artifacts | Verify |
| Trace Commons | Opt-in raw agent traces | Native logs, but sampled Claude messages were flattened | CC BY 4.0 compilation; embedded code retains upstream licenses | Qualitative prompt donor | Shortlist |
| Claude Code Community Conversations | 114 contributed Claude Code sessions | Final turn structure, no documented clipboard event | MIT; automated redaction and contributor consent | Small qualitative donor | Shortlist |
| Opt-in Claude Code prompt history | Natural prompts with placeholders plus `pastedContents` maps | Direct paste provenance; some entries store only a content hash | Local private data; needs contributor consent, redaction, and explicit release grant | Primary natural seam collection | Strongest new route |
| Publicly committed Claude histories | Real prompt history, often including paste maps | Direct when content is retained | Usually accidental exposure; no research consent or dependable content license | Schema evidence only | Exclude from benchmark mining |
| WildChat | 529K cleaned real ChatGPT conversations | No clipboard provenance | ODC-BY | Prevalence audit and natural prompt tails | Shortlist |
| LMSYS-Chat-1M | 1M real conversations | No clipboard provenance | Consent documented; release terms require verification | Prevalence/prompt mining | Verify |
| NIRVANA | 77 student writing sessions with ChatGPT and event logs | Copy/paste timestamps and keystrokes; prompt-direction unclear | Public-release location/license unclear | Closest precedent; possible direct data | Contact authors |
| CoAuthor | 1,445 human–AI writing sessions | Keystroke-level provenance for composition and AI suggestions | Download available; data license needs verification | Collector/schema precedent | Verify |
| Inputlog collections | Writing-process event logs | Explicit copy/paste/move actions | Tool CC BY-NC-ND; individual corpora vary | Method precedent | Shortlist |
| Enron email corpus | Natural workplace email and threads | Artifact only | Publicly released; privacy and derivative-release review required | Email artifact donor | Verify carefully |
| EnronSR | Message IDs, human-reply IDs, and three smart-reply candidates | Thread/reply indices; full bodies require an Enron join | CC BY-NC-SA 4.0; Harvard Dataverse DOI 10.7910/DVN/RQBWAC | Email reply structure and controls | Shortlist |
| CEREC | 6,001 Enron threads / 36,448 messages | Natural message/thread order | Access and derivative terms need final review | Email-thread artifact donor | Verify |
| BC3 | 40 W3C threads with extractive/abstractive summaries and other annotations | Natural public-list thread structure | Redistribution terms need verification | Small curated validation subset | Verify |
| EmailSum | 2,549 Avocado threads with short/long summaries; also scripts for W3C threads | Natural thread structure; no paste event | Only summaries are openly released; Avocado source mail requires an LDC license | Utility references, not a released artifact donor | Conditional |
| Avocado email | Corporate email collection | Natural messages and threads | Restricted LDC license prohibits excerpt redistribution | Local-only comparison | Exclude from released set |
| OANC / MASC | Contemporary multi-genre text; MASC includes 78 email files / 27,642 email words, OANC includes 245 ICIC letters / 91,318 words | Artifact only, with genre/provenance metadata | OANC unrestricted for use/redistribution; current MASC site specifies CC BY 3.0 US | Safest email/letter artifact donor found | Strong shortlist |
| Public mailing lists | W3C, Debian, and Apache list archives | Natural public threads | Public readability is not a blanket redistribution license | Scenario mining only unless cleared | Hold |
| Stack Exchange network | Code, prose, correction, email-draft, and advice posts | Natural post/revision/comment structure; no clipboard event | Official dumps/API; CC BY-SA version depends on publication/revision date | Multi-genre artifact and task donor | Strong shortlist |
| SOTorrent | Reconstructed Stack Overflow post histories | Fine-grained code/text revision history | Scripts Apache 2.0; underlying content retains Stack Exchange CC BY-SA | Natural edit pairs and revision analysis | Strong shortlist |
| CoEdIT | 70,783 instruction/source/target edit examples | No paste provenance; strong edit targets | Apache 2.0 | Utility-reference donor | Shortlist |
| IteraTeR Human-Doc | 559 human document revision sequences | Revision provenance, no chat paste | Apache 2.0 | Scientific/long-document edit donor | Shortlist |
| JFLEG | 1,503 grammatical/fluency correction examples | Source and four human references | CC BY-NC-SA 4.0 | Small noncommercial GEC subset | Conditional |
| W&I+LOCNESS | Document-level learner and native writing corrections | Human correction annotations | Noncommercial research restrictions | GEC utility donor | Conditional |
| WikiIns | Wikipedia edits with natural-language edit instructions | Revision provenance | Repository lacks a clear license | Editing methodology only until clarified | Hold |
| ParaRev | 48K scientific paragraph revisions, 641 manually annotated | Before/after paragraph revisions | CC BY-NC-SA 4.0 | Long-form revision donor | Conditional |
| TETRA | Professionally edited ACL-paper text | Expert before/after edits | Cited repository currently unavailable (404) | Method precedent only | Hold |
| NewsEdits | 1.2M news articles / 4.6M versions | Natural version history | License and distribution pathway require review | Revision donor | Verify |

## Design implication already supported

No single public source currently supplies all three required facts:

1. realistic artifact content;
2. naturally composed paste-then-type prompts; and
3. exact clipboard provenance.

The likely v2 design is therefore hybrid:

- **Artifact donors:** appropriately licensed email, forum, code, and revision
  corpora.
- **Prompt-style donors:** public chat and coding-agent traces, used to derive
  scenario distributions and surface forms rather than benchmark labels.
- **Instrumented composition:** consenting participants compose prompts in a
  browser/editor that records `insertFromPaste`, the inserted range, cursor and
  selection state, later edits, and the final flattened message.
- **Opt-in native history:** consenting Claude Code users locally select and
  export prompt-history entries whose placeholder/content map preserves real
  paste boundaries. Entries with hash-only paste records remain metadata-only
  and cannot become reconstructable benchmark examples.
- **Controlled counterfactuals:** mechanical separator/register variants built
  from each natural composition without an LLM generator.

## Open questions

- Which sources allow redistribution of transformed excerpts, not merely local
  research use?
- Can Stack Exchange posts/comments provide code, prose, questions, and informal
  notes under a single auditable license?
- Can email data be sampled without retaining names, addresses, signatures, or
  legally sensitive content?
- Can correction corpora supply document-length artifacts rather than isolated
  learner sentences?
- Does NIRVANA record pasted spans inside ChatGPT prompts, or only ChatGPT text
  pasted into the essay editor?
- Can Codex paste ranges be retained in a research sidecar without changing the
  message seen by the model?
- How stable is Claude Code's undocumented `pastedContents` shape across
  versions, operating systems, multiple pastes, edits after paste, and external
  editor mode?

## License/provenance rules for the registry

“Available on the web” is not a release license. For every selected item the
benchmark manifest should record, separately:

- source collection and immutable item/revision identifier;
- canonical URL and retrieval date;
- original author attribution or pseudonymous author ID;
- content license and license version at that revision date;
- dataset-package license and extraction-code license;
- whether redistribution is allowed, requires share-alike, or is local-only;
- transformations, redactions, and reviewer decisions;
- takedown status and a content hash for reproducibility.

For Stack Exchange, attribution and the date-dependent CC BY-SA version are
item-level requirements. For Enron-derived sets, a dataset's license does not
automatically settle the privacy and provenance of every underlying message.

The release should be structured as a **collection**, not relicensed as one
uniform body of text. Creative Commons explains that a collection can contain
works under different CC licenses without changing the licenses on the
individual works. Adaptations are different: ShareAlike material must use the
same or a designated compatible license. Stack Exchange's older CC BY-SA 2.5
and 3.0 content can generally be adapted under a later BY-SA version, but the
benchmark still needs to preserve the actual revision-level source license and
attribution rather than silently claiming all inputs were originally 4.0.

GitHub requires another distinction. Its Terms allow public viewing and
GitHub-native forking, and contributions to a licensed repository are normally
licensed under that repository's license. But this is not a dependable blanket
grant for exporting every issue body or third-party comment into a new text
dataset. GitHub-issue benchmarks are strong task precedents; use their text in a
released SEAM set only after item-level license review or contributor consent.

## Ethical rule for native agent histories

Do not treat a committed history file as consent merely because GitHub code
search can find it. Native histories can include source code, client material,
credentials, paths, names, and personal prompts. SEAM should accept only a
local, contributor-initiated export with item-level preview and selection,
automated secret/PII screening, human confirmation, documented redactions, and
an explicit benchmark redistribution grant.

## Primary references

- Claude Code local-data documentation:
  https://code.claude.com/docs/en/claude-directory
- Trace Commons dataset and donation safeguards:
  https://huggingface.co/datasets/trace-commons/agent-traces
- SWE-chat dataset card: https://huggingface.co/datasets/SALT-NLP/SWE-chat
- WildChat dataset card: https://huggingface.co/datasets/allenai/WildChat
- CoAuthor: https://coauthor.stanford.edu/
- Inputlog: https://www.inputlog.net/overview/
- OANC/MASC: https://anc.org/data/oanc/ and https://anc.org/data/masc/
- EnronSR: https://doi.org/10.7910/DVN/RQBWAC
- Stack Exchange content licensing: https://stackoverflow.com/help/licensing
- Stack Exchange API attribution terms:
  https://stackoverflow.com/legal/api-terms-of-use
- SOTorrent scripts: https://github.com/sotorrent/db-scripts
- Creative Commons reuse/collection FAQ: https://creativecommons.org/faq/
- Creative Commons ShareAlike compatibility:
  https://creativecommons.org/compatible-licenses/
- GitHub Terms of Service:
  https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
- CoEdIT: https://huggingface.co/datasets/grammarly/coedit
- IteraTeR Human-Doc:
  https://huggingface.co/datasets/wanyu/IteraTeR_human_doc
- ParaRev: https://huggingface.co/datasets/taln-ls2n/pararev
