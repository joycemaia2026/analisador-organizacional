---
name: processamento
description: INFRAESTRUTURA do BriefBoard (sempre automática, oculta na UI). Transforma a transcrição bruta de ASR na transcrição processada — turnos, âncoras, correção de nomes e falantes — e grava o artefato canônico que Gerar Ata e as demais skills consomem. Não selecione no app; o runner chama `modulos/ata_maker/processamento.py` antes de qualquer etapa.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "2.0.0"
  framework: briefboard
  ordem: 0
  obrigatoria: true
  infra: true
  entrada: transcrições/*.txt (ASR bruto)
  saida: outputs/analise_texto/<stem>/transcricao_processada.{json,md}
---

# Infraestrutura do BriefBoard (não é skill de UI)

No app Streamlit esta etapa **não aparece** no multiselect. Roda sempre, em
silêncio, via código:

```python
from modulos.ata_maker.processamento import processar, salvar, exigir
```

Contrato do artefato (inalterado):

- `outputs/analise_texto/<stem>/transcricao_processada.json`
- `outputs/analise_texto/<stem>/transcricao_processada.md`

Quem consome chama `exigir(stem, texto_origem)` — se faltar ou o hash divergir,
o BriefBoard reprocessa automaticamente na próxima execução de Gerar Ata / Skills.

## Para agentes Cursor / Claude

Se estiver operando fora do Streamlit e o artefato não existir:

1. Levante nomes: `nomes_do_cadastro()` + nomes citados na reunião.
2. `dados = processar(texto, nomes, origem=...)`
3. `salvar(stem, dados)`

A parte determinística (segmentação, âncoras, sugestão de falante) está em
`normalizacao.py` e `processamento.py` — não reescreva em prosa.

## O que este passo NÃO faz

- Não gera ata (isso é **Gerar Ata**).
- Não aparece como opção para o usuário final.
- Não substitui levantamento, pontos de ação, decisões ou pauta.
