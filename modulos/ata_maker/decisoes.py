"""Registro de decisões com o critério que as sustentou.

Sem LLM e sem I/O.

Uma decisão sem o critério registrado não pode ser revisitada: seis meses depois
ninguém lembra por que a escolha foi feita, e a discussão recomeça do zero. Este
módulo trata "critério não declarado" como um achado a reportar, não como um campo
opcional que se preenche com uma justificativa plausível.

A distinção porta-de-ida / porta-de-volta vem de decisão de produto: escolha
reversível pode ser tomada rápido e corrigida; irreversível sem critério declarado
é o pior caso, e sai no topo dos avisos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SEM_CRITERIO = "critério não declarado na reunião"
SEM_RESPONSAVEL = "[quem decidiu não identificado]"

REVERSIVEL = "reversivel"
IRREVERSIVEL = "irreversivel"
INDEFINIDO = "indefinido"

TIPOS = (REVERSIVEL, IRREVERSIVEL, INDEFINIDO)


@dataclass
class Decisao:
    """Algo que a reunião definiu, com o porquê quando houve porquê."""

    enunciado: str
    criterio: str = SEM_CRITERIO
    alternativas_descartadas: list[str] = field(default_factory=list)
    sustentada_por: str | None = None
    ancora: str = ""
    tipo: str = INDEFINIDO
    id: str = ""

    @property
    def identificador(self) -> str:
        return self.id or self.enunciado[:40]

    @property
    def tem_criterio(self) -> bool:
        return bool(self.criterio) and self.criterio != SEM_CRITERIO

    def para_dict(self) -> dict:
        return {
            "id": self.identificador,
            "enunciado": self.enunciado,
            "criterio": self.criterio or SEM_CRITERIO,
            "alternativas_descartadas": list(self.alternativas_descartadas),
            "sustentada_por": self.sustentada_por or SEM_RESPONSAVEL,
            "ancora": self.ancora or "[sem âncora]",
            "tipo": self.tipo if self.tipo in TIPOS else INDEFINIDO,
        }


@dataclass
class AvisoDecisao:
    tipo: str
    mensagem: str
    decisoes: list[str] = field(default_factory=list)
    gravidade: str = "media"


def validar_decisoes(decisoes: list[Decisao]) -> list[AvisoDecisao]:
    """O que compromete a rastreabilidade das decisões. Ordenado por gravidade."""
    avisos: list[AvisoDecisao] = []

    irreversiveis_sem_criterio = [
        d.identificador
        for d in decisoes
        if d.tipo == IRREVERSIVEL and not d.tem_criterio
    ]
    if irreversiveis_sem_criterio:
        avisos.append(
            AvisoDecisao(
                "irreversivel_sem_criterio",
                "Decisão difícil de desfazer, tomada sem critério declarado.",
                irreversiveis_sem_criterio,
                gravidade="alta",
            )
        )

    sem_criterio = [
        d.identificador
        for d in decisoes
        if not d.tem_criterio and d.tipo != IRREVERSIVEL
    ]
    if sem_criterio:
        avisos.append(
            AvisoDecisao(
                "sem_criterio",
                "Decisão sem o porquê registrado — não dá para revisitar depois.",
                sem_criterio,
            )
        )

    sem_ancora = [d.identificador for d in decisoes if not d.ancora]
    if sem_ancora:
        avisos.append(
            AvisoDecisao(
                "sem_ancora",
                "Decisão sem trecho da transcrição que a sustente.",
                sem_ancora,
                gravidade="alta",
            )
        )

    sem_responsavel = [d.identificador for d in decisoes if not d.sustentada_por]
    if sem_responsavel:
        avisos.append(
            AvisoDecisao(
                "sem_responsavel",
                "Não ficou registrado quem sustentou a decisão.",
                sem_responsavel,
            )
        )

    indefinidas = [d.identificador for d in decisoes if d.tipo == INDEFINIDO]
    if indefinidas:
        avisos.append(
            AvisoDecisao(
                "reversibilidade_indefinida",
                "Não foi avaliado se a decisão é fácil ou difícil de desfazer.",
                indefinidas,
                gravidade="baixa",
            )
        )

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    avisos.sort(key=lambda a: ordem.get(a.gravidade, 3))
    return avisos


def decisoes_para_markdown(decisoes: list[Decisao]) -> str:
    """Uma decisão por bloco, com o critério logo abaixo do enunciado."""
    if not decisoes:
        return "Nenhuma decisão formalizada nesta reunião."

    linhas: list[str] = []
    for d in decisoes:
        rotulo = {
            REVERSIVEL: "fácil de desfazer",
            IRREVERSIVEL: "difícil de desfazer",
            INDEFINIDO: "reversibilidade não avaliada",
        }[d.tipo if d.tipo in TIPOS else INDEFINIDO]

        linhas.append(f"**{d.enunciado}** — {d.ancora or '[sem âncora]'}")
        linhas.append(f"- Critério: {d.criterio or SEM_CRITERIO}")
        if d.alternativas_descartadas:
            linhas.append(
                "- Alternativas descartadas: "
                + "; ".join(d.alternativas_descartadas)
            )
        linhas.append(f"- Sustentada por: {d.sustentada_por or SEM_RESPONSAVEL}")
        linhas.append(f"- Natureza: {rotulo}")
        linhas.append("")
    return "\n".join(linhas).strip()


def relatorio_decisoes(decisoes: list[Decisao]) -> str:
    """Avisos em Markdown para a seção 'O que não ficou registrado'."""
    avisos = validar_decisoes(decisoes)
    if not avisos:
        return "Todas as decisões têm critério, âncora e responsável registrados."
    linhas = []
    for av in avisos:
        alvo = ", ".join(av.decisoes[:4])
        linhas.append(f"- **{av.tipo}** ({av.gravidade}): {av.mensagem} — {alvo}")
    return "\n".join(linhas)
