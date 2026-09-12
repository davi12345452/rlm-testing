# Consolidação das Leis do Trabalho (CLT) — Curated Excerpts

> **What this file is.** A hand-curated, abridged corpus of provisions from the Brazilian
> Consolidation of Labour Laws (Decreto-Lei 5.452/1943), selected because they are frequently
> dispositive in real labour claims *and* because several of them interact with — or were
> displaced by — the 2017 labour reform (Lei 13.467/2017) and later constitutional rulings.
>
> **What this file is not.** A legal source of truth. Wording is abridged and paraphrased for
> benchmark readability. Never cite this file in legal work; cite
> <https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm>.
>
> **Format contract.** Every retrievable unit is a `## [citation-key] Title` section, optionally
> followed by `**Status:**` and `**Cross-refs:**` metadata lines. The parser in `src/corpus.py`
> depends on this shape. `Cross-refs` are the edges an RLM can traverse and a similarity-based
> retriever cannot see.

---

## [CLT art. 2º] Employer, economic group and group liability
**Status:** in force (as amended by Lei 13.467/2017)
**Cross-refs:** [CLT art. 3º]

Considera-se empregador a empresa, individual ou coletiva, que, assumindo os riscos da atividade
econômica, admite, assalaria e dirige a prestação pessoal de serviços.

§ 2º Sempre que uma ou mais empresas, tendo, embora, cada uma delas personalidade jurídica própria,
estiverem sob a direção, controle ou administração de outra, ou ainda quando, mesmo guardando cada
uma sua autonomia, integrem grupo econômico, serão responsáveis solidariamente pelas obrigações
decorrentes da relação de emprego.

§ 3º Não caracteriza grupo econômico a mera identidade de sócios, sendo necessárias, para a
configuração do grupo, a demonstração do interesse integrado, a efetiva comunhão de interesses e a
atuação conjunta das empresas dele integrantes.

## [CLT art. 3º] Definition of employee
**Status:** in force
**Cross-refs:** [CLT art. 2º], [CLT art. 442-B]

Considera-se empregado toda pessoa física que prestar serviços de natureza não eventual a
empregador, sob a dependência deste e mediante salário. Os requisitos clássicos extraídos dos arts.
2º e 3º são: pessoalidade, não eventualidade, onerosidade e subordinação jurídica.

## [CLT art. 11] Limitation period (prescrição)
**Status:** in force
**Cross-refs:** [CF art. 7º XXIX]

A pretensão quanto a créditos resultantes das relações de trabalho prescreve em cinco anos para os
trabalhadores urbanos e rurais, até o limite de dois anos após a extinção do contrato de trabalho.

Na prática: ajuizada a ação dentro de dois anos do fim do contrato (prescrição bienal), só são
exigíveis as parcelas vencidas nos cinco anos anteriores ao ajuizamento (prescrição quinquenal).

## [CLT art. 58 §1º] Residual minutes at the time clock
**Status:** in force
**Cross-refs:** [Súmula 366 TST]

Não serão descontadas nem computadas como jornada extraordinária as variações de horário no registro
de ponto não excedentes de cinco minutos, observado o limite máximo de dez minutos diários.

## [CLT art. 58 §2º] Commuting time (horas in itinere) — post-reform wording
**Status:** in force since 11 Nov 2017 (Lei 13.467/2017). **Displaces** the prior case law for
contracts and periods after that date.
**Cross-refs:** [Súmula 90 TST], [Lei 13.467/2017 vigência]

O tempo despendido pelo empregado desde a sua residência até a efetiva ocupação do posto de trabalho
e para o seu retorno, caminhando ou por qualquer meio de transporte, inclusive o fornecido pelo
empregador, não será computado na jornada de trabalho, por não ser tempo à disposição do empregador.

> **Temporal note.** Before 11 Nov 2017 the opposite rule applied (old art. 58 §2º plus
> [Súmula 90 TST]): commuting on employer-provided transport to a site that was hard to reach or
> unserved by public transport *was* counted as working time. Contracts straddling that date must be
> split into two periods.

