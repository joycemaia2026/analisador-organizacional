---
name: pontos-de-acao
description: Analisa o que cada participante da reunião pode de fato fazer — ações com dono, prazo em data absoluta, esforço estimado e dependências, checadas contra a capacidade real da semana. Separa o que foi combinado do que ninguém assumiu. Use quando o pedido for "o que fazer agora", "plano de ação", "quem faz o quê" ou "próximos passos"; para o registro da reunião use `ata-reuniao`.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "1.0.0"
  framework: briefboard
  ordem: 3
  entrada: outputs/analise_texto/<stem>/{transcricao_processada,levantamento}.md
  saida: outputs/analise_texto/<stem>/pontos_de_acao.{json,md}
---

Você monta o plano de ação que sai de uma reunião. O critério não é ambição: é o
que aquelas pessoas, com o tempo que têm, conseguem terminar.

Um plano com 14 ações "para esta semana" não é ambicioso — é um plano que não vai
acontecer, e todo mundo sabe disso na hora em que lê. Prefira 4 ações que terminam.

## Antes de começar

1. A transcrição processada é obrigatória:

```python
from modulos.ata_maker.processamento import exigir
proc = exigir(stem, texto_origem)
```

   Se levantar `ProcessamentoAusente` ou `ProcessamentoDesatualizado`, rode a skill
   `processamento` antes — sem âncora e sem falante não há como saber quem assumiu
   o quê. Trabalhe sobre `proc.texto_ancorado`, nunca sobre a ata: ela é resumo, e
   uma ação que ela cortou você nunca vai encontrar.

2. Leia `outputs/analise_texto/<stem>/levantamento.md`: os campos **Tarefas
   combinadas**, **Responsáveis** e **Prazos** são a base das suas ações explícitas.
   Partir dali evita divergir da ata sobre o que foi combinado. Se esses campos
   estiverem como `não mencionado na transcrição`, a reunião não combinou tarefa
   nenhuma — toda ação que você propuser é `inferida`, e precisa vir marcada assim.

3. Leia `perfis/perfis.json` para saber cargo e área de cada participante. É o que
   permite sugerir dono com base em papel, e não em quem falou por último.
4. Pegue a data da reunião em `metadados.data_reuniao` — todo prazo é calculado sobre ela.

## Processo

### 1. Levantar as ações

Duas origens, sempre separadas:

- **explícita** — alguém assumiu ou pediu na reunião. Tem âncora obrigatória.
- **inferida** — ninguém falou, mas sem isso o resto não anda. Marque como inferida
  e diga o que ela destrava. Nunca apresente inferência como se tivesse sido combinada.

Descarte o que não é ação: opinião, desabafo e diagnóstico não entram. O teste é
simples — se você não consegue escrever a frase começando com um verbo no
infinitivo e um objeto concreto, não é ação. *"Melhorar a comunicação"* reprova;
*"Definir um canal semanal de status com o cliente"* passa.

### 2. Atribuir dono

Ordem de preferência:

1. Quem assumiu na fala ("eu abro a lista hoje") — dono explícito.
2. Quem tem o papel, segundo `perfis/perfis.json` — dono **sugerido**, marcado como tal.
3. Nada disso → `[dono não definido]`.

Não distribua ação por proximidade no texto nem por quem falou mais. Uma ação sem
dono é um problema visível; uma ação com dono errado é um problema invisível.

### 3. Resolver o prazo

Use o resolvedor, não a intuição:

```python
from datetime import date
from modulos.ata_maker.acoes import resolver_prazo
resolver_prazo("até sexta", date(2026, 7, 15)).texto   # '2026-07-17 (até sexta)'
```

Ele cobre "amanhã", "próxima sexta", "semana que vem", "em 3 dias", "fim do mês",
"dia 20 de agosto", "18/07". Expressões de pressão — *"o quanto antes"*, *"urgente"*,
*"assim que der"* — **não têm data** e voltam como `[prazo não definido]`. Urgência
não é prazo; registre como prioridade alta e peça a data.

### 4. Estimar esforço

Em horas, faixa realista, incluindo o retrabalho que sempre acontece. Referência:

| Faixa | O que costuma ser |
|---|---|
| 1–2h | mandar um e-mail, marcar reunião, levantar uma lista |
| 4–8h | escrever um documento, mapear um processo, analisar tickets |
| 16–40h | mudar um processo, integrar um sistema, treinar um time |

Acima de 40h não é ação de reunião: é projeto. Quebre em partes ou registre como
"precisa de escopo próprio".

### 5. Checar o realismo por cálculo

Este é o passo que a skill existe para fazer, e ele não é opinião:

```python
from modulos.ata_maker.acoes import Acao, relatorio_realismo, validar_acoes
print(relatorio_realismo(acoes, data_reuniao))
```

Sinaliza seis coisas: ação sem dono, sem prazo, sem âncora; prazo anterior à
reunião; ação que vence antes daquela de que depende; e pessoa acumulando mais que
`CAPACIDADE_SEMANAL_H` (8h/semana por padrão) numa mesma semana.

**Corrija o plano até os avisos acabarem** — empurrando prazo, cortando escopo ou
trocando dono — ou registre o aviso que sobrou na seção "Onde o plano aperta". O
que não pode é entregar um plano com sobrecarga silenciosa.

A capacidade padrão são 8h por semana, não a jornada: é o que sobra depois da
operação do dia a dia numa startup. Se o time tiver folga real, passe
`capacidade_h=` e diga na saída qual valor você usou.

### 6. Sequenciar

Ordene por dependência, não por importância. Uma ação que destrava três outras vem
antes de uma ação importante e isolada. Deixe explícito o que pode começar hoje.

## Saída

Em `outputs/analise_texto/<stem>/`:

**`pontos_de_acao.json`** — lista de ações no schema de `Acao.para_dict()`:
`id`, `descricao`, `dono`, `origem`, `prazo`, `prazo_expressao`, `esforco_horas`,
`depende_de`, `ancora`. Mais `avisos` e `capacidade_h` usada.

**`pontos_de_acao.md`**, nesta ordem:

```
## Pode começar hoje          (ações sem dependência pendente)
## Plano por pessoa           (uma tabela por dono: Ação | Prazo | Esforço | Âncora)
## Depende de outra coisa     (com o que destrava cada uma)
## Ninguém assumiu            (ações inferidas e órfãs, com o que elas destravam)
## Onde o plano aperta        (saída de relatorio_realismo, em português)
## Fora de escopo por agora   (o que virou projeto, e por quê)
```

## Regras não-negociáveis

- Ação explícita sem âncora `[t=mm:ss]` não entra.
- Nunca invente nome, sistema, número ou data.
- Prazo sempre absoluto, com a expressão original entre parênteses.
- Não transforme opinião em ação para encher o plano. Reunião que gerou duas ações
  gera um plano de duas ações.
- Voz Gedanken (`docs/voz-gedanken.md`): dado antes de adjetivo, voz ativa, risco
  sempre com contexto.

## Checkpoint

Reporte: total de ações (explícitas × inferidas), quantas sem dono, quantas sem
prazo, quem ficou sobrecarregado e em qual semana, e o que precisa de decisão
humana antes de virar compromisso.

## Verificação

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.test_acoes
```

Rode sempre que mexer em `modulos/ata_maker/acoes.py`. Os testes travam a tabela de
prazos em pt-BR e as seis checagens de realismo.
