---
name: ata-reuniao
description: FUNDIDA em Gerar Ata (jornada 1). Não rode como skill separada. A ata assertiva (processamento + levantamento + registro factual) é o checkbox "1. Gerar Ata" no BriefBoard.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "2.0.0"
  framework: briefboard
  ordem: 2
  fundida_em: gerar-ata
  entrada: outputs/analise_texto/<stem>/{transcricao_processada,levantamento}.md
  saida: outputs/analise_texto/<stem>/ata.md
---

# Fundida em Gerar Ata

Esta skill **não** aparece mais no multiselect de skills do BriefBoard.

O fluxo canônico é:

1. Checkbox **1. Gerar Ata** na jornada 1
2. Internamente: `processamento` → `levantamento-reuniao` → ata assertiva
3. Prompt: `modulos/ata_maker/prompts/ata_reuniao.txt`
4. Saída: `outputs/analise_texto/<stem>/ata.md` + ata na sessão

Prioridade de conteúdo para o leitor: **decisões → pendências com dono/prazo → o que ficou em aberto → contexto mínimo**.

Se um agente Cursor/Claude ainda ativar esta skill por engano, redirecione para o
mesmo contrato do prompt `ata_reuniao.txt` e grave em `ata.md` — sem divergir do app.
