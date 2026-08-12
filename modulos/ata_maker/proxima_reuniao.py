"""Pauta da próxima reunião: itens com tempo, e quem precisa estar.

Sem LLM e sem I/O.

Duas checagens que evitam a pauta impossível:

1. **Soma dos tempos.** Nove assuntos numa reunião de 30 minutos não é uma pauta,
   é uma lista de desejos. O módulo compara a soma com a duração prevista e cobra
   folga — reunião cheia até o último minuto atrasa a seguinte.
2. **Participante necessário.** Quem foi citado repetidamente e não estava na
   reunião é candidato objetivo para a próxima, e isso sai do próprio artefato
   processado, não de suposição.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from modulos.ata_maker.acoes import resolver_prazo

# Follow-up de pendências não precisa de uma hora. Ajuste ao marcar a reunião.
DURACAO_PADRAO_MIN = 30

# Fração da reunião que a pauta pode ocupar. O resto é abertura, atraso e fecho.
OCUPACAO_MAXIMA = 0.8

ORIGEM_PERGUNTA = "pergunta_aberta"
ORIGEM_ADIADO = "assunto_adiado"
ORIGEM_PENDENCIA = "pendencia"
ORIGEM_SEM_CRITERIO = "decisao_sem_criterio"

ORIGENS = (ORIGEM_PERGUNTA, ORIGEM_ADIADO, ORIGEM_PENDENCIA, ORIGEM_SEM_CRITERIO)

ROTULO_ORIGEM = {
    ORIGEM_PERGUNTA: "pergunta em aberto",
    ORIGEM_ADIADO: "assunto adiado",
    ORIGEM_PENDENCIA: "pendência",
    ORIGEM_SEM_CRITERIO: "decisão sem critério registrado",
}


@dataclass
class ItemPauta:
    """Um assunto da próxima reunião, com o que precisa sair dele."""

    assunto: str
    objetivo: str = ""
    dono: str | None = None
    minutos: int = 0
    origem: str = ORIGEM_PENDENCIA
    ancora: str = ""
    material: str = ""

    @property
    def identificador(self) -> str:
        return self.assunto[:40]

    def para_dict(self) -> dict:
        return {
            "assunto": self.assunto,
            "objetivo": self.objetivo or "[objetivo não definido]",
            "dono": self.dono or "[dono não definido]",
            "minutos": self.minutos,
            "origem": self.origem if self.origem in ORIGENS else ORIGEM_PENDENCIA,
            "ancora": self.ancora or "[sem âncora]",
            "material": self.material or "nenhum",
        }


@dataclass
class Participante:
    nome: str
    motivo: str
    obrigatorio: bool = True


@dataclass
class AvisoPauta:
    tipo: str
    mensagem: str
    itens: list[str] = field(default_factory=list)


def sugerir_participantes(
    donos_de_itens: list[str] | None = None,
    citados_ausentes: list[str] | None = None,
    presentes: list[str] | None = None,
) -> list[Participante]:
    """Quem precisa estar, com o motivo. Nada aqui é palpite.

    - Dono de item da pauta é obrigatório: sem ele o assunto não anda.
    - Quem foi citado e não estava é sugerido, não obrigatório — a decisão de
      chamar alguém é de quem convoca.
    """
    sugeridos: dict[str, Participante] = {}

    for dono in donos_de_itens or []:
        if not dono or dono.startswith("["):
            continue
        sugeridos[dono] = Participante(dono, "responsável por item da pauta", True)

    ja_presentes = {p for p in (presentes or [])}
    for nome in citados_ausentes or []:
        if not nome or nome in sugeridos or nome in ja_presentes:
            continue
        sugeridos[nome] = Participante(
            nome, "citado na reunião anterior sem estar presente", False
        )

    return sorted(sugeridos.values(), key=lambda p: (not p.obrigatorio, p.nome))


def tempo_total(itens: list[ItemPauta]) -> int:
    return sum(max(0, i.minutos) for i in itens)


def validar_pauta(
    itens: list[ItemPauta],
    *,
    duracao_min: int = DURACAO_PADRAO_MIN,
    ocupacao_maxima: float = OCUPACAO_MAXIMA,
) -> list[AvisoPauta]:
    """O que torna a pauta impraticável."""
    avisos: list[AvisoPauta] = []

    if not itens:
        return [AvisoPauta("pauta_vazia", "Nenhum assunto para a próxima reunião.")]

    sem_objetivo = [i.identificador for i in itens if not i.objetivo.strip()]
    if sem_objetivo:
        avisos.append(
            AvisoPauta(
                "sem_objetivo",
                "Assunto sem dizer o que precisa sair dele — vira conversa aberta.",
                sem_objetivo,
            )
        )

    sem_dono = [i.identificador for i in itens if not i.dono]
    if sem_dono:
        avisos.append(
            AvisoPauta("sem_dono", "Assunto sem quem conduz.", sem_dono)
        )

    sem_tempo = [i.identificador for i in itens if i.minutos <= 0]
    if sem_tempo:
        avisos.append(
            AvisoPauta("sem_tempo", "Assunto sem tempo estimado.", sem_tempo)
        )

    total = tempo_total(itens)
    teto = int(duracao_min * ocupacao_maxima)
    if total > teto:
        avisos.append(
            AvisoPauta(
                "pauta_estourada",
                f"A pauta soma {total} min para uma reunião de {duracao_min} min "
                f"(teto útil: {teto} min). Corte assunto ou aumente a reunião.",
                [i.identificador for i in itens],
            )
        )

    return avisos


def resolver_data(expressao: str, data_reuniao: date) -> dict:
    """Data da próxima reunião a partir do que foi combinado na fala."""
    r = resolver_prazo(expressao, data_reuniao)
    return {
        "data": r.data.isoformat() if r.data else None,
        "texto": r.texto if r.data else "[data não combinada]",
        "expressao": r.expressao,
        "regra": r.regra,
        "confianca": r.confianca,
    }


def pauta_para_markdown(
    itens: list[ItemPauta],
    participantes: list[Participante] | None = None,
    *,
    data_texto: str = "[data não combinada]",
    duracao_min: int = DURACAO_PADRAO_MIN,
) -> str:
    """Pauta pronta para colar no convite."""
    linhas = [
        f"**Data:** {data_texto} · **Duração prevista:** {duracao_min} min "
        f"· **Pauta:** {tempo_total(itens)} min",
        "",
    ]

    if participantes:
        obrigatorios = [p for p in participantes if p.obrigatorio]
        sugeridos = [p for p in participantes if not p.obrigatorio]
        linhas.append("**Quem precisa estar**")
        for p in obrigatorios:
            linhas.append(f"- {p.nome} — {p.motivo}")
        if sugeridos:
            linhas.append("")
            linhas.append("**Sugeridos (decisão de quem convoca)**")
            for p in sugeridos:
                linhas.append(f"- {p.nome} — {p.motivo}")
        linhas.append("")

    if not itens:
        linhas.append("_Nenhum assunto pendente para a próxima reunião._")
        return "\n".join(linhas)

    linhas.append("| Assunto | O que precisa sair | Conduz | Min | Origem |")
    linhas.append("|---|---|---|---|---|")
    for i in itens:
        d = i.para_dict()
        linhas.append(
            f"| {d['assunto']} | {d['objetivo']} | {d['dono']} | "
            f"{d['minutos']} | {ROTULO_ORIGEM.get(d['origem'], d['origem'])} |"
        )

    materiais = [i for i in itens if i.material and i.material != "nenhum"]
    if materiais:
        linhas.extend(["", "**Materiais a preparar antes**"])
        for i in materiais:
            linhas.append(f"- {i.material} — {i.dono or '[dono não definido]'}")

    return "\n".join(linhas)


def relatorio_pauta(
    itens: list[ItemPauta],
    *,
    duracao_min: int = DURACAO_PADRAO_MIN,
) -> str:
    avisos = validar_pauta(itens, duracao_min=duracao_min)
    if not avisos:
        return "Pauta cabe no tempo, com dono e objetivo em cada assunto."
    return "\n".join(
        f"- **{a.tipo}**: {a.mensagem}"
        + (f" — {', '.join(a.itens[:4])}" if a.itens else "")
        for a in avisos
    )
