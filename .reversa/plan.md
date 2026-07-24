# Plano de Exploração — analisador-organizacional

> Criado pelo Reversa em 2026-07-17
> Marque cada tarefa com ✅ quando concluída.
> Documento de produto atual: `ESPECIFICACAO.md` (v1.3).

---

## Fase 1: Reconhecimento

- [ ] **Scout** — Mapeamento de estrutura de pastas e tecnologias
- [ ] **Scout** — Análise de dependências (`requirements.txt`, `rodar.sh`)
- [ ] **Scout** — Entry points (`app.py`), jornadas e módulos (`core/`, `modulos/`)

## Decisão de organização das specs

> Entre o Scout e o Arqueólogo, o Reversa pergunta como organizar as specs.
> Sugestão inicial para este projeto: **por features/jornadas** (ata, análise, comparativa, resumo, studio).

## Fase 2: Escavação

> Preenchida após o Scout com os módulos reais.

- [ ] **Archaeologist** — Análise do módulo `jornadas` (UI Streamlit)
- [ ] **Archaeologist** — Análise do módulo `core` (análise, perfis, export, resumo)
- [ ] **Archaeologist** — Análise do módulo `modulos/ata_maker`
- [ ] **Archaeologist** — Análise do módulo `modulos/notebooklm`

## Fase 3: Interpretação

- [ ] **Detective** — Regras de negócio implícitas e fluxos de sessão
- [ ] **Detective** — ADRs retroativos via Git (se histórico permitir)
- [ ] **Architect** — Diagramas C4 e mapa de integrações (OpenAI, NotebookLM)
- [ ] **Architect** — Spec Impact Matrix

## Fase 4: Geração

- [ ] **Writer** — Specs SDD por jornada/componente
- [ ] **Writer** — Code/Spec Matrix alinhada a `ESPECIFICACAO.md`

## Fase 5: Revisão

- [ ] **Reviewer** — Revisão cruzada de specs
- [ ] **Reviewer** — Lacunas e relatório de confiança

---

## Agentes independentes

- [ ] **Visor** — UI via screenshots (se disponíveis)
- [ ] **Data Master** — N/A (sem banco relacional; só `perfis.json` / arquivos)
- [ ] **Design System** — Tema Streamlit Gedanken (cores/tokens)

---

## Próximo passo após Discovery

- `/reversa-forward` ou `/reversa-migrate` conforme necessidade
- Manter `ESPECIFICACAO.md` como fonte de verdade de produto até as SDD estarem maduras
