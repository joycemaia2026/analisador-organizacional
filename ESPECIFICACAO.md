# Especificação — Analisador Organizacional

| Campo | Valor |
|-------|--------|
| Produto | Analisador Organizacional |
| Marca | Gedanken |
| Slogan | Da ata à decisão — com a lente de quem lidera. |
| Versão do documento | 1.1 |
| Data | 2026-07-17 |
| Tipo | Especificação funcional e técnica |

---

## 1. Visão geral

### 1.1 Objetivo

Aplicação web que apoia a **continuidade organizacional** após reuniões e decisões, conectando:

1. **Registro** — transformar transcrição em ata estruturada  
2. **Interpretação** — analisar o problema/atas sob o olhar de um Tomador de Decisão real da empresa  
3. **Contraste** — confrontar a visão do Tomador com a de um Especialista Sênior em IA  
4. **Comunicação** — reunir artefatos, enviar ao NotebookLM e gerar PPTX/infográfico  

### 1.2 Problema que resolve

Reuniões geram informação dispersa; decisões e pendências se perdem; perfis de liderança não entram de forma sistemática na análise. O sistema formaliza o registro, ancora a análise no perfil profissional, faz um stress-test técnico da solução e prepara material de comunicação executiva.

### 1.3 Usuários-alvo

- Lideranças e facilitadores de reunião  
- Times de produto, operações e transformação  
- Analistas que precisam transformar conversa em plano acionável  

### 1.4 Princípios de produto

- A **transcrição/ata** é a fonte principal de fatos; inferências devem ser explícitas  
- O **Tomador não “esteve” na reunião**: interpreta só o registro escrito  
- Personas vêm da pasta `pessoas/` — a UI não recebe upload de currículo  
- Fluxo em **quatro jornadas** claras e encadeáveis  

---

## 2. Escopo

### 2.1 Em escopo

- Geração de ata a partir de transcrição (modo rápido ou completo)  
- Perguntas rápidas sobre a transcrição  
- Análise NLP local (sentimento, palavras, perfil linguístico)  
- Gestão de personas via pasta `pessoas/` (adicionar novos / atualizar existentes)  
- Análise organizacional (Tomador + Especialista IA + lentes)  
- Análise comparativa entre as duas vozes  
- Anexos múltiplos (atas/documentos) em `.txt`, `.md`, `.csv`, `.docx`  
- Exportação DOCX e PDF (atas); DOCX (relatórios de análise)  
- Persistência de atas em `outputs/ata_*.docx`  
- Jornada Studio: `.docx` → NotebookLM (`notebooklm-py`, login Chrome a cada pedido) + fallback PPTX/infográfico locais  

### 2.2 Fora de escopo

- Autenticação de usuários / multi-tenant  
- Edição colaborativa em tempo real  
- Integração com calendário ou Zoom/Teams  
- API oficial / Enterprise do NotebookLM (usa `notebooklm-py` não oficial no consumer)  
- Servidor FastAPI externo do projeto `ata_maker` (o módulo está embarcado)  
- Upload de currículos pela interface  

---

## 3. Arquitetura lógica

```text
┌─────────────────────────────────────────────────────────┐
│                    UI Streamlit (app.py)                │
│  Marca + navegação de jornadas + sidebar de contexto   │
└─────────────┬───────────────────┬───────────────┬───────┘
              │                   │               │
     ┌────────▼────────┐ ┌────────▼────────┐ ┌───▼────────────┐
     │ 1. Gerar Ata    │ │ 2. Análise Org. │ │ 3. Comparativa │
     └────────┬────────┘ └────────┬────────┘ └───┬────────────┘
              │                   │               │
     ┌────────▼────────┐ ┌────────▼────────┐     │
     │ modulos/        │ │ core/analisador │◄────┘
     │ ata_maker       │ │ leitor_perfis   │
     │ (engine, NLP,   │ │ documentos      │
     │  perguntas)     │ │ lentes, prompts │
     └────────┬────────┘ └────────┬────────┘
              │                   │
              └─────────┬─────────┘
                        ▼
                 OpenAI API (+ NLP local)
```

### 3.1 Stack

| Camada | Tecnologia |
|--------|------------|
| UI | Streamlit |
| Linguagem | Python 3.10+ |
| LLM | OpenAI Chat Completions |
| Documentos | python-docx, fpdf2 |
| Dados tabulares | pandas, openpyxl |
| Config | python-dotenv (`.env`) |

### 3.2 Execução

```bash
./rodar.sh
# ou: streamlit run app.py
```

Interface em `http://localhost:8501`.

---

## 4. Jornadas

### 4.1 Jornada 1 — Gerar Ata

