---
name: briefboard-transcricao
description: Normaliza a transcrição bruta de uma reunião — segmenta turnos, preserva os timestamps como âncora, corrige nomes próprios errados do ASR e atribui falantes com base em evidência. É a primeira skill de qualquer análise de reunião no BriefBoard; as demais assumem a saída dela. Use quando chegar uma transcrição nova em `transcrições/`, antes de gerar ata, extrair decisões ou auditar rastreabilidade.
license: MIT
compatibility: Claude Code, Codex, Cursor, Gemini CLI e demais agentes compatíveis com Agent Skills.
metadata:
  author: joyce
  version: "1.0.0"
  framework: briefboard
  ordem: 1
  entrada: transcrições/*.txt (ASR bruto)
  saida: outputs/analise_texto/<stem>/transcricao_normalizada.{json,md}
---

Você prepara a matéria-prima de todas as outras análises de reunião. Uma transcrição
mal normalizada envenena tudo que vem depois: decisão atribuída à pessoa errada,
prazo colado no turno errado, afirmação sem trecho que a sustente.

Seu trabalho é **metade determinística, metade julgamento**. A parte determinística
já existe em `modulos/ata_maker/normalizacao.py` — não a reimplemente em prosa.
A sua parte é resolver o que a regra deixou ambíguo, lendo a conversa.

## Antes de começar

1. Identifique o arquivo de transcrição. Se o usuário não indicou, liste `transcrições/`
   e pergunte — não escolha por ele.
2. Levante os **nomes conhecidos**: `perfis/perfis.json` (campo `nome`) mais os nomes
   citados na própria reunião. Sem essa lista a atribuição não roda: nomes só saem de
   um cadastro ou da fala, nunca da sua imaginação.
3. Confirme que existe `outputs/analise_texto/<stem>/` — crie se faltar. `<stem>` é o
   nome do arquivo sem extensão.

## Processo

### 1. Primeira passada determinística

```python
from modulos.ata_maker.normalizacao import normalizar_transcricao
resultado = normalizar_transcricao(texto, nomes_conhecidos)
```

Devolve: `metadados` (título, data e fuso da reunião), `formato_detectado`
(`seta` / `nomeado` / `corrido`), `turnos` com âncora e falante, `correcoes_asr`
(já aplicadas), `sugestoes_asr` e `sugestoes_falante`.

Confira dois números antes de seguir: `total_turnos` maior que zero e
`formato_detectado` compatível com o que você vê no arquivo. Se der `corrido` num
arquivo que claramente tem turnos, o parser não reconheceu a marca — reporte, não
contorne com gambiarra no prompt.

### 2. Resolver os apelidos (julgamento)

`sugestoes_asr` traz o que a regra não ousa aplicar sozinha: apelidos e primeiros
nomes truncados (`Cris` → `Cristian`, `Lind` → `Lindia`, `Cristiá` → `Cristian`).

Para cada um, decida lendo o contexto — a mesma pessoa aparece como apelido e como
nome completo na conversa? o apelido é usado em vocativo dirigido a alguém que fala?
Confirme só o que a conversa sustenta. **Não confirme** um apelido que possa ser uma
segunda pessoa (dois "Gabriel" na sala é caso real deste projeto).

Rode a segunda passada com o mapa confirmado:

```python
resultado = normalizar_transcricao(texto, nomes_conhecidos, apelidos={"Cris": "Cristian"})
```

### 3. Resolver falantes ambíguos (julgamento)

A heurística determinística só atribui com evidência forte:

| Evidência | Score | Significado |
|---|---|---|
| Nome explícito na transcrição | 1.0 | `Nome: fala` |
| Auto-apresentação | 0.95 | "aqui é o Cristian" |
| Vocativo abrindo o turno seguinte | 0.7 | "Perfeito, Cris." → o turno anterior é do Cristian |
| Vocativo no próprio turno | — | evidência **negativa**: quem chama não é o chamado |

Abaixo de `0.6` o turno fica `[não identificado]`, e isso é o comportamento correto.

Você pode elevar uma atribuição usando o que a regra não lê: continuidade de assunto
entre turnos do mesmo participante, papel funcional ("eu cuido do suporte" casado com
o cargo em `perfis/perfis.json`), referência cruzada ("como o Rogério falou agora há
pouco"). Ao fazer isso, registre o motivo e o trecho — atribuição sem justificativa
escrita não entra.

**Não feche a lacuna a qualquer custo.** É esperado que boa parte dos turnos de uma
gravação de Meet fique sem dono. Uma transcrição com 70% de `[não identificado]` e
30% de atribuições sustentadas vale mais que 100% de chutes.

### 4. Marcar o que é fala, não decisão

Ao anotar os turnos, classifique o que for usado depois como
**fato / opinião / decisão / pendência / intenção vaga**.

Português falado engana: "a gente precisa mudar bastante a nossa forma de trabalho"
é intenção vaga, não decisão — não tem dono, prazo nem objeto. "Vou abrir o ticket
hoje" é pendência com dono. Essa distinção é o que impede a ata de inventar decisões.

### 5. Converter prazos relativos

Use `metadados.data_reuniao` como referência para transformar "semana que vem",
"até sexta", "depois do carnaval" em data absoluta. Registre sempre **as duas**: a
expressão original e a data calculada. Se a reunião não tiver data no cabeçalho,
pergunte — não estime.

## Saída

Em `outputs/analise_texto/<stem>/`:

- **`transcricao_normalizada.json`** — o dict de `normalizar_transcricao`, acrescido
  das suas resoluções. Cada turno: `indice`, `ancora`, `inicio_seg`, `falante`,
  `origem_falante` (`explicito` | `sugerido` | `inferido` | `desconhecido`),
  `confianca`, `motivo` (quando `inferido`), `texto`.
- **`transcricao_normalizada.md`** — legível, via `turnos_para_markdown`, no formato
  `**[t=mm:ss] Falante:** texto`. É esta a entrada das skills seguintes.
- **`normalizacao_relatorio.md`** — o que você decidiu e por quê: apelidos confirmados
  e recusados, correções de ASR aplicadas, falantes inferidos com o trecho que
  sustenta cada um, e a lista do que ficou sem dono.

Nunca escreva em `transcrições/` — o original é a fonte de verdade.

## Checkpoint

Reporte ao usuário, curto:

- formato detectado, total de turnos, quantos com falante e quantos sem
- correções de ASR aplicadas (as 5 mais frequentes)
- apelidos que você confirmou e os que recusou, com o motivo
- o que precisa de confirmação humana antes das próximas skills rodarem

## Verificação

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.test_normalizacao
```

Rode sempre que mexer em `modulos/ata_maker/normalizacao.py`. Para inspecionar uma
transcrição nova antes de confiar nela:

```bash
cd /home/joyce/projetos/briefboard && .venv/bin/python -m tests.validar_transcricao_real "transcrições/arquivo.txt"
```
