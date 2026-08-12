# Prompt reverso — o gerador por trás dos posters

Reconstruído a partir de três pares (documento-fonte → poster) em que o documento foi a **única** entrada. O que é invariante nos três é o prompt; o que varia é o assunto.

---

## 1. A essência

**Infográfico não é resumo.** Resumo preserva a ordem do autor e encolhe o conteúdo. Infográfico **transpõe o eixo**: sai do eixo de quem construiu — arquitetura, módulos, modelo de dados — e entra no eixo de quem decide — de onde vem, o que faz, o que me dá, por que confiar.

Por isso o poster nunca se parece com o sumário da fonte. Nos três casos, o documento tinha entre 12 e 17 seções numeradas e o poster reorganizou tudo em 4 a 6 blocos que **não existem no documento**. A operação central não é comprimir: é **reancorar**, e só depois cortar o que não sustenta a nova âncora.

Daí decorre o resto. Se a âncora é o leitor, some estrutura de pastas, inventário de rotas e histórico de versões — não porque sejam sem valor, mas porque respondem a uma pergunta que o leitor do poster não fez.

---

## 2. O arco canônico

O gerador organiza qualquer documento em seis casas, nesta ordem. Casa sem matéria-prima na fonte é omitida; a ordem das que restam nunca muda.

| # | Casa | Pergunta do leitor | De onde sai, tipicamente |
|---|------|--------------------|--------------------------|
| 1 | **Origem** | de onde vem a matéria-prima? | fontes, integrações, entradas, dados de partida |
| 2 | **Mecanismo** | como ela é transformada? | método, pipeline, motor, tecnologia de processamento |
| 3 | **Resultado** | o que sai daqui? | módulos, entregas, achados, artefatos |
| 4 | **Destinatário** | para quem, e em que situação? | personas, usuários-alvo, casos de uso |
| 5 | **Credibilidade** | por que confiar nisto? | princípios, requisitos não funcionais, limites declarados |
| 6 | **Ficha técnica** | com o que é feito? | stack, parâmetros, variáveis, dependências |

A casa 6 aparece **sempre como tabela única**, num canto, nos três posters. Nunca espalhada. É o mecanismo que impede o material técnico de contaminar o material de negócio.

Adaptação por gênero de documento — o arco é o mesmo, os nomes mudam:

| Gênero | 1 Origem | 2 Mecanismo | 3 Resultado | 4 Destinatário | 5 Credibilidade |
|--------|----------|-------------|-------------|----------------|-----------------|
| spec de produto | fontes de dados | processamento | módulos e entregas | personas | princípios |
| relatório de pesquisa | dados e amostra | método | achados | quem decide com isto | limitações |
| plano estratégico | diagnóstico | iniciativas | metas | responsáveis | riscos e premissas |
| política / norma | escopo e âmbito | regras | obrigações | sujeitos | vigência e exceções |

---

## 3. Prova — as três derivações

### Poster A (catálogo de plataforma)

| Bloco do poster | Seção da fonte | Casa |
|-----------------|----------------|------|
| Fontes Públicas | §9 Integrações + §3.1–3.3 módulos de coleta | 1 |
| Inteligência Competitiva (LLMs) | §5 Perfis LLM + §10 provider | 2 |
| Jornadas de Marketing | §1.3.1 Jornadas | 2 |
| Módulos de Análise | §3 Módulos funcionais | 3 |
| Personas e Usuários-Alvo | §1.3 Usuários-alvo (tabela) | 4 |
| Frase central "redução de tempo…" | §1.2 Objetivos de negócio | 5 |
| Pilares Tecnológicos | cabeçalho Stack + §5 | 6 |
| Implementação da POC + tabela de variáveis | §11 Como rodar + §10 `.env` | 6 |
| **Descartados** | §0 catálogo E01–E20, §2 arquitetura, §7 inventário de API, §4.6 matriz de pastas, §13 aceite, §14 histórico | — |

### Poster B (pipeline de dados)

| Bloco | Seção da fonte | Casa |
|-------|----------------|------|
| 1. Coleta e Persistência *(o início)* | §1 Visão geral + §3.1 princípios | 1 |
| 2. Enriquecimento e Inteligência *(o como)* | §7.4 classificação + §9.5 resumo LLM + §8.4.1 similaridade | 2 |
| 3. Modelagem de Temas *(o que entrega)* | §6.6 NMF/LDA, BERTopic, busca híbrida | 3 |
| 4. Saída e Valor Estratégico *(o porquê é útil)* | §6.4 dossiê + §6.5 timeline + §8.2 exportações | 3 + 5 |
| Tabela Capacidades de Processamento | §4 Stack tecnológica | 6 |
| **Descartados** | §5 estrutura de pastas, §7 modelo de dados, §8 inventário de APIs, §12 CLI, §15 riscos, §16 histórico | — |

