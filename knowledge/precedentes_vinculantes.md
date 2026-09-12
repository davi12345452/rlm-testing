# Overriding Norms: Constitutional Rulings and Transitional Rules

> **Why this file exists.** In Brazilian labour law the dispositive rule is frequently *not* the
> provision that best matches the wording of the question. It is a Supreme Court ruling, a
> commencement date, or a special statute that sits one hop away from the obvious text and shares
> almost no vocabulary with the facts of the case.
>
> This is the file a top-k retriever misses. Nothing here mentions "intervalo intrajornada",
> "gratificação de função" or "transporte fornecido pelo empregador" — the words a claimant uses.
> It is reachable only by **following a `Cross-refs` edge** from the provision that looks relevant.
>
> Abridged and paraphrased for benchmark use; not a legal source of truth.

---

## [Lei 13.467/2017 vigência] Commencement of the 2017 labour reform
**Status:** in force
**Cross-refs:** [CLT art. 71], [CLT art. 468], [CLT art. 58 §2º], [CLT art. 74 §2º], [Súmula 437 TST], [Súmula 372 TST], [Súmula 90 TST]

A Lei 13.467/2017 (Reforma Trabalhista) foi publicada em 14 de julho de 2017 e entrou em vigor em
**11 de novembro de 2017**, após o período de vacatio legis de 120 dias.

**Operative rule for this corpus.** As alterações de direito material aplicam-se aos **fatos
ocorridos a partir de 11/11/2017**. Contratos iniciados antes dessa data e ainda vigentes depois
dela devem ser analisados em **dois períodos distintos**: até 10/11/2017 aplica-se o regime anterior
(inclusive as súmulas então vigentes); de 11/11/2017 em diante aplica-se a nova redação legal.

> Whenever a case in this benchmark spans that date, the correct answer is almost always a
> **split**, not a single regime.

## [Lei 12.506/2011] Proportional notice period
**Status:** in force
**Cross-refs:** [CLT art. 487]

O aviso prévio será concedido na proporção de **trinta dias** aos empregados que contem até um ano de
serviço na mesma empresa, **acrescido de três dias por ano de serviço prestado na mesma empresa, até
o máximo de sessenta dias, perfazendo um total de até noventa dias**.

Exemplo de cálculo: 7 anos completos de casa → 30 + (3 × 7) = 51 dias. O acréscimo é devido apenas ao
empregado, não ao empregador que pede demissão.

## [CF art. 7º XXIX] Constitutional limitation period
**Status:** in force
**Cross-refs:** [CLT art. 11]

São direitos dos trabalhadores urbanos e rurais: ação, quanto aos créditos resultantes das relações
de trabalho, com prazo prescricional de **cinco anos** para os trabalhadores urbanos e rurais, **até
o limite de dois anos após a extinção do contrato de trabalho**.

## [STF ADI 5766] Legal aid and litigation costs in the labour courts
**Status:** binding, with general effect (*erga omnes*)
**Cross-refs:** [CLT art. 790-B], [CLT art. 791-A §4º]

O Supremo Tribunal Federal julgou parcialmente procedente a ação e declarou **inconstitucionais** os
dispositivos da Reforma Trabalhista que impunham ao beneficiário da justiça gratuita o pagamento de
**honorários periciais e de honorários advocatícios de sucumbência com os créditos obtidos no próprio
processo ou em outro processo**, bem como a exigência de custas para propositura de nova ação após
arquivamento.

**Operative rule.** O beneficiário da justiça gratuita que sucumbe — inclusive na pretensão objeto da
perícia — **não pode ter esses encargos descontados dos créditos que obteve na reclamação**. A
obrigação permanece sob condição suspensiva de exigibilidade e, quanto aos honorários periciais, o
encargo recai sobre a União na forma da regulamentação aplicável.

## [STF ADPF 323] Ultra-activity of collective agreements
**Status:** binding, with general effect
**Cross-refs:** [Súmula 277 TST], [CLT art. 611-A]

O Supremo Tribunal Federal declarou a **inconstitucionalidade da ultratividade** das normas de acordos
e convenções coletivas, fixando que as cláusulas normativas **não aderem definitivamente aos
contratos individuais** de trabalho.

**Operative rule.** Expirado o prazo de vigência do instrumento coletivo e não havendo novo acordo, a
cláusula normativa **deixa de produzir efeitos**, salvo se incorporada por outro fundamento jurídico
autônomo. [Súmula 277 TST] não pode ser aplicada como fundamento para manter a cláusula.

## [STF ADI 6050] Statutory bands for non-pecuniary damages
**Status:** binding, with general effect
**Cross-refs:** [CLT art. 223-G §1º]

O Supremo Tribunal Federal deu **interpretação conforme a Constituição** aos incisos do art. 223-G,
§ 1º, da CLT, fixando que os critérios de quantificação ali previstos constituem **parâmetros
orientativos** para a fixação da indenização por dano extrapatrimonial.

**Operative rule.** Os valores indicados **não funcionam como teto absoluto**. O juiz pode arbitrar
indenização superior ao limite do inciso aplicável, desde que o faça de forma fundamentada,
observados os princípios da razoabilidade, da proporcionalidade e da reparação integral, e
considerando a gravidade concreta do dano e a capacidade econômica do ofensor.

## [Princípio da primazia da realidade] Substance over form
**Status:** general principle, in force
**Cross-refs:** [CLT art. 3º], [CLT art. 442-B], [CLT art. 62]

No Direito do Trabalho, os fatos prevalecem sobre a forma documental. A denominação dada pelas partes
ao contrato, o enquadramento formal anotado em CTPS ou a assinatura de um contrato de prestação de
serviços autônomos **não afastam o vínculo de emprego** se, no plano dos fatos, estiverem presentes
pessoalidade, não eventualidade, onerosidade e subordinação.

O mesmo princípio governa o enquadramento no art. 62 da CLT: o que importa é a existência **real** de
controle de jornada, não a anotação formal ou a nomenclatura do cargo.