**Objetivo:** transformar transcrição informal em ata acionável e, opcionalmente, alimentar a jornada 2.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Transcrição via upload (`.txt`, `.csv`, `.docx`) ou texto colado |
| Saídas | Ata estruturada (Markdown interno); download **DOCX** e **PDF**; anexo à sessão |
| Pré-condição | `OPENAI_API_KEY` configurada |

#### 4.1.1 Perguntas rápidas

- Disponíveis após haver transcrição carregada  
- Sugestões prontas + pergunta livre  
- Fonte principal: transcrição; LLM organiza/sintetiza; inferências devem ser marcadas  
- Mantém histórico na sessão  

#### 4.1.2 Modos de geração

| Modo | Comportamento |
|------|----------------|
| **Prompt principal** | Um prompt consolidado (rápido) |
| **Análise completa** | Especialistas selecionados pelo usuário (nenhum pré-marcado) → consolidação se ≥2 → resumo executivo |

#### 4.1.3 Especialistas (análise completa)

O usuário escolhe um ou mais:

1. Especialista em Produto  
2. Especialista em Marketing  
3. Especialista em Finanças  
4. Especialista em Inteligência Artificial  
5. Especialista em TI  

#### 4.1.4 Análise NLP

- Opção disponível nos **dois** modos  
- Roda localmente (sem chamada OpenAI)  
- Inclui: sentimento, palavras frequentes, perfil linguístico, frases polarizadas  
- No documento gerado, a seção NLP aparece **por último**  

#### 4.1.5 Encaminhamento para Análise

- Checkbox: ir automaticamente para Análise Organizacional após gerar  
- Preenche o pedido de ajuda com o resumo da ata  
- Anexa a ata à lista de documentos da jornada 2  
- Várias atas podem acumular na sessão  

#### 4.1.6 Download

- Seletor da ata (se houver mais de uma)  
- Dois botões no topo: **Baixar DOCX** e **Baixar PDF**  
- Sem download `.md` e sem botões duplicados  

---

### 4.2 Jornada 2 — Análise Organizacional

**Objetivo:** o Tomador interpreta problema e/ou atas; o Especialista IA avalia essa visão.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Perfil (Tomador) + lentes + problema/contexto + documentos/atas |
| Saídas | Análise do Tomador + avaliação do Especialista; export `.docx` em `outputs/` |
| Pré-condição | Pelo menos um perfil convertido a partir de `pessoas/` |

#### 4.2.1 Personas

| Ação | Comportamento |
|------|----------------|
| **Adicionar personas** | Varre `pessoas/*.txt`, converte apenas arquivos **ainda sem perfil** |
| **Atualizar pessoas** | Relê `pessoas/` e **reconverte** os perfis já cadastrados |

Regras:

- O usuário **não** envia currículo pela UI  
- Currículos são arquivos `.txt` colocados na pasta `pessoas/`  
- Cache estruturado em `perfis/perfis.json`  

Campos típicos do perfil: `id`, `nome`, `cargo`, `empresa`, formação, especialidades, competências, anos de experiência, perfil analítico, forma de pensar, perguntas típicas, indicadores, pontos fortes, limitações.

#### 4.2.2 Lentes de continuidade

Multiselect (default: Planejador + Analítico):

| ID | Nome | Foco |
|----|------|------|
| `planejador` | Planejador | sequência, donos, prazos, dependências |
| `analitico` | Analítico | hipóteses, evidências, causa-raiz |
| `tecnico` | Técnico | viabilidade, integração, risco operacional |
| `financista` | Financista | custo, ROI, trade-offs |

As lentes ampliam o roteiro (pré / durante / pós) sem substituir o perfil do Tomador.

#### 4.2.3 Documentos / atas

- Upload múltiplo: `.txt`, `.md`, `.csv`, `.docx`  
- Atas da jornada 1 entram automaticamente  
- Lista com preview, remoção individual e limpar todas  
- Conteúdo concatenado no prompt como blocos `Documento N`  

#### 4.2.4 Saídas da análise

- **Tomador:** relatório estruturado (diagnóstico, plano, riscos, continuidade etc.)  
- **Especialista IA:** avaliação crítica / stress-test da visão do Tomador  
- Persistência: `outputs/analise_{tomador}_{timestamp}.docx`  

---

### 4.3 Jornada 3 — Análise Comparativa

**Objetivo:** confrontar as duas vozes e reduzir viés.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | Análise do Tomador + avaliação do Especialista (jornada 2) |
| Saídas | Síntese comparativa (convergências, divergências, gaps, conceitos) |
| Persistência | `outputs/comparativa_{tomador}_{timestamp}.docx` |

Pré-condição: análises da jornada 2 presentes na sessão.

---