## [CLT art. 59] Overtime and hour-banking
**Status:** in force (as amended by Lei 13.467/2017)
**Cross-refs:** [Súmula 85 TST], [CLT art. 59-A]

A duração diária do trabalho poderá ser acrescida de horas extras, em número não excedente de duas,
por acordo individual, convenção coletiva ou acordo coletivo de trabalho.

§ 5º O banco de horas poderá ser pactuado por acordo individual escrito, desde que a compensação
ocorra no período máximo de seis meses.

§ 6º É lícito o regime de compensação de jornada estabelecido por acordo individual, tácito ou
escrito, para a compensação no mesmo mês.

## [CLT art. 59-A] The 12x36 shift
**Status:** in force since 11 Nov 2017
**Cross-refs:** [Súmula 444 TST], [CLT art. 59]

É facultado às partes, mediante acordo individual escrito, convenção coletiva ou acordo coletivo de
trabalho, estabelecer horário de trabalho de doze horas seguidas por trinta e seis horas
ininterruptas de descanso, observados ou indenizados os intervalos para repouso e alimentação.

## [CLT art. 62] Workers outside the working-hours regime
**Status:** in force (item III added by Lei 13.467/2017)
**Cross-refs:** [Súmula 428 TST], [CLT art. 74 §2º]

Não são abrangidos pelo regime de duração do trabalho previsto neste Capítulo:

I — os empregados que exercem atividade externa incompatível com a fixação de horário de trabalho,
devendo tal condição ser anotada na CTPS e no registro de empregados;

II — os gerentes, assim considerados os exercentes de cargos de gestão, aos quais se equiparam os
diretores e chefes de departamento ou filial;

III — os empregados em regime de teletrabalho que prestam serviço por produção ou tarefa.

Parágrafo único. O regime previsto no inciso II é aplicável desde que o valor da gratificação de
função, se houver, não seja inferior a quarenta por cento do salário efetivo.

> **Doctrinal note.** Enquadramento no art. 62 é excepcional e depende de prova da real
> incompatibilidade com o controle de jornada. Havendo controle efetivo — ainda que telemático — o
> enquadramento cai e as horas extras são devidas.

## [CLT art. 71] Intra-shift rest break
**Status:** in force; § 4º has post-reform wording since 11 Nov 2017
**Cross-refs:** [Súmula 437 TST], [Lei 13.467/2017 vigência]

Em qualquer trabalho contínuo cuja duração exceda de seis horas, é obrigatória a concessão de um
intervalo para repouso ou alimentação, o qual será, no mínimo, de uma hora. Não excedendo de seis
horas o trabalho, será obrigatório um intervalo de quinze minutos quando a duração ultrapassar
quatro horas.

§ 4º A não concessão ou a concessão parcial do intervalo intrajornada mínimo implica o pagamento, de
natureza indenizatória, **apenas do período suprimido**, com acréscimo de cinquenta por cento sobre
o valor da remuneração da hora normal de trabalho.

> **Temporal note.** For facts before 11 Nov 2017, [Súmula 437 TST] applied instead: the employer
> owed the **entire** break period, with salary nature and all consequent integrations.

## [CLT art. 74 §2º] Mandatory time records
**Status:** in force (threshold raised from 10 to 20 employees by Lei 13.467/2017)
**Cross-refs:** [Súmula 338 TST]

Para os estabelecimentos com mais de vinte trabalhadores será obrigatória a anotação da hora de
entrada e de saída, em registro manual, mecânico ou eletrônico.

> **Conflict note.** [Súmula 338 TST] still reads "mais de 10 empregados", reflecting the pre-reform
> threshold. An establishment with, say, 15 employees sits exactly in the gap between the two texts.

## [CLT art. 223-G §1º] Damages for non-pecuniary harm — statutory bands
**Status:** in force, but **read down** by the Supreme Court
**Cross-refs:** [STF ADI 6050]

