---
name: proxima-reuniao
description: Monta a pauta da próxima reunião a partir do que ficou em aberto — perguntas sem resposta, assuntos adiados, materiais a preparar, quem precisa estar e a data combinada. Cada assunto vem com objetivo, condutor e tempo, e a pauta é conferida contra a duração da reunião. Use quando o pedido for "o que fica para a próxima", "montar a pauta", "convite da reunião" ou "o que ficou pendente".
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "1.0.0"
  framework: briefboard
  ordem: 4
  entrada: outputs/analise_texto/<stem>/{transcricao_processada,levantamento}.md
  saida: outputs/analise_texto/<stem>/proxima_reuniao.{json,md}
---

Você fecha o ciclo: pega o que a reunião deixou em aberto e transforma em pauta
que cabe no tempo.

O teste de uma boa pauta não é cobrir tudo. É que a reunião termine com aqueles
assuntos resolvidos. Nove itens em trinta minutos não é ambição — é a garantia de
que os quatro últimos vão ser empurrados de novo.

## Antes de começar

1. A transcrição processada é obrigatória:

```python
from modulos.ata_maker.processamento import exigir
proc = exigir(stem, texto_origem)
```

2. Leia `outputs/analise_texto/<stem>/levantamento.md` — campos **Pendências**,
   **Próximos passos** e **Riscos**. Se existirem, leia também
   `pontos_de_acao.md` (o que ficou sem dono) e `resumo_decisoes.md` (decisões sem
   critério registrado). São as quatro fontes de assunto para a próxima reunião.

3. Pegue a data da reunião em `proc.metadados["data_reuniao"]`.

## Processo

### 1. Levantar o que ficou em aberto

Quatro origens, e cada item declara a sua:

| Origem | O que é |
|---|---|
| `ORIGEM_PERGUNTA` | pergunta feita na reunião que ninguém respondeu |
| `ORIGEM_ADIADO` | assunto explicitamente empurrado ("isso a gente vê depois") |
| `ORIGEM_PENDENCIA` | pendência do levantamento que não virou ação com dono |
| `ORIGEM_SEM_CRITERIO` | decisão tomada sem porquê registrado, que precisa ser fechada |

Só entra o que tem âncora. Assunto que você acha que seria bom discutir, mas que
ninguém levantou, não vira pauta — no máximo uma sugestão marcada como tal.

### 2. Transformar em item com objetivo

Um assunto sem objetivo vira conversa aberta e consome a reunião inteira.

```python
from modulos.ata_maker.proxima_reuniao import ItemPauta, ORIGEM_ADIADO

ItemPauta(
    assunto="prazo da homologação dos fornecedores",
    objetivo="definir a data-limite com a Lindia e o fornecedor",
    dono="Lindia",
    minutos=10,
    origem=ORIGEM_ADIADO,
    ancora="[t=33:15]",
    material="planilha de homologações pendentes",
)
```

- **objetivo** — o que precisa *sair* do assunto: uma decisão, um número, um aceite.
  "Discutir o assunto X" não é objetivo.
- **dono** — quem conduz o item, não quem executa depois.
- **minutos** — realista. Decisão simples: 5–10. Assunto com divergência conhecida:
  15–20. Acima de 20, o assunto provavelmente precisa de preparação antes, não de
  mais tempo na reunião.
- **material** — o que precisa estar pronto **antes**. É o que evita a reunião
  virar coleta de dados.

### 3. Definir quem precisa estar

```python
from modulos.ata_maker.proxima_reuniao import sugerir_participantes

participantes = sugerir_participantes(
    donos_de_itens=[i.dono for i in itens],
    citados_ausentes=levantamento["participantes"]["citados_sem_falar"],
    presentes=levantamento["participantes"]["presentes"],
)
```

Dois níveis, e a diferença importa:

- **obrigatório** — dono de item da pauta. Sem essa pessoa, o assunto não anda e a
  reunião deveria ser remarcada.
- **sugerido** — quem foi citado na reunião anterior sem estar presente. É um sinal
  objetivo, não uma convocação: quem convoca decide.

Não encha a sala. Cada participante a mais reduz a chance de decidir.

### 4. Resolver a data

```python
from modulos.ata_maker.proxima_reuniao import resolver_data
resolver_data("semana que vem", data_reuniao)   # → 2026-07-22 (semana que vem)
```

Se ninguém combinou data, o resultado é `[data não combinada]` — e isso vira o
primeiro item de acompanhamento, não uma data que você escolheu.

### 5. Conferir se a pauta cabe

```python
from modulos.ata_maker.proxima_reuniao import relatorio_pauta
print(relatorio_pauta(itens, duracao_min=30))
```

Sinaliza pauta vazia, item sem objetivo, sem dono, sem tempo, e pauta estourada.

O teto útil é **80% da duração** — o resto é abertura, atraso e fechamento. Uma
pauta de 28 minutos numa reunião de 30 estoura, e isso é proposital: reunião cheia
até o último minuto atrasa a seguinte.

**Se estourou, corte assunto ou aumente a reunião.** Não reduza os tempos até a
conta fechar: isso só transfere o problema para o dia.

A duração padrão são 30 minutos. Se a reunião marcada for outra, passe
`duracao_min=` e diga na saída qual valor usou.

## Saída

Em `outputs/analise_texto/<stem>/`:

**`proxima_reuniao.json`** — `data`, `duracao_min`, `itens` (schema de
`ItemPauta.para_dict()`), `participantes`, `materiais`, `avisos`.

**`proxima_reuniao.md`**, nesta ordem:

```
## Perguntas em aberto        (com âncora e por que ficaram sem resposta)
## Assuntos adiados           (com o que motivou o adiamento)
## Pauta proposta             (pauta_para_markdown: data, participantes, tabela, materiais)
## Materiais a preparar       (o quê, quem, até quando)
## Onde a pauta aperta        (relatorio_pauta, em português)
```

A seção "Pauta proposta" é feita para ser colada no convite sem edição.

## Regras não-negociáveis

- Todo item carrega âncora do que o originou. Sem trecho, é sugestão sua e precisa
  vir marcada como sugestão.
- Data não combinada fica declarada. Nunca escolhida por você.
- Nunca invente nome, sistema, número ou data.
- Não transforme a pauta em lista de desejos: se a reunião deixou dois assuntos em
  aberto, a pauta tem dois itens.
- Voz Gedanken (`docs/voz-gedanken.md`): dado antes de adjetivo, voz ativa.

## Checkpoint

Reporte: quantos itens, o tempo somado contra a duração prevista, quem é obrigatório
na reunião, quais materiais precisam ficar prontos antes e se a data foi combinada.

## Verificação

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.test_decisoes_pauta
```
