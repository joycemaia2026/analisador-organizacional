# Especificação — BriefBoard - Gedanken

| Campo | Valor |
|-------|--------|
| Produto | BriefBoard - Gedanken |
| Marca | Gedanken |
| Nome na UI | BriefBoard |
| Slogan | Da ata à decisão — com a lente de quem lidera. |
| Versão do documento | 6 |
| Data | 2026-08-12 |
| Tipo | Especificação funcional e técnica |
| Repositório | https://github.com/joycemaia2026/analisador-organizacional |
| Pasta do projeto | `/home/joyce/projetos/briefboard` |

---

## 1. Visão geral

### 1.1 Objetivo

Aplicação web que apoia a **continuidade organizacional** após reuniões e decisões, conectando:

1. **Registro** — transformar transcrição em ata estruturada  
2. **Interpretação** — analisar o problema/atas sob o olhar de um ou mais Tomadores reais  
3. **Contraste** — confrontar a visão do Tomador com a de um Especialista Sênior em IA  
4. **Síntese** — consolidar ata + personas + Especialista em um resumo rastreável  
5. **Comunicação** — (opcional) exportar visualmente via NotebookLM ou PPTX/infográfico locais  

### 1.2 Problema que resolve

Reuniões geram informação dispersa; decisões e pendências se perdem; perfis de liderança não entram de forma sistemática na análise. O sistema formaliza o registro, ancora a análise no perfil profissional, faz um stress-test técnico e entrega um resumo executivo com fontes.

### 1.3 Usuários-alvo

- Lideranças e facilitadores de reunião  
- Times de produto, operações e transformação  
- Analistas que precisam transformar conversa em plano acionável  

### 1.4 Princípios de produto

- A **transcrição/ata** é a fonte principal de fatos; inferências devem ser explícitas  
- O **Tomador não “esteve” na reunião**: interpreta só o registro escrito  
- Personas vêm da pasta `pessoas/` — a UI não recebe upload de currículo  
- Fluxo em **cinco jornadas** claras e encadeáveis  
- Chaves de API ficam **apenas no `.env` local** (nunca no Git)  

---

## 2. Escopo

### 2.1 Em escopo

- Geração de ata (modo prompt ou completo; especialistas; NLP opcional; Q&A)  
- Gestão de personas via pasta `pessoas/` (adicionar / atualizar)  
- Análise institucional com **um ou mais Tomadores** + Especialista IA + lentes  
- Análise comparativa entre as vozes  
- Resumo consolidado (problema e o que fazer no topo; `Fonte:` por seção)  
- Studio / NotebookLM (opcional) + PPTX/infográfico locais  
- Exportação DOCX/PDF (atas); DOCX (análise, comparativa, resumo)  
- Persistência em `outputs/` (`ata_`, `analise_`, `comparativa_`, `resumo_`, …)  

### 2.2 Fora de escopo

- Autenticação de usuários / multi-tenant  
- Edição colaborativa em tempo real  
- Integração com calendário ou Zoom/Teams  
- API oficial / Enterprise do NotebookLM  
- Servidor FastAPI externo do `ata_maker` (módulo embarcado)  
- Upload de currículos pela interface  

---

## 3. Arquitetura lógica

```text
┌──────────────────────────────────────────────────────────────────┐
│                     UI Streamlit (app.py)                        │
│         Marca Gedanken + 5 jornadas + sidebar de status          │
└───┬──────┬──────┬──────┬──────┬──────────────────────────────────┘
    │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼
  Ata   Análise Comp. Resumo  Studio
    │      │      │      │      │
    ▼      ▼      └──────┘      ▼
 ata_maker  analisador     resumo_     notebooklm-py
 + NLP      + perfis       consolidado + OpenAI local
    │      │                    │            │
    └──────┴────────────────────┴────────────┘
                         │
                    OpenAI API
                 (.env local only)
```

### 3.1 Stack

| Camada | Tecnologia |
|--------|------------|
| UI | Streamlit |
| Linguagem | Python 3.10+ |
| LLM | OpenAI Chat Completions |
| Documentos | python-docx, fpdf2, python-pptx |
| Automação NLM | playwright, notebooklm-py (não oficial) |
| Config | python-dotenv (`.env` gitignored) |

### 3.2 Execução

```bash
./rodar.sh
```

Interface: `http://localhost:8501`.

---

## 4. Jornadas