Ao apreciar o pedido, o juízo considerará a natureza do bem jurídico tutelado e fixará a indenização
observando os seguintes parâmetros, calculados sobre o salário contratual do ofendido:

I — ofensa de natureza leve: até três vezes;
II — ofensa de natureza média: até cinco vezes;
III — ofensa de natureza grave: até vinte vezes;
IV — ofensa de natureza gravíssima: até cinquenta vezes.

> **Constitutional note.** See [STF ADI 6050]: these bands are **orienting parameters, not binding
> caps**. A judge may exceed them on reasoned grounds.

## [CLT art. 442-B] The contracted self-employed worker
**Status:** in force since 11 Nov 2017
**Cross-refs:** [CLT art. 3º]

A contratação do autônomo, cumpridas por este todas as formalidades legais, com ou sem exclusividade,
de forma contínua ou não, afasta a qualidade de empregado prevista no art. 3º desta Consolidação.

> **Doctrinal note.** O dispositivo não afasta o princípio da primazia da realidade: presentes os
> requisitos do art. 3º de fato, reconhece-se o vínculo, pois a forma não prevalece sobre os fatos.

## [CLT art. 468] Contract amendment and reversal from a position of trust
**Status:** in force; § 2º added by Lei 13.467/2017
**Cross-refs:** [Súmula 372 TST], [Lei 13.467/2017 vigência]

Nos contratos individuais de trabalho só é lícita a alteração das respectivas condições por mútuo
consentimento, e ainda assim desde que não resultem, direta ou indiretamente, prejuízos ao empregado.

§ 1º Não se considera alteração unilateral a determinação do empregador para que o respectivo
empregado reverta ao cargo efetivo, anteriormente ocupado, deixando o exercício de função de
confiança.

§ 2º **A reversão ao cargo efetivo não assegura ao empregado o direito à manutenção do pagamento da
gratificação correspondente**, que não será incorporada ao salário, independentemente do tempo de
exercício da respectiva função.

> **Conflict note.** § 2º is the statutory answer to [Súmula 372 TST]. For facts after 11 Nov 2017
> the statute governs; the súmula survives for earlier reversals.

## [CLT art. 477 §6º e §8º] Severance payment deadline and penalty
**Status:** in force
**Cross-refs:** [CLT art. 483]

§ 6º A entrega ao empregado de documentos que comprovem a comunicação da extinção contratual aos
órgãos competentes e o pagamento das verbas rescisórias deverão ser efetuados até dez dias contados
a partir do término do contrato.

§ 8º A inobservância do disposto no § 6º sujeitará o infrator à multa em favor do empregado, em valor
equivalente ao seu salário, salvo quando, comprovadamente, o trabalhador der causa à mora.

## [CLT art. 482] Just cause attributable to the employee
**Status:** in force
**Cross-refs:** [CLT art. 483]

Constituem justa causa para rescisão do contrato de trabalho pelo empregador: ato de improbidade;
incontinência de conduta ou mau procedimento; negociação habitual por conta própria; condenação
criminal transitada em julgado; desídia no desempenho das funções; embriaguez habitual ou em
serviço; violação de segredo da empresa; ato de indisciplina ou de insubordinação; abandono de
emprego; ato lesivo da honra ou da boa fama praticado no serviço; ofensas físicas; prática constante
de jogos de azar; perda da habilitação para o exercício da profissão.

> **Direction note.** Este artigo trata da falta do **empregado**. A falta grave do **empregador** é
> tratada em [CLT art. 483]. Confundi-los inverte o polo da rescisão.

## [CLT art. 483] Constructive dismissal (rescisão indireta)
**Status:** in force
**Cross-refs:** [Súmula 13 TST], [CLT art. 477 §6º e §8º], [CLT art. 482]

O empregado poderá considerar rescindido o contrato e pleitear a devida indenização quando:

