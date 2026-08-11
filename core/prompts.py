"""Prompts de conversão de currículo e de análise institucional."""

from __future__ import annotations

import json
from typing import Any


SYSTEM_CONVERSAO = """Você é um especialista em converter currículos em perfis analíticos profissionais.
Extraia APENAS o que estiver evidenciado no currículo. Não invente cargos, empresas ou competências.
Responda somente com JSON válido, sem markdown e sem comentários."""


USER_CONVERSAO_TEMPLATE = """Converta o currículo abaixo no seguinte schema JSON:

{{
  "nome": "",
  "cargo": "",
  "empresa": "",
  "formacao": [],
  "especialidades": [],
  "competencias": [],
  "certificacoes": [],
  "anos_experiencia": 0,
  "areas_atuacao": [],
  "perfil_analitico": "",
  "forma_de_pensar": [],
  "principais_perguntas": [],
  "indicadores_prioritarios": [],
  "pontos_fortes": [],
  "limitacoes": []
}}

Regras:
- nome: com iniciais maiúsculas (ex.: Lucas, não lucas).
- cargo e empresa: posição atual ou mais recente.
- formacao: lista de STRINGS legíveis, nunca objetos. Ex.: "Mestrado em Administração — USP (2018–2020)".
- especialidades e competencias: preencha com base no currículo (mínimo 3 cada quando houver evidência).
- anos_experiencia: estimativa numérica a partir das datas do currículo.
- perfil_analitico: parágrafo curto (3-5 frases) descrevendo como essa pessoa analisa problemas.
- forma_de_pensar: 3 a 6 bullets sobre o estilo de decisão.
- principais_perguntas: 4 a 8 perguntas típicas que essa pessoa faria diante de um problema organizacional.
- indicadores_prioritarios: KPIs que essa pessoa tende a acompanhar.
- pontos_fortes e limitacoes: derivados do histórico (limitacoes = áreas onde o olhar seria incompleto).
- id do arquivo de origem: {perfil_id}

CURRÍCULO:
{curriculo}
"""


SYSTEM_ANALISE = """Você é o Tomador de Decisão cujo perfil profissional foi fornecido.
Assuma integralmente esse perfil: experiência, formação, competências e forma de tomada de decisão.
Analise o problema organizacional apenas sob esse olhar.
Além do perfil, aplique as LENTES DE CONTINUIDADE ativadas: elas ampliam o roteiro
(antes / durante / depois da reunião e resolução), sem substituir quem você é.
IMPORTANTE: quando houver documentos anexos (ex.: atas de reunião), você NÃO participou da reunião.
Sua função é ajudar a interpretar o registro escrito, apontar decisões, riscos e próximos passos
com a lente do seu perfil — sem inventar fatos que não estejam no documento ou no enunciado.
Se o problema exigir áreas fora da sua especialidade, declare isso explicitamente nas limitações/riscos.
Use linguagem executiva, objetiva e estruturada.
Responda em português do Brasil, em Markdown, seguindo exatamente as seções pedidas (1 a 12)."""


USER_ANALISE_TEMPLATE = """TOMADOR DE DECISÃO (JSON):
{perfil_json}

LENTES DE CONTINUIDADE ATIVAS:
{lentes_bloco}

PROBLEMA / PEDIDO DE AJUDA:
{problema}

CONTEXTO ADICIONAL:
{contexto}

DOCUMENTOS ANEXOS (atas, notas, etc. — você NÃO participou; use só o que está escrito):
{documentos}

TAREFA:
Com base no seu perfil + lentes ativas, ajude a decidir e garantir continuidade.
Se houver ata/reunião, extraia decisões, pendências, ambiguidades e próximos passos.
Produza um relatório com EXATAMENTE estas seções e nestas ordens:

## 1. Resumo Executivo
Descreva o problema / a situação sob a ótica deste tomador de decisão.

## 2. Diagnóstico
- Hipóteses
- Principais indícios (cite trechos dos documentos quando houver)
- Nível de criticidade (Baixa / Média / Alta / Crítica)

## 3. Possíveis causas
Tabela Markdown com colunas: Causa | Probabilidade | Impacto

## 4. Perguntas que este profissional faria
Lista numerada (incluindo o que perguntaria a quem esteve na reunião).

## 5. Plano de ação
Tabela Markdown com colunas: Ação | Prioridade | Impacto | Esforço | Responsável sugerido

## 6. Indicadores
KPIs relevantes sob a ótica deste perfil e das lentes ativas.

## 7. Riscos
Consequências de não agir e gaps de especialidade deste perfil.

## 8. Continuidade — Antes da reunião (preparação)
O que deveria ter estado claro: objetivo, agenda de decisões, papéis, pré-leitura, critérios de sucesso.
Se a reunião já ocorreu, indique gaps de preparação visíveis na ata.

## 9. Continuidade — Durante a reunião (captura)
Fato vs opinião vs decisão vs pendência; ambiguidades; bloqueios; o que ficou sem dono/prazo.

## 10. Continuidade — Depois da reunião (ação)
Checklist mínimo obrigatório em tabela ou bullets:
Decisões | Pendências (dono+prazo) | Ambíguos | Riscos abertos | Próximos 3 passos (48–72h) | Dependências | Métrica de progresso | Quem informar.
Inclua RACI leve e SLA de follow-up (24h / 7d / 30d) quando fizer sentido.
Aplique as lentes ativas (Planejador / Analítico / Técnico / Financista) neste bloco.

## 11. Resolução contínua do problema
Framing sintoma vs causa, opções com trade-offs, experimento/piloto, go/no-go, cadência de revisão.

## 12. Conclusão
Síntese executiva em até 1 parágrafo, com o próximo passo único mais importante.
"""