### 4.1 Jornada 1 — Gerar Ata

**Objetivo:** transformar transcrição em ata acionável e alimentar a jornada 2.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Upload (`.txt`, `.csv`, `.docx`) ou texto colado |
| Saídas | Markdown; DOCX/PDF; `outputs/ata_{stem}_{timestamp}.docx` |
| Pré-condição | `OPENAI_API_KEY` |

- Modos: **prompt** ou **análise completa** (especialistas; botões Selecionar todos / Limpar)  
- NLP opcional nos dois modos (local; seção no final da ata)  
- Perguntas rápidas sobre a transcrição  
- Encaminhamento automático opcional para Análise (anexa ata + preenche pedido)  

### 4.2 Jornada 2 — Análise Institucional

**Objetivo:** Tomador(es) interpretam problema/atas; Especialista IA faz stress-test.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Perfis + lentes + problema + documentos/atas |
| Saídas | `analise_tomador`, `avaliacao_especialista`, `analises_multiplas`; DOCX |
| Personas | Multiselect de Tomadores (default: todos); Adicionar / Atualizar via `pessoas/` |

Lentes: Planejador, Analítico, Técnico, Financista.

### 4.3 Jornada 3 — Análise Comparativa

**Objetivo:** confrontar Tomador × Especialista.

| Entrada | Saídas |
|---------|--------|
| Análises da jornada 2 | `analise_comparativa` → `outputs/comparativa_*.docx` |

### 4.4 Jornada 4 — Resumo

**Objetivo:** consolidar as três fontes em um documento enxuto — quem ler **só** o resumo precisa saber o que fazer (TO-DO explícito).

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Ata(s), análise(s) de persona, Especialista IA, problema |
| Módulo | `core/resumo_consolidado.py` + `jornadas/jornada_resumo.py` |
| Persistência | `resumo_consolidado` na sessão; `outputs/resumo_{timestamp}.docx` |

#### Seções obrigatórias do documento

1. **Problema** (prioritário)  
2. **TO-DO (o que deve ser feito)** — checklist `- [ ]` com dono/prazo quando houver; divergências Tomador × Especialista explícitas  
3. **Resumo da ata** — só fatos/decisões/pendências (**sem** análise opinativa)  
4. **Resumo das personas consultadas**  
5. **Resumo do Analista Sênior em IA**  
6. **Fontes usadas**  

Cada seção de conteúdo (exceto Fontes) termina com `Fonte: …`. Não inventar fatos fora das fontes.

### 4.5 Jornada 5 — Studio / NotebookLM

**Objetivo:** comunicação visual a partir dos `.docx` gerados.

| Caminho | Comportamento |
|---------|----------------|
| NotebookLM | Login Chrome a cada pedido → upload → slide deck + infográfico (`notebooklm-py`) |
| Local (padrão) | Skills `apresentacao-visual` (PPTX 16:9 via `python-pptx`) e `infografico-visual` (HTML responsivo) |
| Local (legado) | Infográfico PNG 16:9 via Images API (opcional) |

Riscos: API não oficial; UI/quota Google; precisa display (WSLg).

---

## 5. Modelo de dados (resumido)

### 5.1 Currículo / perfil

- Bruto: `pessoas/*.txt`  
- Analítico: `perfis/perfis.json` (cache com `arquivo`/`mtime`)  

### 5.2 Sessão Streamlit (principais)

| Chave | Uso |
|-------|-----|
| `jornada_ativa` | `ata` \| `analise` \| `comparativa` \| `resumo` \| `studio` |
| `atas_anexadas` | lista `{nome, texto}` |
| `analises_multiplas` | lista `{id, nome, analise, avaliacao}` |
| `analise_tomador` / `avaliacao_especialista` | consolidado jornada 2 |
| `analise_comparativa` | jornada 3 |
| `resumo_consolidado` / `ultimo_resumo_docx` | jornada 4 |
| `studio_*` / `nlm_*` | jornada 5 |
| `qa_historico` | Q&A da ata |

---

## 6. Integrações e configuração

### 6.1 Segredos

| Arquivo | Git | Conteúdo |
|---------|-----|----------|
| `.env` | **ignorado** | `OPENAI_API_KEY` real |
| `.env.example` | versionado | placeholders vazios |
| `.notebooklm/` | **ignorado** | Chrome local, storage de sessão |

### 6.2 Variáveis

