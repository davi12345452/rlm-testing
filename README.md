# Does retrieval actually help? A controlled RAG benchmark on Brazilian labour law

Four architectures answer the same eleven legal questions over the same corpus: a **recursive
language model** that navigates the corpus with tools, a **RAG baseline** with embeddings and MMR, a
**long-context** arm that reads everything, and a **closed-book control** that gets no corpus at all.

The closed-book control is the point.

```
| Architecture          | Rubric | Correct | Citation F1 | Retrieval recall | Tokens/case |
|-----------------------|--------|---------|-------------|------------------|-------------|
| RLM (recursive)       |  0.95  |  11/11  |    0.95     |       0.95       |   18,357    |
| RAG (top-k + MMR)     |  0.96  |  11/11  |    0.89     |       0.80       |    2,955    |
| Long context          |  0.97  |  11/11  |    1.00     |       1.00       |   10,558    |
| Closed book (control) |  0.92  |  11/11  |    0.83     |       0.00       |    1,424    |
```

**A model with no corpus, no retrieval and no tools answers every case correctly** — at 1,424
tokens per case, a seventh of what the long-context arm spends and a thirteenth of the recursive
agent's. On this benchmark, retrieval buys almost nothing in
accuracy. What it buys is *grounding* — and that turns out to be a different quantity, measured by a
different number, and the one that actually matters here.

Reproduce every figure above with no API key:

```bash
pip install -r requirements.txt
make replay
```

---

## Why this benchmark is built the way it is

Most published RAG comparisons are run on public, well-documented material — statutes, Wikipedia,
popular open-source docs. A frontier model has read all of it. So when architecture A scores 0.96 and
architecture B scores 0.92, the honest question is: **how much of either number came from the corpus
at all?**

Almost nobody runs the experiment that answers it. It costs eleven API calls.

Here it says: on this corpus, the model already knew. `gemini-3.8-flash` reproduces the 2017 labour
reform's commencement date, knows that `Súmula 437` was displaced by the new `art. 71 § 4º`, and
knows that the Supreme Court read down the damages bands in `art. 223-G`. The corpus is worth about
four rubric points on top of that.

That is not a reason to stop measuring. It is a reason to **measure something else**.

### What separates the architectures is grounding, not accuracy

| Architecture | Correct bottom line | …but never saw all the governing provisions |
|---|---|---|
| Long context | 11/11 | **0/11** |
| RLM (recursive) | 11/11 | **1/11** |
| RAG (top-k) | 11/11 | **5/11** |
| Closed book | 11/11 | 11/11 (by construction) |

In five of eleven cases the RAG arm reached the correct legal conclusion **without ever retrieving
the provisions that produce it**. The answer was right; the stated basis was incomplete; the gap was
filled from pre-training. An accuracy column scores that as a success. In a domain where the answer
must be *defensible*, it is closer to the opposite — a correct answer you cannot audit, produced by a
pipeline whose retrieval you now wrongly believe is working.

This is the failure mode the benchmark was rebuilt to expose, and it is invisible without measuring
retrieval recall separately from answer quality.

### Where recursion paid off, and where it did not

The recursive agent is the only corpus-bound arm that beat RAG on the cases built around a
legislative change (`temporal_split`: 1.00 vs 0.81), because it could *follow a cross-reference* from
the provision that matched the question to the commencement date that decided it. It carried near
perfect retrieval recall (0.95 vs 0.80) and near perfect grounding.

It paid **6× the tokens of RAG** to do so, and the long-context arm matched it for half the cost.

On a 28 KB corpus that is the expected result and it is reported as such: when everything fits in the
window, reading everything is hard to beat. Recursion is an answer to context that does *not* fit.
This benchmark does not reach that regime, so it does not claim to have tested it — the long-context
arm is included precisely so that the claim stays falsifiable.

---

## The corpus is a graph, and that is the experimental variable

`knowledge/` holds 45 provisions across 3 documents, connected by **72 cross-reference edges**:

```markdown
## [CLT art. 71] Intra-shift rest break
**Status:** in force; § 4º has post-reform wording since 11 Nov 2017
**Cross-refs:** [Súmula 437 TST], [Lei 13.467/2017 vigência]
```

Brazilian labour law is unusually well suited to this. The 2017 reform and a series of
constitutional rulings left the corpus full of provisions that are still *printed* but no longer
*govern*. The rule that decides a case is routinely one hop away from the rule that matches its
wording — and shares none of its vocabulary:

| A claimant asks about… | Top-k retrieves | What actually governs |
|---|---|---|
| an unpaid meal break | `Súmula 437` — pay the **whole** break | `art. 71 § 4º` — pay **only** what was suppressed |
| 12 years of a function bonus | `Súmula 372` — keep it (financial stability) | `art. 468 § 2º` — reverses that outright |
| expert fees under legal aid | `art. 790-B` — charge the loser | `STF ADI 5766` — struck that down |
| an expired collective clause | `Súmula 277` — it survives | `STF ADPF 323` — ultra-activity is unconstitutional |

Nothing in `precedentes_vinculantes.md` mentions "intervalo intrajornada" or "gratificação de
função". Embedding similarity cannot reach it from the facts. A `follow()` call can.

Every edge is validated on load — a dangling cross-reference raises rather than silently removing the
path the recursive agent is supposed to take.

## The eleven cases

Each case names the specific reasoning failure it is built to induce, so a score decomposes into
something diagnostic instead of a single average:

