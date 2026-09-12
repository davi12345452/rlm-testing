# Methodology

This document records the design decisions behind the benchmark and, where a decision was changed
during development, why. A benchmark whose construction is not inspectable is an assertion.

## 1. The question

The nominal question was *"does a recursive language model beat RAG on a hyperlinked legal corpus?"*

The first complete run answered it: **no, not meaningfully.** All arms reached the correct bottom
line on 11/11 cases, with rubric scores inside 0.02 of each other. Publishing that as the headline
would have been true and useless.

The useful question turned out to be one level down: *given that all arms are near ceiling, what is
the ceiling made of?* That is what the closed-book control measures, and it is what reframed the
whole project.

## 2. Arms

Four architectures, identical instructions, identical output schema.

| Arm | Sees | Decides what to see |
|---|---|---|
| `closedbook` | nothing | — |
| `rag` | 6 retrieved chunks | before reasoning, by embedding similarity |
| `longcontext` | the whole corpus | — |
| `rlm` | what it navigates to | during reasoning, one observation at a time |

The two controls are not filler. `closedbook` establishes what pre-training already supplies;
`longcontext` establishes what perfect access supplies. Any claim about retrieval or recursion lives
in the space between them, and without both, the space is unbounded.

### Fairness constraints

- **One instruction set.** `LEGAL_GUIDANCE` in `src/agent_base.py` goes verbatim to all four arms. It
  describes practitioner reasoning — check validity status, check dates, prefer the later statute —
  and names no provision, no case and no answer. Giving the recursive agent extra guidance would have
  measured a prompt.
- **One output schema.** Scoring never parses prose, so verbosity cannot buy score.
- **A competent baseline.** RAG gets overlapping chunks sized to keep a provision together with its
  status metadata, `RETRIEVAL_DOCUMENT`/`RETRIEVAL_QUERY` task-typed embeddings, and MMR so the
  top-k is not five paraphrases of one passage. Beating a deliberately weak baseline measures
  nothing.
- **Status metadata is visible to every arm.** Each provision's validity appears in its text, so RAG
  can see "superseded" on a chunk it retrieved. The recursive agent's advantage has to come from
  traversal, not privileged information.

## 3. The corpus as a graph

45 provisions, 3 documents, 72 cross-reference edges. Sections are declared as:

```markdown
## [citation key] Title
**Status:** in force | superseded for facts on or after … | read down by …
**Cross-refs:** [other key], [other key]
```

Brazilian labour law after the 2017 reform is dense with provisions that are still printed but no
longer govern. That produces the property the benchmark needs: **the dispositive rule is often one
hop from the matching rule and shares none of its vocabulary.** `precedentes_vinculantes.md` contains
the rulings that decide five of the eleven cases and never uses the words a claimant would use.

Edges are validated on load. During development this check caught three dangling references
immediately — exactly the class of typo that would have silently removed the path under test and
produced a clean, wrong result.

## 4. Cases

Eleven cases, each labelled with the reasoning failure it induces (`polarity_trap`,
`temporal_split`, `threshold_conflict`, `constitutional_override`, `negative_control`, …). Reporting
by type rather than as one average is what makes a score diagnostic.

Gold answers carry:

- `required_citations` — the provisions that must be relied upon (recall denominator)
- `supporting_citations` — legitimate companions, neither rewarded nor penalised
- `distractor_citations` — the specific wrong provision the case baits, counted explicitly
- `rubric` — weighted claims the answer must make, graded item by item

`case_10` is a deliberate negative control: the correct answer is that nothing is owed. Benchmarks
made only of claims that succeed reward over-triggering.

## 5. Scoring

**Deterministic first.** Citation precision and recall are computed against canonical keys by an
order-insensitive token-set resolver. It accepts `art. 483 da CLT` for `CLT art. 483` and
`parágrafo 2º do art. 74 da CLT` for `CLT art. 74 §2º`, and refuses to guess: an ambiguous citation
resolves to nothing, and a paragraph marker can never collide with an article number (`§ 2º` ≠
`art. 2º`). Twenty-three offline tests pin this behaviour, including the refusals.

**Retrieval recall separately.** Whether the governing provisions ever reached the model's context is
measured independently of whether the answer was right. Collapsing them makes "the baseline lost"
unattributable; separating them produced the benchmark's second finding.

**Judge last, and constrained.** Grading uses a different, stronger model than the agents
(`gemini-3.1-pro-preview` vs `gemini-3.8-flash`) because models systematically prefer their own
outputs. Rubric item ids are compiled into the judge's response schema, so it must return a verdict
for every criterion and cannot invent one. It grades only what cannot be measured mechanically.

**Costs include thinking tokens.** Reasoning models bill them as output. A recursive agent re-sends
its transcript every turn, so omitting them would understate its cost by a large factor.

## 6. Two bugs worth recording

Both produced plausible-looking wrong results, which is the only kind worth documenting.

**Empty answers scored as reasoning failures.** The first RLM implementation used one schema for
every turn, with `action` required and `answer` optional. The model reliably emitted
`action: "finish"` with perfectly correct citations and no prose. Three cases scored 0.00 on the
rubric while their traces showed the agent had read exactly the right provisions. Headline: RLM 0.73
against RAG 0.96 — a clean, publishable, entirely false result.

The fix was structural rather than a prompt patch: **deciding to stop and writing the answer are
separate operations.** `finish` now ends investigation, and a dedicated composition call writes the
answer from the transcript under a schema where the answer is mandatory. The failure mode is gone by
construction. Corrected headline: 0.95 against 0.96.

**A metric whose name asserted more than it measured.** Citations that resolve to no corpus key were
first reported as "unresolvable citations — invented law". The closed-book arm produced twelve. They
were all real: `CF art. 5º, XXXVI`, `CPC art. 373, I`, `CLT art. 9º`, `OJ 83 SDI-1 TST`. Correct
Brazilian law that simply lies outside a curated excerpt. The metric was renamed to
`citations_outside_corpus` and the report now states that the number means different things for a
corpus-bound arm than for a closed-book one. Reading it as a hallucination count would have inverted
the conclusion — that arm's legal knowledge was *better* than the corpus, not worse.

## 7. Reproducibility

Every request is content-addressed by a hash of model, prompt, system instruction, schema and
sampling parameters, and cached to `cache/`. `--offline` turns a cache miss into a hard error, so a
replay either reproduces the published run exactly or fails loudly.

`python -m src.benchmark prune` replays the canonical run offline, records which entries it touched
and deletes the rest — so the committed cache is the evidence for the committed report and nothing
left over from development.

## 8. What this benchmark cannot tell you

- Whether recursion wins on corpora that exceed the context window. Not tested; that is the regime
  the architecture exists for, and 28 KB is not it.
- Whether the closed-book result generalises beyond well-known public law. It almost certainly does
  not — that is the point, and it is the reason to run the control on *your* corpus rather than
  assume either outcome.
- Whether these rankings hold across models. One family, one size. `RLM_AGENT_MODEL` makes the sweep
  a one-line change.
- Anything with statistical confidence. n = 11, single seed, single judge. Differences below roughly
  0.1 rubric points are noise and are not interpreted as findings.