a) forem exigidos serviços superiores às suas forças, defesos por lei, contrários aos bons costumes,
ou alheios ao contrato;
b) for tratado pelo empregador ou por seus superiores hierárquicos com rigor excessivo;
c) correr perigo manifesto de mal considerável;
d) **não cumprir o empregador as obrigações do contrato**;
e) praticar o empregador ou seus prepostos, contra ele ou pessoas de sua família, ato lesivo da honra
e boa fama;
f) o empregador ou seus prepostos ofenderem-no fisicamente, salvo em caso de legítima defesa;
g) o empregador reduzir o seu trabalho, sendo este por peça ou tarefa, de forma a afetar
sensivelmente a importância dos salários.

§ 3º Nas hipóteses das letras **d** e **g**, poderá o empregado pleitear a rescisão de seu contrato
de trabalho e o pagamento das respectivas indenizações, **permanecendo ou não no serviço até final
decisão do processo**.

## [CLT art. 487] Notice period (aviso prévio)
**Status:** in force; proportionality governed by Lei 12.506/2011
**Cross-refs:** [Lei 12.506/2011]

Não havendo prazo estipulado, a parte que, sem justo motivo, quiser rescindir o contrato deverá
avisar a outra da sua resolução com a antecedência mínima de trinta dias.

## [CLT art. 611-A] Collective bargaining prevailing over statute
**Status:** in force since 11 Nov 2017
**Cross-refs:** [CLT art. 611-B], [Súmula 277 TST]

A convenção coletiva e o acordo coletivo de trabalho têm prevalência sobre a lei quando dispuserem,
entre outros, sobre: pacto quanto à jornada, dentro dos limites constitucionais; banco de horas
anual; intervalo intrajornada, respeitado o limite mínimo de trinta minutos para jornadas superiores
a seis horas; teletrabalho; e enquadramento do grau de insalubridade.

## [CLT art. 611-B] Matters excluded from collective bargaining
**Status:** in force since 11 Nov 2017
**Cross-refs:** [CLT art. 611-A]

Constituem objeto ilícito de convenção ou acordo coletivo a supressão ou a redução de direitos como:
normas de saúde, higiene e segurança do trabalho; salário mínimo; FGTS; seguro-desemprego; e o
adicional de remuneração para as atividades penosas, insalubres ou perigosas.

## [CLT art. 790-B] Expert-witness fees and legal aid
**Status:** in force, but **partially unconstitutional**
**Cross-refs:** [STF ADI 5766], [CLT art. 791-A §4º]

A responsabilidade pelo pagamento dos honorários periciais é da parte sucumbente na pretensão objeto
da perícia, ainda que beneficiária da justiça gratuita.

§ 4º Somente no caso em que o beneficiário da justiça gratuita não tenha obtido em juízo créditos
capazes de suportar a despesa, a União responderá pelo encargo.

> **Constitutional note.** [STF ADI 5766] struck down the mechanism that charged these fees against
> credits won in the very same claim. See that entry before answering any legal-aid cost question.

## [CLT art. 791-A §4º] Loser-pays attorney fees against a legal-aid beneficiary
**Status:** in force, but **partially unconstitutional**
**Cross-refs:** [STF ADI 5766], [CLT art. 790-B]

Vencido o beneficiário da justiça gratuita, as obrigações decorrentes de sua sucumbência ficarão sob
condição suspensiva de exigibilidade. Os honorários de sucumbência são fixados entre cinco e quinze
por cento sobre o valor que resultar da liquidação da sentença.

## [CLT art. 818] Burden of proof
**Status:** in force (as amended by Lei 13.467/2017)
**Cross-refs:** [Súmula 212 TST], [Súmula 338 TST], [Súmula 460 TST]

O ônus da prova incumbe:
I — ao reclamante, quanto ao fato constitutivo de seu direito;
II — ao reclamado, quanto à existência de fato impeditivo, modificativo ou extintivo do direito do
reclamante.

§ 1º Nos casos previstos em lei ou diante de peculiaridades da causa relacionadas à impossibilidade
ou à excessiva dificuldade de cumprir o encargo, o juízo poderá atribuir o ônus da prova de modo
diverso (distribuição dinâmica), por decisão fundamentada e antes da abertura da instrução.
