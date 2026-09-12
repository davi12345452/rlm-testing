# Benchmark report

Generated 2026-09-12T01:15:22+00:00 · 11 cases · 45 corpus sections · agent `gemini-3.8-flash` · judge `gemini-3.1-pro-preview` · **offline replay**

## Headline

| Agent | Rubric | Verdict acc. | Fully correct | Contradicts gold | Citation F1 | Retrieval recall | Tokens/case | Steps |
|---|---|---|---|---|---|---|---|---|
| RLM (recursive) | 0.95 | 1.00 | 11/11 | 0 | 0.95 | 0.95 | 18,357 | 7.5 |
| RAG (top-k) | 0.96 | 1.00 | 11/11 | 0 | 0.89 | 0.80 | 2,955 | 1.0 |
| Long context | 0.97 | 1.00 | 11/11 | 0 | 1.00 | 1.00 | 10,558 | 1.0 |
| Closed book (control) | 0.92 | 1.00 | 11/11 | 0 | 0.83 | 0.00 | 1,424 | 1.0 |

*Rubric* is the weighted fraction of gold reasoning steps the answer actually made. *Verdict acc.* scores the bottom line (correct 1.0, partially correct 0.5). *Contradicts gold* counts answers that reached the opposite conclusion — the failure that matters most in this domain and the one an average hides.

## By reasoning type

| Reasoning type | RLM (recursive) | RAG (top-k) | Long context | Closed book (control) |
|---|---|---|---|---|
| `constitutional_override` | 0.92 | 1.00 | 1.00 | 0.96 |
| `form_vs_substance` | 1.00 | 1.00 | 1.00 | 1.00 |
| `multi_hop_arithmetic` | 1.00 | 1.00 | 1.00 | 1.00 |
| `negative_control` | 1.00 | 1.00 | 1.00 | 0.88 |
| `polarity_trap` | 1.00 | 1.00 | 1.00 | 0.86 |
| `statute_over_precedent` | 1.00 | 1.00 | 1.00 | 1.00 |
| `temporal_override` | 0.75 | 0.75 | 0.75 | 0.75 |
| `temporal_split` | 1.00 | 0.81 | 0.94 | 1.00 |
| `threshold_conflict` | 1.00 | 1.00 | 1.00 | 0.78 |

## Citation behaviour

| Agent | Precision | Recall | Distractors cited | Citations outside corpus | Correct but ungrounded |
|---|---|---|---|---|---|
| RLM (recursive) | 0.97 | 0.95 | 0 | 0 | 1/11 |
| RAG (top-k) | 1.00 | 0.83 | 0 | 0 | 5/11 |
| Long context | 1.00 | 1.00 | 0 | 0 | 0/11 |
| Closed book (control) | 1.00 | 0.74 | 0 | 12 | 11/11 |

*Distractors cited* are the specific wrong provisions each case was built to bait, such as art. 482 (employee misconduct) in a constructive-dismissal claim. *Citations outside corpus* means two different things by arm: for a corpus-bound arm it is an ungrounded claim, while for the closed-book control it is usually real law that lies outside this curated excerpt — inspect them before calling either one a hallucination. *Correct but ungrounded* counts cases where the arm reached the right bottom line without ever having all the governing provisions in front of it: the right answer for reasons it could not have had, which is the failure an accuracy column cannot show.

## Per-case rubric scores

| Case | Type | RLM (recursive) | RAG (top-k) | Long context | Closed book (control) |
|---|---|---|---|---|---|
| `case_01_rescisao_indireta` | `polarity_trap` | 1.00 | 1.00 | 1.00 | 0.86 |
| `case_02_intervalo_intrajornada` | `temporal_override` | 0.75 | 0.75 | 0.75 | 0.75 |
| `case_03_horas_in_itinere` | `temporal_split` | 1.00 | 0.81 | 0.94 | 1.00 |
| `case_04_gratificacao_funcao` | `statute_over_precedent` | 1.00 | 1.00 | 1.00 | 1.00 |
| `case_05_registro_ponto` | `threshold_conflict` | 1.00 | 1.00 | 1.00 | 0.78 |
| `case_06_honorarios_periciais` | `constitutional_override` | 1.00 | 1.00 | 1.00 | 1.00 |
| `case_07_teletrabalho_controle` | `form_vs_substance` | 1.00 | 1.00 | 1.00 | 1.00 |
| `case_08_dano_extrapatrimonial` | `constitutional_override` | 1.00 | 1.00 | 1.00 | 0.89 |
| `case_09_ultratividade` | `constitutional_override` | 0.75 | 1.00 | 1.00 | 1.00 |
| `case_10_sobreaviso` | `negative_control` | 1.00 | 1.00 | 1.00 | 0.88 |
| `case_11_prescricao_aviso_previo` | `multi_hop_arithmetic` | 1.00 | 1.00 | 1.00 | 1.00 |

⚠ marks an answer whose bottom line contradicts the reference answer.

## Cost

- **RLM (recursive)**: 201,931 tokens total, 18,357 per case, 0.0s per case
- **RAG (top-k)**: 32,506 tokens total, 2,955 per case, 0.4s per case
- **Long context**: 116,142 tokens total, 10,558 per case, 0.0s per case
- **Closed book (control)**: 15,664 tokens total, 1,424 per case, 0.0s per case
- **Judge**: 72,253 tokens over all gradings

Token counts include reasoning ('thinking') tokens, which reasoning models bill as output and which benchmarks routinely omit. A recursive agent that takes twelve turns pays for its transcript on every turn; that is the price of the accuracy it buys, and it is stated here rather than hidden.
