---
name: resumo-decisoes
description: Registra o contexto da reunião, os temas discutidos e cada decisão com o critério que a sustentou, as alternativas descartadas e quem a defendeu. Sinaliza decisão tomada sem porquê registrado — especialmente as difíceis de desfazer. Use quando o pedido for "por que decidimos isso", "resumo das decisões", "o que ficou definido" ou ao preparar a revisão de uma escolha antiga; para o registro completo da reunião use `ata-reuniao`.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "1.0.0"
  framework: briefboard
  ordem: 1
  entrada: outputs/analise_texto/<stem>/{transcricao_processada,levantamento}.md
  saida: outputs/analise_texto/<stem>/resumo_decisoes.{json,md}
---

Você registra decisões **com o porquê**. Essa é a diferença entre esta skill e a ata.

Uma decisão sem critério registrado não pode ser revisitada. Seis meses depois
ninguém lembra por que a escolha foi feita, e a discussão recomeça do zero — com
as mesmas pessoas, os mesmos argumentos e nenhuma memória de que já aconteceu.
Registrar o critério é o que transforma uma ata em memória organizacional.

## Antes de começar

1. A transcrição processada é obrigatória:

```python
from modulos.ata_maker.processamento import exigir
proc = exigir(stem, texto_origem)
```

   Se levantar `ProcessamentoAusente` ou `ProcessamentoDesatualizado`, rode a skill
   `processamento` antes.

2. Leia `outputs/analise_texto/<stem>/levantamento.md`. O campo **Decisões tomadas**
   é o seu ponto de partida; você acrescenta o que ele não tem — critério,
   alternativas e reversibilidade. Se ele estiver como
   `não mencionado na transcrição`, a reunião não decidiu nada, e a sua saída diz
   exatamente isso.

## Processo

### 1. Contexto principal *(obrigatório)*

Uma a três frases: o que motivou a reunião e em que estado o assunto estava quando
ela começou. Sai da fala, não do título da gravação. Se ninguém disse por que
estavam ali, escreva `não mencionado na transcrição` — não deduza do assunto.
**Esta seção nunca fica em branco nem é omitida**, mesmo sem decisões.

### 2. Temas discutidos, ancorados no tempo *(obrigatório)*

Use as janelas de tempo para não inventar tema nem perder um:

```python
from modulos.ata_maker.normalizacao import blocos_de_tempo
from modulos.ata_maker.levantamento import turnos_do_artefato

blocos = blocos_de_tempo(turnos_do_artefato(proc.dados["turnos"]), minutos=10)
```

Cada bloco traz a janela (`0:00`–`10:00`), os turnos e os falantes. Percorra as
janelas e nomeie o tema de cada uma. Tema que ocupa três janelas é o assunto real
da reunião; tema que aparece em meia janela é menção de passagem — não os
apresente com o mesmo peso.

Para cada tema: o que era, onde parou, e a faixa de tempo. Sem recomendação aqui.
**Esta seção nunca fica em branco nem é omitida**, mesmo sem decisões.

### 3. Decisões, com o critério

Uma decisão precisa de **objeto** (o quê) e **efeito** (terminou valendo). Para
cada uma, monte:

```python
from modulos.ata_maker.decisoes import Decisao, IRREVERSIVEL, REVERSIVEL

Decisao(
    enunciado="priorizar os tickets por Pareto",
    criterio="resolver 3 ou 4 já mostra reação rápida ao cliente",
    alternativas_descartadas=["resolver na ordem de abertura"],
    sustentada_por="Gabriel Pereira",
    ancora="[t=2:40]",
    tipo=REVERSIVEL,
)
```

- **critério** — o porquê *dito na reunião*. Não construa uma justificativa
  razoável: se ninguém explicou, deixe o padrão `SEM_CRITERIO`. Essa lacuna é o
  achado mais valioso da skill.
- **alternativas_descartadas** — o que chegou a ser considerado e caiu. Só o que
  foi mencionado.
- **sustentada_por** — quem defendeu. Sem isso, `None`.
- **tipo** — `REVERSIVEL` se der para desfazer em uma semana sem custo relevante;
  `IRREVERSIVEL` se envolver contrato, demissão, migração ou comunicação externa
  já feita; `INDEFINIDO` se você não conseguir julgar pela transcrição.

### 4. Validar

```python
from modulos.ata_maker.decisoes import relatorio_decisoes, validar_decisoes
print(relatorio_decisoes(decisoes))
```

Reporta, por gravidade: decisão irreversível sem critério (alta), decisão sem
âncora (alta), decisão sem critério, sem responsável, e reversibilidade não
avaliada (baixa).

**Não "conserte" os avisos inventando conteúdo.** Eles vão para a saída como estão
— são o retrato do que a reunião não registrou, e servem para a próxima reunião
fechar a lacuna.

### 5. Critérios e justificativas que valem além da decisão

Nem todo critério pertence a uma decisão específica. Regras que a reunião declarou
("cliente pagante tem prioridade sobre trial", "nada entra na sprint sem estimativa")
valem para as próximas decisões e merecem seção própria, com âncora.

## Saída

Em `outputs/analise_texto/<stem>/`:

**`resumo_decisoes.json`** — `contexto`, `temas` (com faixa de tempo), `decisoes`
(schema de `Decisao.para_dict()`), `criterios_gerais`, `avisos`.

**`resumo_decisoes.md`**, nesta ordem:

```
## Contexto principal
## Temas discutidos          (com a faixa de tempo de cada um)
## Decisões tomadas          (decisoes_para_markdown: enunciado, critério, alternativas, natureza)
## Critérios e justificativas que valem além desta reunião
## O que não ficou registrado  (relatorio_decisoes, em português)
```

## Regras não-negociáveis

- **Contexto principal e Temas discutidos são obrigatórios** em toda saída,
  mesmo quando não houve decisão. Se a reunião não disse o motivo ou não nomeou
  temas, declare `não mencionado na transcrição` — nunca omita a seção nem
  deixe em branco.
- Toda decisão carrega âncora `[t=mm:ss]`. Sem trecho, não entra.
- Critério ausente fica declarado como ausente. Nunca reconstruído.
- Intenção vaga não é decisão: *"a gente precisa mudar a forma de trabalho"* não
  tem objeto nem efeito.
- Nunca invente nome, sistema, número ou data.
- Voz Gedanken (`docs/voz-gedanken.md`): dado antes de adjetivo, voz ativa.

## Checkpoint

Reporte: quantas decisões, quantas sem critério registrado, quantas irreversíveis,
e quais lacunas precisam virar pauta da próxima reunião — a skill `proxima-reuniao`
consome exatamente essas.

## Verificação

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.test_decisoes_pauta
```
