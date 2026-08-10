# BriefBoard - Gedanken

Aplicação Streamlit que transforma currículos em perfis analíticos e conduz o fluxo **ata → análise → comparativa → resumo → studio**.

Documentação completa: ver [`ESPECIFICACAO.md`](ESPECIFICACAO.md).

## O que faz

1. Lê os currículos em `pessoas/*.txt` e gera perfis em `perfis/perfis.json`
2. **Gerar Ata** — transcrição → ata (especialistas, NLP, perguntas rápidas; DOCX/PDF em `outputs/`)
3. **Análise Organizacional** — um ou mais Tomadores + lentes + Especialista IA
4. **Análise Comparativa** (opcional) — contraste técnico entre as vozes
5. **Resumo** — pacote `resumo_*.docx` com as etapas da sessão
6. **Studio / NotebookLM** — login Google → slide deck + infográfico; fallback PPTX/infográfico locais

## Pré-requisitos

- Python 3.10+
- Chave da API OpenAI
- Conta Google (opcional; só para NotebookLM na jornada 5)
- Display gráfico no WSL (WSLg) se for usar NotebookLM

## Setup

```bash
cd /home/joyce/projetos/briefboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
./scripts/install_playwright_deps.sh   # libs locais (sem sudo)
./scripts/install_chrome_wsl.sh        # Google Chrome Linux (login NotebookLM)
cp .env.example .env
# Edite .env e preencha OPENAI_API_KEY
```

## Executar

```bash
./rodar.sh
# ou: source .venv/bin/activate && streamlit run app.py
```

A interface abre em `http://localhost:8501` como **BriefBoard - Gedanken**.

## Estrutura

```text
app.py                 # Interface Streamlit
jornadas/              # UI das 5 jornadas
core/                  # Análise, perfis, documentos, resumo, export
modulos/ata_maker/     # Motor de ata embarcado
modulos/notebooklm/    # notebooklm-py (jornada 5)
outputs/               # Relatórios .docx / pptx / png
```

## Jornadas

1. **Gerar Ata**
2. **Análise Organizacional**
3. **Análise Comparativa** (opcional)
4. **Resumo** — consolidação com fontes
5. **Studio / NotebookLM** — comunicação visual

A ata gerada na jornada 1 entra automaticamente nos documentos da jornada 2 e é persistida em `outputs/ata_*.docx`.