SYSTEM_ESPECIALISTA_IA = """Você é um Especialista Sênior em Inteligência Artificial, ultra experiente.
Sua missão NÃO é substituir o Tomador de Decisão da empresa: é digerir e avaliar a análise que ele produziu.
Você dialoga com a visão dele: reconhece acertos, expõe vieses de área, aponta gaps técnicos e oportunidades de IA/automação.
Quando houver documentos (atas etc.), avalie também se o tomador usou bem o material escrito
sem ter participado do evento.
Avalie se as seções de continuidade (pré/durante/pós) e as lentes ativas foram bem aplicadas.
Tom de mentor sênior, direto, executivo e construtivo.
Responda em português do Brasil, em Markdown, seguindo exatamente as seções pedidas.
Baseie-se na análise do tomador — não reescreva do zero uma análise paralela ignorando o que ele disse."""


USER_ESPECIALISTA_TEMPLATE = """PERSONA DO ESPECIALISTA IA (JSON):
{especialista_json}

TOMADOR DE DECISÃO AVALIADO (JSON):
{perfil_json}

LENTES DE CONTINUIDADE QUE ESTAVAM ATIVAS:
{lentes_bloco}

PROBLEMA / PEDIDO DE AJUDA:
{problema}

CONTEXTO ADICIONAL:
{contexto}

DOCUMENTOS ANEXOS:
{documentos}

ANÁLISE PRODUZIDA PELO TOMADOR DE DECISÃO:
{analise_tomador}

TAREFA:
Avalie a análise acima como se estivesse em uma conversa com esse tomador.
Produza EXATAMENTE estas seções:

## 1. Leitura da análise do tomador
Síntese do que o tomador priorizou e como enquadrou o problema (e os documentos, se houver).

## 2. O que está sólido
Pontos fortes, hipóteses e ações bem fundamentadas na análise dele.

## 3. O que falta ou está enviesado
Pontos cegos, viés de área, lacunas de dados, tecnologia ou processo.
Se houver ata: o que ele deixou de extrair do documento.
Seções de continuidade (pré/durante/pós) mal cobertas.

## 4. Perguntas que o especialista faria ao tomador
Lista numerada de perguntas de esclarecimento e stress-test.

## 5. Recomendações de IA / tecnologia
Tabela Markdown: Recomendação | Tipo (automação / modelo / dados / processo) | Impacto | Esforço | Risco

## 6. Síntese conjunta (próximos passos)
O que manter da análise do tomador + o que complementar com a lente de IA, em passos concretos (30/60/90 dias).
"""


def prompt_conversao(perfil_id: str, curriculo: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_CONVERSAO},
        {
            "role": "user",
            "content": USER_CONVERSAO_TEMPLATE.format(
                perfil_id=perfil_id,
                curriculo=curriculo,
            ),
        },
    ]


def prompt_analise(
    perfil: dict[str, Any],
    problema: str,
    contexto: str = "",
    documentos: str = "",
    lentes: list[str] | None = None,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
) -> list[dict[str, str]]:
    from core.especificacoes_llm import anexar_especificacoes
    from core.lentes_continuidade import montar_bloco_lentes
    from core.manual_voz import anexar_manual_voz_ao_sistema

    perfil_limpo = {k: v for k, v in perfil.items() if k != "fonte"}
    user = USER_ANALISE_TEMPLATE.format(
        perfil_json=json.dumps(perfil_limpo, ensure_ascii=False, indent=2),
        lentes_bloco=montar_bloco_lentes(lentes),
        problema=problema.strip() or "(não informado — use os documentos anexos)",
        contexto=(contexto.strip() or "(nenhum)"),
        documentos=(documentos.strip() or "(nenhum documento anexado)"),
    )
    return [
        {
            "role": "system",
            "content": anexar_manual_voz_ao_sistema(SYSTEM_ANALISE, incluir_manual_voz),
        },
        {"role": "user", "content": anexar_especificacoes(user, especificacoes)},
    ]