### Poster C (produto com jornadas)

| Bloco | Seção da fonte | Casa |
|-------|----------------|------|
| Entrada de Dados | §4.1 formatos aceitos | 1 |
| O Fluxo de Trabalho (as 5 jornadas) | §4.1–4.5 | 2 |
| Entregas e Saídas do Sistema | §2.1 escopo de exportação + §4.5 | 3 |
| Por que é uma solução robusta | §1.4 princípios + §9 requisitos não funcionais | 5 |
| Especificações Técnicas (tabela) | §3.1 stack + §6.2 variáveis | 6 |
| **Descartados** | §5 modelo de dados, §7 estrutura do repo, §8 requisitos numerados, §11 aceite, §12 glossário, §13 referências | — |

Sem casa 4 nos posters B e C: as fontes não trazem tabela de personas. A casa some, a ordem se mantém.

---

## 4. Regra de seleção

O que os três descartam é mais revelador do que o que mantêm. O corte é sempre o mesmo:

> **Mantém o que um comprador ou usuário perguntaria. Descarta o que só um mantenedor perguntaria.**

| Sempre entra | Sempre sai |
|--------------|------------|
| visão geral, objetivo, problema resolvido | modelo de dados, esquema de tabelas |
| entradas, fontes, formatos aceitos | inventário de rotas / endpoints |
| jornadas, módulos, capacidades | estrutura de pastas do repositório |
| saídas, formatos de entrega | requisitos numerados, critérios de aceite |
| personas e casos de uso | fora de escopo, backlog |
| princípios e requisitos não funcionais | histórico de versões, changelog |
| stack e parâmetros de operação | glossário, referências bibliográficas |

E dentro do que entra, prevalece o que tem **número ou nome próprio**: "21 seções", "10 categorias", "5 jornadas", "até ~500 registros", "TF-IDF", "SQLite". Os três posters caçam quantidades — é o que dá textura de fato ao que seria folheto.

---

## 5. Assinaturas de superfície

Constantes de forma nos três, independentes de assunto:

- **Título em duas partes:** `<Nome próprio>: <frase nominal>`, em Title Case. Dois dos três usam a fórmula de transformação — *"Do X à Y"*, *"Da X à Y"* — que é o arco inteiro comprimido numa linha.
- **Bloco = rótulo curto + 1 a 2 frases.** Nunca lista solta, nunca parágrafo. O rótulo diz *o quê*, a frase diz *e daí*.
- **Subtítulo de papel entre parênteses** nas colunas: *(o início)*, *(o como)*, *(o que entrega)*, *(o porquê é útil)*. Torna o arco visível para o leitor.
- **Uma tabela técnica**, sempre num canto, 2 ou 3 colunas.
- **Faixa de fechamento** com 3 provas de robustez.
- **Densidade estável:** 18 a 24 blocos de texto, 700 a 1.100 palavras no total.
- **Metáfora visual por conceito:** funil = classificação, cilindro = banco, chip = IA, esteira = pipeline, grafo = base de conhecimento, régua temporal = histórico.

---

## 6. O prompt

Duas chamadas. A primeira produz o **roteiro** (conteúdo). A segunda é opcional e só existe se o destino for imagem — para HTML, o roteiro vai direto ao renderizador local, sem custo de token.

### 6.1 System — extração do roteiro