| Type | The trap |
|---|---|
| `polarity_trap` | facts about dismissal pull toward `art. 482` (employee misconduct) when `art. 483` (employer breach) governs |
| `temporal_override` | the semantically closest rule was superseded in 2017 |
| `temporal_split` | the contract straddles the reform; the answer is two regimes, not one |
| `statute_over_precedent` | a near-verbatim súmula match that a later statute reversed |
| `threshold_conflict` | 15 employees — between the súmula's ">10" and the statute's ">20" |
| `constitutional_override` | the provision reads clearly and was read down by the Supreme Court |
| `form_vs_substance` | the contract says "by output"; the logs say otherwise |
| `multi_hop_arithmetic` | four documents and two date computations, none of them in any single chunk |
| `negative_control` | the correct answer is that **nothing is owed** — catches over-triggering |

Gold answers carry required citations, acceptable supporting citations, and named **distractor
citations** — the specific wrong provision the case baits — so citing the trap is measured, not
inferred.

## Evaluation

Deterministic metrics first, a constrained judge second:

- **Citations are scored mechanically** against canonical keys. An order-insensitive resolver accepts
  `art. 483 da CLT` for `CLT art. 483` but refuses to guess: an ambiguous citation resolves to
  nothing, and `§ 2º` can never match `art. 2º`. Over-eager matching would inflate the one metric
  that has to be beyond doubt.
- **Retrieval recall is measured separately** from answer quality, so a failure is attributable:
  never saw the rule, or saw it and reasoned past it.
- **The judge is not the model under test.** Agents run on `gemini-3.8-flash`, grading on
  `gemini-3.1-pro-preview`. Self-grading introduces a well-documented self-preference bias and
  avoiding it is free.
- **The judge answers a fixed checklist.** Rubric item ids are baked into its response schema, so it
  cannot invent a criterion, skip one, or drift between cases.
- **Token accounting includes thinking tokens**, which reasoning models bill as output and which
  benchmarks routinely drop. A 12-turn agent re-pays for its transcript every turn; that cost is
  stated, not hidden.

All four arms receive **identical legal instructions** and return **one identical output schema**.
The instructions describe how a practitioner reasons — check validity, check dates, prefer the later
statute — and name no provision. Telling only the recursive agent to watch for superseded rules would
have measured a prompt instead of an architecture.

## Reproducibility

Every API response is content-addressed and committed to `cache/`. `make replay` re-runs the whole
benchmark offline, and a cache miss is a hard error rather than a silent API call — so the published
numbers cannot quietly drift from the published artefacts.

The cache is pruned to exactly the entries the published run depends on
(`python -m src.benchmark prune`), so what ships is the evidence for the report and nothing else.

```bash
make replay                                     # reproduce the committed numbers, no API key
make test                                       # 23 offline tests
make run                                        # run live (needs GEMINI_API_KEY)
python -m src.benchmark run --agents rag,closedbook
python -m src.benchmark inspect --case case_03 --agent rlm   # read a full agent trace
```

`inspect` prints every tool call an agent made, its observation, and the answer it composed — the
artefact that lets a reader audit a result instead of trusting a score.

## Layout

```
knowledge/    3 markdown documents, 45 cross-linked provisions
cases/        11 cases with gold answers, required/distractor citations and weighted rubrics
src/
  corpus.py           parses the corpus into a validated graph; citation resolution
  tools.py            the navigation environment: outline, grep, read, follow
  agent_rlm.py        recursive agent: depth-limited, budgeted, spawns sub-agents
  agent_rag.py        baseline: overlapping chunks, task-typed embeddings, MMR
  agent_longcontext.py  control: the whole corpus in one prompt
  agent_closedbook.py   control: no corpus at all
  evaluator.py        deterministic citation metrics + rubric-constrained LLM judge
  benchmark.py        CLI: run, replay, inspect, prune
results/latest/       the committed run: results.json + report.md
cache/                content-addressed API responses that make the run replayable
```

## Known limitations

Stated because a benchmark that hides these is not worth reading.

- **Eleven cases is a small n.** Differences under roughly 0.1 rubric points are noise. The
  closed-book result is large enough to survive that; the RLM-vs-RAG gap on `temporal_split` is one
  case and should be read as a signal to investigate, not a finding.
- **The corpus fits in context.** The regime recursion is designed for — corpora that do not fit —
  is not tested here. The long-context arm exists to make that limitation visible rather than
  rhetorical.
- **The corpus is curated and abridged.** Provisions are paraphrased for benchmark readability and
  the source files say so. This is not a legal source of truth and must never be cited as one.
- **Single judge, single seed.** No inter-judge agreement study, no repeated sampling. Deterministic
  metrics are reported alongside the judge specifically so the judge is not load-bearing on its own.
- **One model family.** Whether the closed-book result holds for smaller or non-Gemini models is
  untested; `RLM_AGENT_MODEL` exists to make that sweep easy.

## Prior work

The recursive framing follows the Recursive Language Model line of work — treating context as an
environment a model queries and decomposes, rather than a buffer it is handed. The contribution here
is not the architecture but the **control design**: closed-book and long-context arms that make it
possible to say what a retrieval result actually measures.

## Licence

MIT. The legal corpus is abridged and paraphrased for research use; cite
[planalto.gov.br](https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm) and
[tst.jus.br](https://www.tst.jus.br/sumulas), never this repository.
