---
name: levantamento-reuniao
description: Levanta os 10 campos obrigatórios de uma reunião a partir da transcrição processada — objetivo, participantes, decisões, tarefas, responsáveis, prazos, pendências, próximos passos, riscos e informações citadas. Campo que a reunião não tratou fica declarado como não mencionado, nunca preenchido por dedução. Rode depois de `processamento` e antes de `ata-reuniao` e `pontos-de-acao`, que consomem este levantamento.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "2.0.0"
  framework: briefboard
  ordem: 2
  entrada: outputs/analise_texto/<stem>/transcricao_processada.{json,md}
  saida: outputs/analise_texto/<stem>/levantamento.{json,md}
---

Você lê a reunião inteira e preenche uma ficha de 10 campos. Nada além dela.

A ficha é o que as skills seguintes consomem: a ata formata a partir dela, o plano
de ação parte dela. Por isso ela precisa ser fiel, não bonita. Um campo vazio
declarado é um bom resultado — quem lê fica sabendo que a reunião não decidiu nada,
e esse costuma ser o achado mais útil do documento.

## Antes de começar

A transcrição processada é obrigatória:

```python
from modulos.ata_maker.processamento import exigir
proc = exigir(stem, texto_origem)
```

Se levantar `ProcessamentoAusente` ou `ProcessamentoDesatualizado`, rode a skill
`processamento` antes. **Não releia a transcrição bruta e não use a ata** — a ata é
resumo, e levantar a ficha a partir dela herda cortes que você não fez.

Trabalhe sobre `proc.texto_ancorado` (a reunião inteira, com falante e âncora) e
`proc.metadados` (data da reunião, usada em todo prazo).

## Os 10 campos

| Campo | O que registra |
|---|---|
| Objetivo da reunião | por que ela aconteceu |
| Participantes | quem estava presente e quem faltou |
| Decisões tomadas | tudo que foi definido |
| Tarefas combinadas | o que precisa ser feito depois |
| Responsáveis | quem ficou com cada tarefa |
| Prazos | datas ou períodos combinados |
| Pendências | assuntos que ficaram sem resposta |
| Próximos passos | o que acontece depois da reunião |
| Riscos ou problemas | bloqueios, dúvidas, dependências |
| Informações importantes | números, links, nomes, documentos citados |

## A regra que manda em tudo

**A skill nunca cria dado.** Campo que a reunião não tratou recebe o texto
`não mencionado na transcrição`.

Não escreva "a definir". Não deduza o objetivo a partir do título da gravação. Não
invente prazo porque a tarefa "claramente é urgente". Não promova uma frase de
efeito a decisão para a seção não ficar vazia.

Se a reunião inteira não decidiu nada, os 10 campos podem sair com 8 declarados
como não mencionados. Isso é um retrato correto, e é exatamente o que o usuário
precisa ver.

## Processo

### 1. Partir do esqueleto, nunca de um dicionário do zero

```python
from modulos.ata_maker.levantamento import (
    preencher_do_processamento, normalizar_levantamento,
    validar_levantamento, levantamento_para_markdown,
)

dados = preencher_do_processamento(proc.dados, nomes)
```

Passe `proc.dados`, **não** `proc.texto_ancorado`. O texto ancorado é para você
ler; ele já é um markdown formatado, e reprocessá-lo como se fosse transcrição
descarta todos os falantes que a skill `processamento` resolveu.

Isso já entrega dois campos apurados:

- **Participantes** — presentes (falantes atribuídos) e citados que nunca falaram.
- **Informações importantes** — números, links, e-mails, valores em reais,
  percentuais e documentos citados, cada um com âncora, trecho e contagem. Use
  essa lista em vez de reescrever números de memória: é a diferença entre
  "47 tickets" e um número parecido que ninguém disse.

### 2. Preencher os oito campos interpretativos

Percorra os turnos e classifique cada trecho relevante como **fato**, **opinião**,
**decisão**, **pendência** ou **intenção vaga**. Sem esse passo, intenção vira
decisão — é o erro mais comum em transcrição de português falado.

O critério de decisão é duplo: tem **objeto** (o quê) e tem **efeito** (a reunião
terminou com aquilo valendo).

| Fala | Classificação | Campo |
|---|---|---|
| "A gente precisa mudar a nossa forma de trabalho" | intenção vaga | Pendências |
| "Vou abrir os tickets hoje e mandar a lista" | tarefa | Tarefas combinadas |
| "Fica definido que o Rogério assume a conta" | decisão | Decisões tomadas |
| "Acho que o suporte tá devagar" | opinião | fora da ficha |

Ao preencher, campo a campo:

- **Objetivo** — só se alguém disser por que estão ali. Título da gravação não é
  objetivo declarado.
- **Responsáveis e Prazos** — saem das tarefas, mas vão listados também aqui.
  Tarefa sem dono: `[dono não definido]`. Sem prazo: `[prazo não definido]`.
- **Riscos** — sempre com contexto: o que é, sobre quem pesa, qual sinal apareceu
  na reunião. Nunca um risco solto.

Toda entrada de decisão, tarefa e pendência carrega âncora `[t=mm:ss]`. Sem trecho
que sustente, a linha não entra.

### 3. Resolver os prazos

Use o resolvedor, não a intuição:

```python
from modulos.ata_maker.acoes import resolver_prazo
resolver_prazo("até sexta", data_reuniao).texto   # '2026-07-17 (até sexta)'
```

Cobre "amanhã", "próxima sexta", "semana que vem", "em 3 dias", "fim do mês",
"dia 20 de agosto", "18/07". Expressões de pressão — *"o quanto antes"*,
*"urgente"* — não têm data e voltam como `[prazo não definido]`. Urgência não é
prazo: registre como prioridade e peça a data.

### 4. Fechar e validar

```python
dados = normalizar_levantamento(dados)      # vazio vira declarado
assert validar_levantamento(dados) == []    # nenhum campo sumiu
print(levantamento_para_markdown(dados))
```

`normalizar_levantamento` converte `[]`, `""` e `None` em
`não mencionado na transcrição` e descarta campo fora do schema.
`validar_levantamento` acusa campo ausente e vazio não declarado. Não entregue com
a validação falhando.

## Saída

Em `outputs/analise_texto/<stem>/`:

- **`levantamento.json`** — os 10 campos, todos presentes, validados.
- **`levantamento.md`** — os mesmos campos em Markdown, na ordem, inclusive os
  vazios. É o que `ata-reuniao` e `pontos-de-acao` consomem.

## Checkpoint

Reporte, curto:

- quantos dos 10 campos ficaram preenchidos e quantos como não mencionados
- quantas decisões, tarefas e pendências, e quantas sem dono ou sem prazo
- quantas menções objetivas foram capturadas
- o que precisa de confirmação humana antes das próximas skills rodarem

## Verificação

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.test_levantamento
```

Rode sempre que mexer em `modulos/ata_maker/levantamento.py`. Os testes travam a
regra central: um levantamento vazio precisa listar as 10 seções, todas declaradas.
