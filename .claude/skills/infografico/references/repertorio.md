# Repertório — o que copiar e o que evitar

Calibragem da skill, extraída de três posters gerados por ferramenta automática (Gemini Notebook) a partir de especificações de software. Os assuntos não importam; o que importa são os **padrões** — os mesmos aparecem em poster de relatório, de estudo ou de plano.

---

## Dispositivos que funcionam

**Papel declarado na coluna.** Cada coluna de um poster de pipeline trazia, sob a rubrica, o papel entre parênteses: *(o início)*, *(o como)*, *(o que entrega)*, *(por que serve)*. O leitor sabe por que a coluna existe antes de ler o conteúdo. É o achado mais forte dos três e virou campo obrigatório de `colunas-narrativas`.

**Faixa de fechamento respondendo "por que confiar".** Um dos posters termina com três provas de robustez em vez de mais features. Sem essa faixa, um poster de produto vira folheto. Virou obrigatória em `fluxo`.

**Título bicolor.** Nome do sujeito num acento, promessa no tom neutro. Dá identidade sem depender de logotipo.

**Uma tabela técnica, num canto.** Stack, parâmetros e variáveis concentrados num bloco só, longe do conteúdo de negócio. Espalhar tecnologia pela página inteira mistura dois públicos.

**Hero com metáfora de transformação.** Insumo entra de um lado, entregável sai do outro. Resolve em uma figura o que o texto levaria um parágrafo para dizer.

---

## Defeitos, e a regra que cada um gerou

**O mesmo termo com três grafias na mesma página.** Um algoritmo de recuperação aparecia corretamente numa legenda, virava outra sigla numa tabela e uma terceira num diagrama — três formas, uma peça. → **glossário travado na Rodada 1**; a Rodada 2 só escreve o que está nele.

**Etapa numerada duas vezes.** Um poster publicou duas "Jornada 5", uma delas com nome inventado, e a numeração deixou de ser confiável para o leitor. → **checagem de unicidade e sequência** antes de mostrar o roteiro.

**Parágrafo repetido em três blocos.** A mesma frase sobre exportação ocupava três lugares diferentes, consumindo cerca de um terço da área útil. → **proibição de repetição**, inclusive parafraseada.

**Erro de digitação em quase todo bloco.** "análiza", "classificatrão", "extracção", "at é 21 secções", "liata de tarefas", "ponfos cegos", "Consoiliação das rtapas". → **texto congelado e revisado antes do desenho**, mais leitura integral do Artifact caçando erro.

**Nome de dependência escrito errado na tabela técnica.** Um framework de UI apareceu com uma letra trocada — justamente no bloco em que o leitor técnico confia. → nome próprio **entra no glossário** como qualquer sigla.

**Mistura de idiomas e de norma.** Termo em inglês no meio de frase em português; acento de português europeu num documento pt-BR. → `idioma` declarado no roteiro; siglas consagradas preservadas, o resto na norma do documento.

**Sigla consagrada corrompida.** Um método de análise clássico teve uma letra trocada e virou palavra inexistente — o tipo de erro que destrói a credibilidade da peça inteira em quem conhece o assunto. → siglas **sempre** no glossário.

**Logotipos de terceiros colados.** Marcas de produtos externos reproduzidas dentro da peça. Informam o mesmo que uma etiqueta escrita e imitam marca alheia. → **etiqueta com o nome**, nunca o logo.

**Dois ou três eixos numa peça só.** Um poster respondia ao mesmo tempo "o que isto entrega", "com o que é feito" e "como se instala": personas de marketing convivendo com variáveis de ambiente. Cada leitor descarta metade da página. → **um eixo por poster**, declarado e aprovado.

---

## O padrão por trás de todos

Nenhum dos três erra no **desenho** — erram no **texto**, e sempre da mesma forma: o texto foi composto durante o render, uma vez por bloco, sem revisão e sem comparação entre blocos. Daí termo com grafia variável, etapa duplicada e frase repetida: são defeitos que só aparecem quando se olha a página como conjunto, e ninguém olhou.

É o que as duas rodadas resolvem. Na Rodada 1 o texto é escrito uma vez, validado como conjunto e aprovado por uma pessoa. Na Rodada 2 ele só é posicionado.
