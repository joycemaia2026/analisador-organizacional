# Gramática visual

Consumido pela **Rodada 2**. A Rodada 1 usa daqui apenas os vocabulários de `cor` e `icone`.

## Tema

O poster commete-se a **uma** aparência: é feito para exportar, colar em slide e imprimir. Pinte `background` e `color` explicitamente no container raiz — sem isso o artefato herda o fundo do hospedeiro e se desmonta no tema escuro do leitor. Não implemente variante alternativa.

### `tema: claro`

Página clara, painéis um tom mais escuros. Material comercial, executivo ou destinado a impressão.

```css
--page: #eef2f7;  --panel: #e4e9f0;  --card: #ffffff;
--ink:  #1a1a1b;  --ink-muted: #4a4a4a;  --line: #dde3ec;
--title: var(--ink);
```

### `tema: escuro`

**Página escura com painéis claros** — não é a paleta clara invertida. Título e rubricas de faixa em branco sobre o fundo; dentro do painel, tinta escura sobre claro. Material técnico, de engenharia ou de dados.

```css
--page: #0f1c2e;  --panel: #eef2f7;  --card: #ffffff;
--ink:  #1a1a1b;  --ink-muted: #4a4a4a;  --line: #cfd7e3;
--title: #ffffff; --page-line: #2d3a4d;
```

Comum aos dois: `--radius: 14px`, `--radius-sm: 10px`, `--shadow: 0 2px 16px rgba(26,35,50,.07)`, `--font: "Montserrat", system-ui, sans-serif` (troque a família se a fonte declarar outra).

## Vocabulário de cor (campo `cor`)

Paleta neutra padrão. Seis acentos, todos com contraste verificado sobre `--panel` e sobre `--card`.

| Nome | Hex | Texto sobre ele | Papel típico |
|------|-----|-----------------|--------------|
| `verde` | `#00a859` | branco | entrega, resultado, positivo |
| `azul` | `#3b82f6` | branco | entrada, coleta, fluxo de dados |
| `teal` | `#14b8a6` | `#1a1a1b` | consolidação, síntese |
| `ambar` | `#f59e0b` | `#1a1a1b` | atenção, decisão, etapa humana |
| `coral` | `#f87171` | `#1a1a1b` | risco, restrição, alerta |
| `marinho` | `#1e3a5f` | branco | infraestrutura, base técnica |

**Substituição por marca:** quando o passo 5 da Rodada 1 encontrou identidade, troque **o hex** de `marca.primaria` (e da secundária) pelo da marca, mantendo o nome no vocabulário e o par de contraste. Não acrescente um sétimo acento para acomodar a marca.

**Ritmo:** no máximo 4 acentos por poster; nunca dois blocos vizinhos com o mesmo acento dominante. Em `colunas-narrativas`, uma cor por coluna, herdada pelos blocos filhos. Em `comparativo`, uma cor por alternativa.

## Vocabulário de metáfora (campo `metafora`)

Dezesseis nomes, **idênticos ao dicionário `METAFORAS` de `core/prompt_infografico.py`** — o mesmo roteiro alimenta o render HTML e o caminho de imagem, então o vocabulário é um só. Nome novo entra editando os dois lugares, nunca por improviso no render.

SVG inline de traço, `stroke-width: 2`, `viewBox="0 0 24 24"`, centrado em disco de 44px na cor do bloco.

| Metáfora | Desenho | Significa |
|----------|---------|-----------|
| `funil` | funil circular | seleção, classificação |
| `cilindro` | cilindros empilhados | persistência, banco |
| `chip` | hexágono com nós | processamento, IA |
| `esteira` | esteira transportadora | pipeline, sequência |
| `grafo` | nós conectados | rede, base de conhecimento |
| `regua` | régua com marcos | histórico, linha do tempo |
| `documento` | folha com linhas | registro, relatório |
| `pessoa` | silhueta em círculo | persona, papel |
| `escudo` | escudo com cadeado | segurança, garantia |
| `alvo` | alvo com flecha | objetivo, foco |
| `grafico` | barras ascendentes | métrica, resultado |
| `engrenagem` | engrenagem | operação, automação |
| `globo` | globo com meridianos | fonte pública, web |
| `nuvem` | nuvem | serviço externo, hospedagem |
| `chave` | chave | credencial, acesso |
| `balanca` | balança de dois pratos | comparação, decisão |

Conceito fora da lista? Use o mais próximo.

## Tipografia

| Papel | Tamanho | Peso | Caixa |
|-------|---------|------|-------|
| `titulo_marca` | 40px (clamp 26–40) | 800 | normal, no acento primário |
| `titulo_frase` | 40px (clamp 26–40) | 800 | normal, `--title` |
| `subtitulo` | 17px | 500 | normal, `--ink-muted` |
| `rubrica` | 17px em `colunas-narrativas`, 15px nos demais | 700 | CAIXA ALTA, exceto em `colunas-narrativas` |
| `papel` | 15px | 500 | normal, `--ink-muted`, entre parênteses, linha abaixo da rubrica |
| `numero` | igual à rubrica | 800 | prefixo `1.` colado na rubrica |
| `rotulo` | 13px | 700 | CAIXA ALTA |
| `texto` | 13px | 400 | normal, `line-height: 1.45` |
| `bullet` | 12px | 400 | marcador `•`, recuo 14px |
| `rodape` | 11px | 400 | `--ink-muted` |