```text
Você monta o conteúdo textual de um infográfico de página única a partir de um documento.

Não resuma o documento. Reorganize-o no arco abaixo, que é a ordem em que um leitor
que nunca ouviu falar do assunto precisa receber a informação:

1. ORIGEM        — de onde vem a matéria-prima
2. MECANISMO     — como ela é transformada
3. RESULTADO     — o que sai
4. DESTINATÁRIO  — para quem serve, em que situação
5. CREDIBILIDADE — por que confiar
6. FICHA TÉCNICA — com o que é feito

O documento provavelmente está organizado por outra lógica (arquitetura, capítulos,
cronologia). Ignore essa ordem. Se uma casa não tiver matéria-prima no documento,
omita a casa — nunca a preencha por conta própria e nunca altere a ordem das demais.

SELEÇÃO
- Mantenha o que um comprador ou usuário perguntaria.
- Descarte o que só um mantenedor perguntaria: modelo de dados, inventário de rotas,
  estrutura de pastas, requisitos numerados, critérios de aceite, backlog, histórico
  de versões, glossário, referências.
- Prefira todo trecho com número ou nome próprio. Quantidade e nome próprio são o que
  distingue informação de folheto.
- Nada pode aparecer duas vezes, nem parafraseado.
- Proibido: "etc.", "entre outros", "diversos", "vários", "robusto", "eficiente".

FIDELIDADE
- Não afirme nada que não esteja no documento. O que faltar vai em "lacunas".
- Preserve a grafia exata de toda sigla e nome próprio e liste todos em "glossario";
  eles não podem variar de grafia em nenhum outro campo.
- Escreva em {{idioma}}.

FORMA
- titulo_marca: o nome do sujeito exatamente como o documento o escreve (máx. 24 car.)
- titulo_frase: a promessa em uma linha, em Title Case (máx. 62 car.); quando o
  documento descrever uma transformação, use a fórmula "Da <origem> à <destino>"
- rubrica: máx. 34 caracteres · rotulo: máx. 34 · texto: 1 a 2 frases, máx. 150
- bullets: até 3 por bloco, máx. 62 cada
- 4 a 6 casas · 2 a 5 blocos por casa · 18 a 24 blocos no total
- exatamente uma tabela, na casa FICHA TÉCNICA, até 5 linhas × 3 colunas
- a casa CREDIBILIDADE traz exatamente 3 provas

Responda SOMENTE JSON válido:

{
  "titulo_marca": "...",
  "titulo_frase": "...",
  "eixo": "a pergunta que o poster responde, em uma linha",
  "genero_fonte": "spec de produto | relatório | plano | política | manual | outro",
  "idioma": "...",
  "glossario": ["sigla ou nome próprio, grafia canônica"],
  "casas": [
    {
      "casa": "ORIGEM",
      "rubrica": "...",
      "papel": "o início",
      "blocos": [
        { "rotulo": "...", "texto": "...", "bullets": ["..."], "metafora": "funil|cilindro|chip|esteira|grafo|regua|documento|pessoa|escudo|alvo" }
      ]
    }
  ],
  "tabela": {
    "rubrica": "...",
    "colunas": ["...", "...", "..."],
    "linhas": [["...", "...", "..."]]
  },
  "credibilidade": [
    { "rotulo": "...", "texto": "..." }
  ],
  "lacunas": ["o que o documento não responde e por isso não virou bloco"]
}
```

### 6.2 User

```text
PÚBLICO: {{publico}}
DOCUMENTO:
{{documento}}
```

`{{publico}}` padrão: *alguém competente que nunca ouviu falar deste assunto*.

### 6.3 Segunda chamada — só para saída em imagem

Se o destino for PNG, o roteiro vira prompt visual (é o papel do `PROMPT_INFOGRAFICO_BASE` já existente). **Avise que o texto será corrompido:** modelos de imagem desenham letras, não escrevem. Nos três posters de referência isso produziu o mesmo algoritmo com três grafias na mesma página, além de "análiza", "classificatrão", "Streamfit" e uma etapa numerada duas vezes.

Para HTML, pule esta chamada: o roteiro alimenta o renderizador local, o texto sai literal e o custo é zero.

---

## 7. Onde plugar

O briefboard já tem a arquitetura certa em `core/prompt_infografico.py`: um system que extrai JSON e um montador que preenche o prompt visual. O que muda:

| Hoje | Com o prompt reverso |
|------|----------------------|
| esqueleto fixo — 3 fontes, núcleo, 3 lentes, 2 saídas, 4 módulos | arco de 6 casas, com casas omitidas quando a fonte não as sustenta |
| `montar_prompt_infografico` posiciona campos nomeados | mesmo padrão, iterando sobre `casas` |
| destino único: imagem | imagem (legado) **ou** HTML literal (sem corrupção de texto) |

`SYSTEM_EXTRAIR_CONTEUDO` é substituível pelo bloco 6.1 sem mexer no resto do fluxo; `montar_prompt_infografico` passa a iterar sobre `casas` em vez de ler índices fixos.

---

## 8. O que este prompt corrige

O gerador original produz a página inteira numa passada, com o texto nascendo dentro do desenho. Os defeitos que isso gera — grafia variável do mesmo termo, etapa duplicada, parágrafo repetido em três lugares, palavra inexistente — só aparecem quando se olha a página como conjunto, e nessa arquitetura ninguém olha.

Aqui o texto é um objeto separado, validável e aprovável antes de existir qualquer pixel. É a mesma peça, com a revisão que faltava.