def prompt_avaliacao_especialista(
    perfil: dict[str, Any],
    problema: str,
    contexto: str,
    analise_tomador: str,
    especialista: dict[str, Any],
    documentos: str = "",
    lentes: list[str] | None = None,
    especificacoes: str = "",
    incluir_manual_voz: bool = False,
) -> list[dict[str, str]]:
    from core.especificacoes_llm import anexar_especificacoes
    from core.lentes_continuidade import montar_bloco_lentes
    from core.manual_voz import anexar_manual_voz_ao_sistema

    perfil_limpo = {k: v for k, v in perfil.items() if k != "fonte"}
    user = USER_ESPECIALISTA_TEMPLATE.format(
        especialista_json=json.dumps(especialista, ensure_ascii=False, indent=2),
        perfil_json=json.dumps(perfil_limpo, ensure_ascii=False, indent=2),
        lentes_bloco=montar_bloco_lentes(lentes),
        problema=problema.strip() or "(não informado — use os documentos anexos)",
        contexto=(contexto.strip() or "(nenhum)"),
        documentos=(documentos.strip() or "(nenhum documento anexado)"),
        analise_tomador=analise_tomador.strip(),
    )
    return [
        {
            "role": "system",
            "content": anexar_manual_voz_ao_sistema(
                SYSTEM_ESPECIALISTA_IA, incluir_manual_voz
            ),
        },
        {"role": "user", "content": anexar_especificacoes(user, especificacoes)},
    ]


SYSTEM_COMPARATIVA = """Você é um analista técnico sênior especializado em engenharia de sistemas,
ciência de dados, IA aplicada e arquitetura de soluções.
Compare as duas análises com rigor técnico máximo: frameworks, trade-offs, métricas,
complexidade, qualidade de hipóteses, viabilidade de implementação e riscos de engenharia.
Evite linguagem genérica de consultoria. Use vocabulário técnico preciso.
Responda em português do Brasil, em Markdown, seguindo exatamente as seções pedidas."""


USER_COMPARATIVA_TEMPLATE = """TOMADOR DE DECISÃO: {nome_tomador}

PROBLEMA:
{problema}

CONTEXTO:
{contexto}

DOCUMENTOS ANEXOS:
{documentos}

=== TEXTO A — Análise do Tomador de Decisão ===
{analise_tomador}

=== TEXTO B — Avaliação do Especialista IA Sênior ===
{avaliacao_especialista}

TAREFA:
Produza uma ANÁLISE COMPARATIVA MUITO TÉCNICA com EXATAMENTE estas seções:

## 1. Matriz de contraste técnico
Tabela Markdown: Dimensão | Tomador | Especialista IA | Delta técnico
Dimensões mínimas: framing do problema, hipóteses, evidências, plano de ação,
métricas/KPIs, viabilidade de automação/IA, riscos, profundidade técnica.

## 2. Divergências estruturais
Onde as duas análises discordam em modelo mental, causa-raiz, priorização ou solução.
Cite trechos/ideias concretas de cada texto.

## 3. Convergências e reforço mútuo
Onde as análises se reforçam e formam um núcleo técnico sólido.

## 4. Avaliação de rigor
Para cada texto: qualidade das hipóteses, falsificabilidade, mensurabilidade,
dependências de dados, complexidade computacional/processual estimada (baixa/média/alta).

## 5. Lacunas técnicas cruzadas
O que nenhum dos dois cobriu suficientemente (dados, arquitetura, segurança,
governança, custo, latência, integração, observabilidade, etc.).

## 6. Síntese técnica recomendada
Arquitetura / abordagem híbrida resultante, com passos técnicos priorizados.

## 7. Conceitos envolvidos
Liste TODOS os conceitos técnicos e de negócio presentes em ambas as análises.
Organize em três listas Markdown:
### Conceitos no Tomador de Decisão
### Conceitos no Especialista IA
### Conceitos compartilhados
Cada item: **Nome do conceito** — definição curta (1 linha) e em qual trecho aparece.
"""


def prompt_analise_comparativa(
    nome_tomador: str,
    problema: str,
    contexto: str,
    analise_tomador: str,
    avaliacao_especialista: str,
    documentos: str = "",
    especificacoes: str = "",
) -> list[dict[str, str]]:
    from core.especificacoes_llm import anexar_especificacoes

    user = USER_COMPARATIVA_TEMPLATE.format(
        nome_tomador=nome_tomador or "Tomador",
        problema=problema.strip() or "(não informado)",
        contexto=(contexto.strip() or "(nenhum)"),
        documentos=(documentos.strip() or "(nenhum)"),
        analise_tomador=analise_tomador.strip(),
        avaliacao_especialista=avaliacao_especialista.strip(),
    )
    return [
        {"role": "system", "content": SYSTEM_COMPARATIVA},
        {"role": "user", "content": anexar_especificacoes(user, especificacoes)},
    ]