### 4.4 Jornada 4 — Studio / NotebookLM

**Objetivo:** reunir os `.docx` das jornadas 1–3, autenticar no NotebookLM consumer e gerar slide deck + infográfico (com download local); fallback OpenAI para PPTX/infográfico locais.

| Aspecto | Especificação |
|---------|----------------|
| Entrada | `outputs/*.docx` com prefixos `ata_`, `analise_`, `comparativa_` |
| NotebookLM | `notebooklm-py` (não oficial): login Chrome real a cada pedido → create notebook → add files → generate → download |
| Saídas NLM | `outputs/nlm_slides_{timestamp}.pptx` e `outputs/nlm_infografico_{timestamp}.png` |
| Fallback local | OpenAI + `python-pptx` / HTML+screenshot → `apresentacao_*.pptx`, `infografico_*.png` |

Fluxo UI:

1. Checklist dos `.docx` (exige ≥ 1)  
2. **Gerar no NotebookLM** — abre Chrome; usuário faz login Google; pipeline automática  
3. **Gerar PPTX local** / **Gerar infográfico local** — independentes do Google  

Riscos: lib não oficial pode quebrar; quota Google; login exige display (WSLg).

Sem `OPENAI_API_KEY`, exports locais avisam; NotebookLM não depende da OpenAI.

---

## 5. Modelo de dados (resumido)

### 5.1 Currículo bruto (`pessoas/*.txt`)

Texto livre (ex.: export LinkedIn). Identificador = stem do arquivo (`persona1`, etc.).

### 5.2 Perfil analítico (`perfis/perfis.json`)

Lista JSON de objetos com metadados de fonte (`arquivo`, `mtime`) para invalidação/reconversão.

### 5.3 Estado de sessão (Streamlit)

Principais chaves:

| Chave | Uso |
|-------|-----|
| `jornada_ativa` | `ata` \| `analise` \| `comparativa` \| `studio` |
| `atas_anexadas` | lista `{nome, texto}` |
| `ultimo_ata_docx` / `outputs_ata` | caminho(s) do `.docx` persistido da jornada 1 |
| `jornada_analise_problema` | pedido de ajuda pré-preenchido |
| `analise_tomador` / `avaliacao_especialista` | saídas da jornada 2 |
| `analise_comparativa` | saída da jornada 3 |
| `studio_pptx` / `studio_infografico` | caminhos dos artefatos da jornada 4 |
| `qa_historico` | perguntas rápidas da jornada 1 |

---

## 6. Integrações e configuração

### 6.1 Variáveis de ambiente

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `OPENAI_API_KEY` | Sim (LLM) | — | Chave da API OpenAI |
| `OPENAI_MODEL` | Não | `gpt-4o-mini` | Modelo de chat |
| `NOTEBOOKLM_STATE_PATH` | Não | `.notebooklm/storage_state.json` | Sessão notebooklm-py |
| `NOTEBOOKLM_CHROME_PATH` | Não | extract local | Chrome Linux para login |

Arquivo: `.env` (modelo em `.env.example`).

### 6.2 Dependências principais

`streamlit`, `openai`, `python-docx`, `fpdf2`, `pandas`, `openpyxl`, `python-dotenv`, `playwright`, `python-pptx`, `notebooklm-py`.

Browsers: `python -m playwright install chromium`; Chrome Linux via `./scripts/install_chrome_wsl.sh`.

---

## 7. Estrutura do repositório

```text
app.py                 # Entrypoint Streamlit
rodar.sh               # Setup + execução
requirements.txt
.env.example
jornadas/
  comum.py             # Marca, tema, navegação, INFO_JORNADAS
  jornada_ata.py
  jornada_analise.py
  jornada_comparativa.py
  jornada_studio.py
core/
  analisador.py
  leitor_perfis.py
  parser_curriculo.py
  prompts.py
  lentes_continuidade.py
  especialista_ia.py
  documentos.py
  ata_maker_client.py
  openai_client.py
  export_docx.py
  export_pdf.py
  export_pptx.py
  export_infografico.py
  outputs_collector.py
  utils.py
modulos/ata_maker/
  engine.py
  prompts_catalog.py
  nlp.py
  perguntas.py
  prompts/default_prompt.txt
modulos/notebooklm/
  auth.py              # login Chrome via notebooklm CLI
  pipeline.py          # create / add / generate / download
  client.py
  browser.py           # Chrome local + syslibs
pessoas/               # Currículos .txt
perfis/perfis.json     # Cache de perfis
outputs/               # Relatórios .docx / pptx / png
.notebooklm/           # Sessão Playwright (gitignored)
assets/                # Logo Gedanken
```

---

