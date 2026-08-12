"""Ações de reunião: resolução de prazo em pt-BR e checagem de realismo.

Sem LLM e sem I/O. A parte de "seja realista com os prazos" que dá para calcular
fica aqui; o que exige ler a conversa fica na skill `pontos-de-acao`.

Três coisas que um prompt não consegue garantir sozinho e este módulo garante:

1. "até sexta" vira uma data, sempre a mesma, calculada sobre a data da reunião;
2. uma ação não pode vencer antes daquela de que ela depende;
3. a mesma pessoa não pode receber 40 horas de tarefa para a semana que vem.
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

# Horas por semana que um participante consegue dedicar ao que saiu da reunião.
# Não é jornada: é o que sobra depois da operação do dia a dia numa startup.
CAPACIDADE_SEMANAL_H = 8.0

DIAS_SEMANA = {
    "segunda": 0, "segunda-feira": 0,
    "terca": 1, "terca-feira": 1,
    "quarta": 2, "quarta-feira": 2,
    "quinta": 3, "quinta-feira": 3,
    "sexta": 4, "sexta-feira": 4,
    "sabado": 5,
    "domingo": 6,
}

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}

ORIGEM_EXPLICITA = "explicita"
ORIGEM_INFERIDA = "inferida"


@dataclass
class ResultadoPrazo:
    """Data resolvida a partir de uma expressão falada."""

    data: date | None
    expressao: str
    regra: str
    confianca: float

    @property
    def texto(self) -> str:
        """Formato canônico da ata: '2026-07-18 (até sexta)'."""
        if self.data is None:
            return "[prazo não definido]"
        return f"{self.data.isoformat()} ({self.expressao.strip()})"


@dataclass
class Acao:
    """Uma ação que saiu (ou deveria sair) da reunião."""

    descricao: str
    dono: str | None = None
    origem: str = ORIGEM_EXPLICITA
    prazo: date | None = None
    prazo_expressao: str = ""
    esforco_horas: float = 0.0
    depende_de: list[str] = field(default_factory=list)
    ancora: str = ""
    id: str = ""

    def para_dict(self) -> dict:
        return {
            "id": self.id or self.descricao[:40],
            "descricao": self.descricao,
            "dono": self.dono or "[dono não definido]",
            "origem": self.origem,
            "prazo": self.prazo.isoformat() if self.prazo else None,
            "prazo_expressao": self.prazo_expressao,
            "esforco_horas": self.esforco_horas,
            "depende_de": list(self.depende_de),
            "ancora": self.ancora or "[sem âncora]",
        }


@dataclass
class Aviso:
    """Problema de realismo encontrado no conjunto de ações."""

    tipo: str
    mensagem: str
    acoes: list[str] = field(default_factory=list)


def _sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFKD", (texto or "").lower().strip())
    return "".join(c for c in base if not unicodedata.combining(c))


# --------------------------------------------------------------------------- #
# Prazo
# --------------------------------------------------------------------------- #


def _proximo_dia_semana(referencia: date, alvo: int, *, semana_seguinte: bool) -> date:
    delta = (alvo - referencia.weekday()) % 7
    if semana_seguinte:
        # "próxima sexta" nunca é a sexta desta semana.
        delta = delta + 7 if delta <= 0 else delta + 7
    return referencia + timedelta(days=delta)


def _somar_meses(referencia: date, meses: int) -> date:
    mes = referencia.month - 1 + meses
    ano = referencia.year + mes // 12
    mes = mes % 12 + 1
    dia = min(referencia.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def resolver_prazo(expressao: str, referencia: date) -> ResultadoPrazo:
    """Converte prazo falado em data absoluta, sobre a data da reunião.

    Devolve `data=None` quando a expressão não sustenta uma data — "o quanto
    antes", "assim que der". Prazo vago é informação: vira `[prazo não definido]`
    em vez de virar uma data inventada.
    """
    bruto = (expressao or "").strip()
    if not bruto:
        return ResultadoPrazo(None, bruto, "expressão vazia", 0.0)

    txt = _sem_acento(bruto)

    # Data explícita: 18/07, 18/07/2026, 2026-07-18
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", txt)
    if m:
        ano, mes, dia = (int(g) for g in m.groups())
        return ResultadoPrazo(date(ano, mes, dia), bruto, "data ISO explícita", 1.0)

    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", txt)
    if m:
        dia, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
        ano_int = referencia.year if not ano else int(ano)
        if ano_int < 100:
            ano_int += 2000
        try:
            return ResultadoPrazo(date(ano_int, mes, dia), bruto, "data explícita", 1.0)
        except ValueError:
            return ResultadoPrazo(None, bruto, "data inválida", 0.0)

    # "dia 20 de agosto" / "dia 20"
    m = re.search(r"\bdia (\d{1,2})(?: de (\w+))?", txt)
    if m:
        dia = int(m.group(1))
        nome_mes = m.group(2)
        mes = MESES.get(nome_mes or "", referencia.month)
        ano = referencia.year
        try:
            alvo = date(ano, mes, dia)
        except ValueError:
            return ResultadoPrazo(None, bruto, "dia inexistente no mês", 0.0)
        if alvo < referencia and not nome_mes:
            alvo = _somar_meses(alvo, 1)
        return ResultadoPrazo(alvo, bruto, "dia do mês", 0.9)

    if "hoje" in txt:
        return ResultadoPrazo(referencia, bruto, "hoje", 1.0)
    if "depois de amanha" in txt:
        return ResultadoPrazo(referencia + timedelta(days=2), bruto, "depois de amanhã", 1.0)
    if "amanha" in txt:
        return ResultadoPrazo(referencia + timedelta(days=1), bruto, "amanhã", 1.0)

    # "em 3 dias", "em duas semanas"
    m = re.search(r"\bem (\d+) (dias?|semanas?|meses|mes)\b", txt)
    if m:
        n, unidade = int(m.group(1)), m.group(2)
        if unidade.startswith("dia"):
            return ResultadoPrazo(referencia + timedelta(days=n), bruto, "em N dias", 0.9)
        if unidade.startswith("semana"):
            return ResultadoPrazo(
                referencia + timedelta(weeks=n), bruto, "em N semanas", 0.9
            )
        return ResultadoPrazo(_somar_meses(referencia, n), bruto, "em N meses", 0.8)

    seguinte = bool(re.search(r"\b(proxim[ao]|que vem|seguinte)\b", txt))

    if "fim do mes" in txt or "final do mes" in txt:
        ultimo = calendar.monthrange(referencia.year, referencia.month)[1]
        alvo = date(referencia.year, referencia.month, ultimo)
        if seguinte:
            alvo = _somar_meses(alvo, 1)
            ultimo = calendar.monthrange(alvo.year, alvo.month)[1]
            alvo = date(alvo.year, alvo.month, ultimo)
        return ResultadoPrazo(alvo, bruto, "fim do mês", 0.8)

    if "fim da semana" in txt or "final da semana" in txt:
        sexta = _proximo_dia_semana(referencia, 4, semana_seguinte=seguinte)
        return ResultadoPrazo(sexta, bruto, "fim da semana", 0.8)

    for nome, indice in DIAS_SEMANA.items():
        if re.search(rf"\b{nome}\b", txt):
            alvo = _proximo_dia_semana(referencia, indice, semana_seguinte=seguinte)
            return ResultadoPrazo(alvo, bruto, f"dia da semana ({nome})", 0.85)

    if "semana que vem" in txt or "proxima semana" in txt:
        return ResultadoPrazo(referencia + timedelta(weeks=1), bruto, "semana que vem", 0.7)
    if "mes que vem" in txt or "proximo mes" in txt:
        return ResultadoPrazo(_somar_meses(referencia, 1), bruto, "mês que vem", 0.7)
    if "esta semana" in txt or "essa semana" in txt:
        return ResultadoPrazo(
            _proximo_dia_semana(referencia, 4, semana_seguinte=False), bruto,
            "esta semana (assume sexta)", 0.6,
        )

    # "o quanto antes", "assim que der", "urgente" — pressão, não prazo.
    return ResultadoPrazo(None, bruto, "expressão sem data determinável", 0.0)


# --------------------------------------------------------------------------- #
# Realismo
# --------------------------------------------------------------------------- #


def dias_uteis(inicio: date, fim: date) -> int:
    """Dias úteis entre duas datas, inclusive o fim. Negativo vira zero."""
    if fim < inicio:
        return 0
    total = 0
    atual = inicio
    while atual <= fim:
        if atual.weekday() < 5:
            total += 1
        atual += timedelta(days=1)
    return total


def carga_semanal(acoes: list[Acao]) -> dict[str, dict[str, float]]:
    """Horas por dono e por semana ISO. Só conta ação com dono e prazo."""
    carga: dict[str, dict[str, float]] = {}
    for a in acoes:
        if not a.dono or a.prazo is None or not a.esforco_horas:
            continue
        ano, semana, _ = a.prazo.isocalendar()
        chave = f"{ano}-S{semana:02d}"
        carga.setdefault(a.dono, {}).setdefault(chave, 0.0)
        carga[a.dono][chave] += a.esforco_horas
    return carga


def validar_acoes(
    acoes: list[Acao],
    data_reuniao: date | None = None,
    *,
    capacidade_h: float = CAPACIDADE_SEMANAL_H,
) -> list[Aviso]:
    """Tudo que torna um plano irreal e dá para verificar por cálculo."""
    avisos: list[Aviso] = []
    por_id = {a.id or a.descricao[:40]: a for a in acoes}

    sem_dono = [a.id or a.descricao[:40] for a in acoes if not a.dono]
    if sem_dono:
        avisos.append(
            Aviso(
                "sem_dono",
                f"{len(sem_dono)} ação(ões) sem responsável definido.",
                sem_dono,
            )
        )

    sem_prazo = [a.id or a.descricao[:40] for a in acoes if a.prazo is None]
    if sem_prazo:
        avisos.append(
            Aviso("sem_prazo", f"{len(sem_prazo)} ação(ões) sem prazo.", sem_prazo)
        )

    sem_ancora = [a.id or a.descricao[:40] for a in acoes if not a.ancora]
    if sem_ancora:
        avisos.append(
            Aviso(
                "sem_ancora",
                f"{len(sem_ancora)} ação(ões) sem trecho da transcrição que as sustente.",
                sem_ancora,
            )
        )

    if data_reuniao:
        passado = [
            a.id or a.descricao[:40]
            for a in acoes
            if a.prazo is not None and a.prazo < data_reuniao
        ]
        if passado:
            avisos.append(
                Aviso("prazo_no_passado", "Prazo anterior à data da reunião.", passado)
            )

    for a in acoes:
        for dep_id in a.depende_de:
            dep = por_id.get(dep_id)
            if dep is None:
                avisos.append(
                    Aviso(
                        "dependencia_inexistente",
                        f"Depende de '{dep_id}', que não está na lista.",
                        [a.id or a.descricao[:40]],
                    )
                )
                continue
            if a.prazo and dep.prazo and dep.prazo > a.prazo:
                avisos.append(
                    Aviso(
                        "dependencia_invertida",
                        f"Vence em {a.prazo} mas depende de '{dep_id}', "
                        f"que só vence em {dep.prazo}.",
                        [a.id or a.descricao[:40], dep_id],
                    )
                )

    for dono, semanas in carga_semanal(acoes).items():
        for semana, horas in sorted(semanas.items()):
            if horas > capacidade_h:
                ids = [
                    a.id or a.descricao[:40]
                    for a in acoes
                    if a.dono == dono
                    and a.prazo
                    and f"{a.prazo.isocalendar()[0]}-S{a.prazo.isocalendar()[1]:02d}" == semana
                ]
                avisos.append(
                    Aviso(
                        "sobrecarga",
                        f"{dono} acumula {horas:.0f}h na semana {semana}, "
                        f"acima da capacidade de {capacidade_h:.0f}h.",
                        ids,
                    )
                )

    return avisos


def relatorio_realismo(
    acoes: list[Acao],
    data_reuniao: date | None = None,
    *,
    capacidade_h: float = CAPACIDADE_SEMANAL_H,
) -> str:
    """Avisos em Markdown, prontos para a seção 'Onde o plano aperta'."""
    avisos = validar_acoes(acoes, data_reuniao, capacidade_h=capacidade_h)
    if not avisos:
        return "Nenhum problema de prazo, dependência ou carga detectado."
    linhas = []
    for av in avisos:
        alvo = ", ".join(av.acoes[:4])
        sufixo = f" — {alvo}" if alvo else ""
        linhas.append(f"- **{av.tipo}**: {av.mensagem}{sufixo}")
    return "\n".join(linhas)
