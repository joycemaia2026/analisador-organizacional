# Analisador Organizacional

Aplicação Streamlit (Gedanken) que transforma currículos em perfis analíticos e conduz o fluxo **ata → análise → comparativa → studio**.

Documentação completa: ver [`ESPECIFICACAO.md`](ESPECIFICACAO.md).

## O que faz

1. Lê os currículos em `pessoas/*.txt` e gera perfis em `perfis/perfis.json`
2. **Gerar Ata** — transcrição → ata (especialistas, NLP, perguntas rápidas; DOCX/PDF em `outputs/`)
3. **Análise Organizacional** — um ou mais Tomadores + lentes + Especialista IA
4. **Análise Comparativa** — contraste técnico entre as vozes
5. **Studio / NotebookLM** — login Google no Chrome → sobe `.docx` → slide deck + infográfico (via `notebooklm-py`); fallback PPTX/infográfico locais (OpenAI)

## Pré-requisitos

- Python 3.10+
- Chave da API OpenAI (para jornadas 1–3 e exports locais)
- Conta Google (NotebookLM consumer na jornada 4)
- Display gráfico no WSL (WSLg) para o login Chrome

## Setup

```bash
cd /home/joyce/projetos/personas
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

A interface abre em `http://localhost:8501`.

Personas: coloque `.txt` em `pessoas/` e use **Adicionar personas** / **Atualizar pessoas** na jornada 2 (sem upload pela tela).

## Estrutura

```text
app.py                 # Interface Streamlit
ESPECIFICACAO.md       # Especificação funcional e técnica
jornadas/              # UI das 4 jornadas
core/                  # Análise, perfis, documentos, export
modulos/ata_maker/     # Motor de ata embarcado
modulos/notebooklm/    # notebooklm-py: login + pipeline de produtos
pessoas/               # Currículos brutos (.txt)
perfis/                # perfis.json gerado
outputs/               # Relatórios .docx / pptx / png
assets/                # Logo Gedanken
.notebooklm/           # Chrome local, syslibs, storage (gitignored)
scripts/               # install_chrome_wsl.sh, install_playwright_deps.sh
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `OPENAI_API_KEY` | Chave da OpenAI (LLM / exports locais) |
| `OPENAI_MODEL` | Modelo (default: `gpt-4o-mini`) |
| `NOTEBOOKLM_STATE_PATH` | storage_state do notebooklm-py |
| `NOTEBOOKLM_CHROME_PATH` | Chrome Linux (opcional; senão usa extract local) |

Na jornada 4, **Gerar no NotebookLM** abre o Chrome para login a cada pedido; em seguida sobe as fontes e baixa slide deck + infográfico. A lib é **não oficial** e pode quebrar se o Google mudar endpoints.

## Jornadas

1. **Gerar Ata** — módulo `modulos/ata_maker` (embarcado)
2. **Análise Organizacional** — Tomador(es) + Especialista IA + lentes
3. **Análise Comparativa** — contraste entre as vozes
4. **Studio / NotebookLM** — produtos NotebookLM + fallback local OpenAI

A ata gerada na jornada 1 entra automaticamente nos documentos da jornada 2 e é persistida em `outputs/ata_*.docx`.
