# Analisador Organizacional

Aplicação Streamlit (Gedanken) que transforma currículos em perfis analíticos e conduz o fluxo **ata → análise organizacional → comparativa**.

Documentação completa: ver [`ESPECIFICACAO.md`](ESPECIFICACAO.md).

## O que faz

1. Lê os currículos em `pessoas/*.txt` e gera perfis em `perfis/perfis.json`
2. **Gerar Ata** — transcrição → ata (especialistas, NLP, perguntas rápidas; download DOCX/PDF)
3. **Análise Organizacional** — Tomador + lentes + Especialista IA sobre problema/atas
4. **Análise Comparativa** — contraste técnico entre as duas vozes

## Pré-requisitos

- Python 3.10+
- Chave da API OpenAI

## Setup

```bash
cd /home/joyce/projetos/personas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
jornadas/              # UI das 3 jornadas
core/                  # Análise, perfis, documentos, export
modulos/ata_maker/     # Motor de ata embarcado
pessoas/               # Currículos brutos (.txt)
perfis/                # perfis.json gerado
outputs/               # Relatórios .docx
assets/                # Logo Gedanken
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `OPENAI_API_KEY` | Chave da OpenAI (obrigatória) |
| `OPENAI_MODEL` | Modelo (default: `gpt-4o-mini`) |

## Jornadas

1. **Gerar Ata** — módulo `modulos/ata_maker` (embarcado)
2. **Análise Organizacional** — Tomador + Especialista IA + lentes
3. **Análise Comparativa** — contraste entre as duas vozes

A ata gerada na jornada 1 entra automaticamente nos documentos da jornada 2.