## 8. Requisitos funcionais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Exibir marca (título + slogan) acima da navegação | Alta |
| RF-02 | Navegar entre as 4 jornadas com botões no topo | Alta |
| RF-03 | Gerar ata em modo prompt ou completo | Alta |
| RF-04 | Selecionar especialistas sem pré-seleção | Alta |
| RF-05 | Incluir NLP opcional nos dois modos de ata | Alta |
| RF-06 | Perguntas rápidas ancoradas na transcrição | Alta |
| RF-07 | Download da ata em DOCX e PDF | Alta |
| RF-08 | Encaminhar resumo/ata para Análise Organizacional | Alta |
| RF-09 | Anexar múltiplas atas/documentos (txt/md/csv/docx) | Alta |
| RF-10 | Adicionar personas lendo novos `.txt` em `pessoas/` | Alta |
| RF-11 | Atualizar pessoas reconvertendo perfis da pasta | Alta |
| RF-12 | Analisar com Tomador + lentes + Especialista IA | Alta |
| RF-13 | Gerar análise comparativa das duas vozes | Alta |
| RF-14 | Exportar relatórios de análise em DOCX | Média |
| RF-15 | Selecionar todos / limpar especialistas na jornada 1 | Alta |
| RF-16 | Persistir atas em `outputs/ata_*.docx` | Alta |
| RF-17 | Jornada Studio: NotebookLM via notebooklm-py (login a cada pedido) + fallback local | Alta |

---

## 9. Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Interface em português do Brasil |
| RNF-02 | Tema visual Gedanken (verde `#00B040`, navy `#001060`) |
| RNF-03 | NLP local sem dependências pesadas (wordcloud/matplotlib) |
| RNF-04 | Módulo ata embarcado (sem serviço HTTP externo) |
| RNF-05 | Não inventar fatos fora da transcrição/documentos; marcar inferências |
| RNF-06 | Cache de perfis para evitar reconversão desnecessária |

---

## 10. Fluxos principais (resumo)

### 10.1 Transcrição → Ata → Análise

1. Usuário cola/envia transcrição  
2. (Opcional) faz perguntas rápidas  
3. Escolhe modo, especialistas e/ou NLP  
4. Gera ata e baixa DOCX/PDF se desejar  
5. Sistema anexa ata e abre Análise com resumo no pedido de ajuda  
6. Usuário escolhe Tomador e lentes → Analisar  
7. (Opcional) gera Comparativa e exporta  

### 10.2 Manutenção de personas

1. Operador coloca/edita `.txt` em `pessoas/`  
2. Clica **Adicionar personas** (novos) ou **Atualizar pessoas** (existentes)  
3. Sistema regenera `perfis/perfis.json` via LLM  

---

## 11. Critérios de aceite (smoke)

- [ ] App sobe com `./rodar.sh` e abre a marca + 4 jornadas  
- [ ] Ata modo prompt gera texto e permite DOCX/PDF  
- [ ] Ata modo completo: **Selecionar todos** / **Limpar** nos especialistas  
- [ ] Ata gerada grava `outputs/ata_*.docx`  
- [ ] NLP, quando ativo, aparece no final da ata  
- [ ] Pergunta rápida responde com base na transcrição  
- [ ] Novo `.txt` em `pessoas/` é detectado por **Adicionar personas**  
- [ ] **Atualizar pessoas** regenera perfis existentes  
- [ ] Análise com ata anexada roda Tomador + Especialista  
- [ ] Comparativa só libera com análises prévias  
- [ ] Jornada 4: **Gerar no NotebookLM** abre Chrome, após login gera slides/infográfico  
- [ ] PPTX e infográfico **locais** geram sem depender do NotebookLM  
- [ ] Sem `OPENAI_API_KEY`, exports locais avisam; NotebookLM segue disponível  
- [ ] Sem `OPENAI_API_KEY`, fluxos LLM exibem aviso claro  

---

## 12. Glossário

| Termo | Definição |
|-------|-----------|
| Tomador de Decisão | Perfil analítico derivado de um currículo em `pessoas/` |
| Especialista IA | Segunda voz fixa do sistema (não vem de `pessoas/`) |
| Lente | Perspectiva de continuidade (planejador, analítico, técnico, financista) |
| Ata | Documento estruturado gerado a partir da transcrição |
| Persona | Sinônimo operacional de perfil/tomador no contexto da UI |

---

## 13. Referências internas

- `README.md` — setup e visão resumida  
- `jornadas/comum.py` — textos de orientação das jornadas  
- `modulos/ata_maker/` — motor de ata embarcado  
- `_legado_node/` — protótipo anterior (somente referência)  

---

*Documento gerado a partir do estado atual do código em `/home/joyce/projetos/personas`.*