Uma família só. Hierarquia sai de peso e caixa, nunca de fonte nova. O título aceita duas cores: `titulo_marca` no acento primário, `titulo_frase` em `--title`, separados por dois-pontos e espaço.

---

## Arquétipos

### `paineis`

Grade de 12 colunas, `max-width: 1600px`, `padding: 32px`, `gap: 20px`.

| `regiao` | span |
|----------|------|
| `esquerda` | 3 |
| `centro` | 3 (é sempre o `hero`) |
| `direita` | subgrade de 6 colunas; blocos dividem a linha ou ocupam a faixa |
| `rodape` | 5 ou 7 |

### `colunas-narrativas`

3–4 colunas de largura igual, cada uma um painel `--panel` de altura total, `gap: 18px`. Dentro: cabeçalho (`numero` + `rubrica`, `papel` na linha de baixo), depois os blocos empilhados com `gap: 22px`, na ordem do roteiro.

Seta vertical entre blocos consecutivos da mesma coluna: 2px, `--line`, ponta de 8px, altura de 16px, centrada. Sem setas entre colunas — a leitura lateral já é implícita. Em tela estreita as colunas empilham inteiras, preservando a numeração.

### `fluxo`

Quatro faixas horizontais na ordem `entrada` · `processo` · `saidas` · `valor`.

- `entrada` — itens `lista-icone` em linha, centralizados; conector descendo para o processo.
- `processo` — etapas numeradas em linha (duas linhas se forem 5). Colchete SVG agrupando etapas que a fonte trata como bloco; seta entre etapas consecutivas.
- `saidas` — mesmo tratamento da entrada.
- `valor` — 3 blocos lado a lado, ícone de 72px, rótulo e um parágrafo. É a faixa que responde "por que confiar nisto"; sem ela o poster vira lista de features.

### `comparativo`

Matriz. Cabeçalho com uma coluna por alternativa, cada uma com sua cor e rótulo; primeira coluna reservada aos critérios. Linhas alternadas, `--card` na ímpar. Célula vencedora em cada critério recebe `check`; célula eliminatória recebe `x` em `coral`. Abaixo da matriz, faixa de veredito em painel `--panel`, um parágrafo, sem cor de acento.

Nunca ordene as alternativas por preferência sem que o documento o faça — a ordem da matriz é lida como ranking.

Conectores (em qualquer arquétipo): ortogonais, 2px, ponta simples, `--line` no tema claro e `--page-line` no escuro. **Linhas não se cruzam** — se cruzarem, a ordem dos blocos está errada; reordene em vez de desviar o traço.

---

## Anatomia dos blocos

Painel: fundo `--panel`, `border-radius: var(--radius)`, `padding: 20px`.

- **`hero`** — sem fundo de painel. Figura SVG de 200–260px, frase abaixo, centralizada, largura máxima 320px.
- **`lista-icone`** — disco de 44px + rótulo abaixo, em coluna.
- **`pilulas`** — retângulos empilhados, fundo na cor do item, `--radius-sm`, rótulo em caixa alta e complemento entre parênteses embaixo.
- **`avatares`** — círculo de 88px com silhueta, rótulo em caixa alta, texto em 3–4 linhas, distribuídos em linha.
- **`chips`** — etiqueta colorida com o rótulo em caixa alta e o texto em cartão `--card` abaixo; larguras iguais.
- **`bullets`** — sem marcador; rótulo em negrito, dois-pontos, continuação no mesmo parágrafo.
- **`etapa`** — número em disco de 28px na cor da coluna, rótulo ao lado, texto abaixo, bullets ao final.
- **`criterio`** — linha da matriz: rótulo do critério à esquerda, uma célula por alternativa.
- **`tabela`** — cabeçalho na cor primária com texto branco, linhas alternadas, borda `--line`, 12px. Rola dentro do próprio container (`overflow-x: auto`), nunca a página.
- **`valor`** — ícone de 72px centralizado, rótulo em negrito, parágrafo de até 3 linhas.

**Organizações e produtos de terceiros:** etiqueta retangular com o nome escrito, fundo `--card`, borda `--line`, 12px, peso 600. Nunca desenhe o logotipo alheio.

## Espaço em branco

Bloco colado na borda parece erro de exportação. `gap` de 20px entre painéis, 16px entre itens, 22px entre blocos de uma coluna narrativa. Página apertada é excesso de conteúdo: volte à Rodada 1 e corte um bloco. Não reduza o respiro.