| Variável | Obrigatória | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Sim (LLM) | — |
| `OPENAI_MODEL` | Não | `gpt-4o-mini` |
| `NOTEBOOKLM_STATE_PATH` | Não | `.notebooklm/storage_state.json` |
| `NOTEBOOKLM_CHROME_PATH` | Não | extract em `.notebooklm/chrome/` |

### 6.3 Dependências

`streamlit`, `openai`, `python-docx`, `fpdf2`, `pandas`, `openpyxl`, `python-dotenv`, `playwright`, `python-pptx`, `notebooklm-py`.

Scripts: `./scripts/install_playwright_deps.sh`, `./scripts/install_chrome_wsl.sh`.

---

## 7. Estrutura do repositório

```text
app.py
rodar.sh
ESPECIFICACAO.md
README.md
AGENTS.md / CLAUDE.md     # entrada Reversa
jornadas/                 # ata, analise, comparativa, resumo, studio
core/                     # analisador, resumo_consolidado, exports…
modulos/ata_maker/
modulos/notebooklm/
pessoas/
perfis/
outputs/
.agents/skills/           # skills Reversa
.reversa/                 # state, plan, config
scripts/
```

---

## 8. Requisitos funcionais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Marca (título + slogan) acima da navegação | Alta |
| RF-02 | Navegar entre as 5 jornadas | Alta |
| RF-03–08 | Ata: modos, especialistas, NLP, Q&A, DOCX/PDF, handoff | Alta |
| RF-09 | Múltiplas atas/documentos | Alta |
| RF-10–11 | Adicionar / atualizar personas via `pessoas/` | Alta |
| RF-12 | Análise multi-Tomador + lentes + Especialista | Alta |
| RF-13–14 | Comparativa + export DOCX | Alta/Média |
| RF-15–16 | Selecionar todos especialistas; persistir `ata_*.docx` | Alta |
| RF-17 | Resumo consolidado com fontes e prioridade problema/ações | Alta |
| RF-18 | Studio NotebookLM + fallback local | Média |

---

## 9. Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Interface em pt-BR |
| RNF-02 | Tema Gedanken (`#00B040`, `#001060`) |
| RNF-03 | NLP local sem deps pesadas |
| RNF-04 | Ata embarcada (sem HTTP externo) |
| RNF-05 | Não inventar fatos; marcar inferências |
| RNF-06 | Cache de perfis |
| RNF-07 | Segredos fora do Git |

---

## 10. Fluxos principais

### 10.1 Ata → Análise → (Comparativa) → Resumo

1. Gerar ata (jornada 1) → grava `outputs/ata_*.docx`  
2. Análise com Tomador(es) + Especialista (jornada 2)  
3. Opcional: Comparativa (jornada 3)  
4. **Resumo** (jornada 4) — problema e o que fazer no topo  
5. Opcional: Studio (jornada 5) para PPTX/infográfico  

### 10.2 Personas

1. Colocar/editar `.txt` em `pessoas/`  
2. **Adicionar personas** ou **Atualizar pessoas**  

---

## 11. Critérios de aceite (smoke)

- [ ] App sobe com 5 jornadas na barra  
- [ ] Ata gera DOCX em `outputs/`  
- [ ] Selecionar todos / Limpar especialistas  
- [ ] Multi-Tomador na análise  
- [ ] Resumo exige material; seções com `Fonte:`; prioriza problema/ações  
- [ ] Studio lista `resumo_*.docx`  
- [ ] Sem `OPENAI_API_KEY`, fluxos LLM avisam  
- [ ] `.env` não versionado  

---

## 12. Glossário

| Termo | Definição |
|-------|-----------|
| Tomador de Decisão | Perfil derivado de `pessoas/` |
| Especialista IA | Segunda voz fixa do sistema |
| Lente | Perspectiva de continuidade |
| Ata | Documento estruturado da transcrição |
| Resumo | Consolidação rastreável (jornada 4) |
| Persona | Sinônimo operacional de perfil/tomador |

---

## 13. Referências

- `README.md` — setup  
- `jornadas/comum.py` — INFO_JORNADAS  
- `core/resumo_consolidado.py` — prompt e geração do resumo  
- `.reversa/plan.md` — plano Reversa  
- `_legado_node/` — protótipo anterior (referência)  

---

*Documento alinhado ao código em `/home/joyce/projetos/briefboard` (BriefBoard - Gedanken).*
