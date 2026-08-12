"""Normalização determinística de transcrição de reunião (sem LLM, sem I/O).

Transcrições de ASR (Meet, Zoom, Teams) chegam em três formatos no projeto:

1. Turnos marcados por ``>>`` sem nome, com timestamps em linha própria — é o caso
   real de ``transcrições/VLI - Alinhamento interno - 2026071.txt``.
2. Turnos nomeados no padrão ``Nome: fala`` — o único que ``nlp.py`` cobria.
3. Texto corrido só com timestamps, sem marca de turno.

Este módulo segmenta os três, **preserva** os timestamps (que
``nlp.preprocess_transcript`` descarta) para servirem de âncora ``[t=mm:ss]``, e
sugere falantes por evidência linguística. Sugestão abaixo do limiar não vira
atribuição: o falante fica desconhecido em vez de chutado.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Abaixo deste score a sugestão é reportada mas não aplicada.
LIMIAR_ATRIBUICAO = 0.6

# Similaridade mínima para corrigir automaticamente um nome próprio errado do ASR.
LIMIAR_ASR = 0.80

FALANTE_DESCONHECIDO = "[não identificado]"

# Léxico do projeto que o ASR costuma escrever errado.
LEXICO_PADRAO = ("VLI", "Gedanken", "BriefBoard", "NotebookLM")

_RE_TS_SOZINHO = re.compile(r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*$")
_RE_TS_PREFIXO = re.compile(r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s+(\S.*)$")
_RE_TURNO_SETA = re.compile(r"^\s*>>+\s*(.*)$")
_RE_TURNO_NOMEADO = re.compile(r"^\s*([A-ZÀ-Ý][\wÀ-ÿ .'-]{1,40}?)\s*:\s+(\S.*)$")
_RE_CABECALHO_DATA = re.compile(
    r"(\d{4})[/-](\d{2})[/-](\d{2})[ T]+(\d{1,2}:\d{2})(?:\s*(GMT[+-]\d{2}:?\d{2}))?"
)

# Palavras que abrem um vocativo: "Perfeito, Cris.", "Desculpa, Rogério."
_ABERTURAS_VOCATIVO = {
    "perfeito", "isso", "exato", "obrigado", "obrigada", "desculpa", "desculpe",
    "valeu", "bom", "boa", "ótimo", "otimo", "certo", "beleza", "concordo",
    "olha", "oi", "opa", "gente", "pois", "então", "entao", "tá", "ta", "sim",
    "não", "nao", "legal", "show", "fechado", "verdade", "claro",
}

# Frases de auto-apresentação: "aqui é o Cristian", "quem fala é a Mônica".
_RE_AUTO_APRESENTACAO = re.compile(
    r"\b(?:aqui (?:é|e|quem fala é) (?:o |a )?|quem fala é (?:o |a )?|"
    r"(?:é|e) (?:o |a )?\w+ falando|meu nome é (?:o |a )?)([A-ZÀ-Ý][\wÀ-ÿ]{2,20})",
    re.IGNORECASE,
)


@dataclass
class Turno:
    """Um bloco contíguo de fala de um mesmo participante."""

    indice: int
    texto: str
    inicio_seg: int | None = None
    falante: str | None = None
    # "explicito" (veio nomeado na transcrição) | "sugerido" | "desconhecido"
    origem_falante: str = "desconhecido"
    confianca: float = 0.0

    @property
    def ancora(self) -> str:
        return formatar_ancora(self.inicio_seg)

    def para_dict(self) -> dict:
        return {
            "indice": self.indice,
            "ancora": self.ancora,
            "inicio_seg": self.inicio_seg,
            "falante": self.falante or FALANTE_DESCONHECIDO,
            "origem_falante": self.origem_falante,
            "confianca": round(self.confianca, 2),
            "texto": self.texto,
        }


@dataclass
class Sugestao:
    """Evidência de que um turno pertence a um falante — ainda não aplicada."""

    indice_turno: int
    falante: str
    score: float
    motivo: str
    trecho: str


@dataclass
class Correcao:
    """Nome próprio reescrito pelo dicionário de ASR."""

    original: str
    corrigido: str
    similaridade: float
    ocorrencias: int


@dataclass
class ResultadoCorrecao:
    texto: str
    correcoes: list[Correcao] = field(default_factory=list)
    # Casos que exigem julgamento (apelido, primeiro nome de nome composto).
    sugestoes: list[Correcao] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Timestamps
# --------------------------------------------------------------------------- #


def ts_para_segundos(ts: str) -> int | None:
    """'12:34' → 754; '1:02:33' → 3753."""
    partes = (ts or "").strip().split(":")
    if not all(p.isdigit() for p in partes):
        return None
    if len(partes) == 2:
        m, s = (int(p) for p in partes)
        return m * 60 + s
    if len(partes) == 3:
        h, m, s = (int(p) for p in partes)
        return h * 3600 + m * 60 + s
    return None


def formatar_ancora(segundos: int | None) -> str:
    """Formato canônico da âncora usada pelas skills: 'mm:ss' ou 'h:mm:ss'."""
    if segundos is None:
        return "??:??"
    horas, resto = divmod(int(segundos), 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{seg:02d}"
    return f"{minutos}:{seg:02d}"


def extrair_metadados_cabecalho(texto: str) -> dict:
    """Título, data e fuso da primeira linha, quando a gravação os traz.

    Ex.: 'VLI - Alinhamento interno - 2026/07/15 09:00 GMT-03:00 - Recording'
    A data serve para converter prazos relativos ('até sexta') em data absoluta.
    """
    primeira = next((l.strip() for l in (texto or "").splitlines() if l.strip()), "")
    meta: dict = {"titulo": primeira or None, "data_reuniao": None, "fuso": None}
    m = _RE_CABECALHO_DATA.search(primeira)
    if m:
        ano, mes, dia, hora, fuso = m.groups()
        meta["data_reuniao"] = f"{ano}-{mes}-{dia}T{hora}"
        meta["fuso"] = fuso
    return meta


# --------------------------------------------------------------------------- #
# Segmentação em turnos
# --------------------------------------------------------------------------- #


def detectar_formato(texto: str) -> str:
    """'seta' | 'nomeado' | 'corrido' — qual marca de turno domina o texto."""
    setas = 0
    nomeados = 0
    for linha in (texto or "").splitlines():
        if _RE_TURNO_SETA.match(linha):
            setas += 1
        elif _nome_de_turno(linha):
            nomeados += 1
    if setas >= nomeados and setas > 0:
        return "seta"
    if nomeados > 0:
        return "nomeado"
    return "corrido"


def _nome_de_turno(linha: str) -> str | None:
    """Nome do falante se a linha for do tipo 'Nome: fala', senão None."""
    m = _RE_TURNO_NOMEADO.match(linha)
    if not m:
        return None
    nome = m.group(1).strip()
    if len(nome.split()) > 5:
        return None
    if nome.lower() in {"http", "https", "www", "timestamp", "speaker", "obs", "nota"}:
        return None
    return nome


def segmentar_turnos(texto: str) -> list[Turno]:
    """Quebra a transcrição em turnos, preservando o timestamp de início de cada um.

    Reconhece os três formatos do projeto. No formato 'corrido' (sem marca de
    turno), cada bloco de timestamp vira um turno — a granularidade da âncora é
    preservada mesmo sem saber quem falou.
    """
    if not (texto or "").strip():
        return []

    formato = detectar_formato(texto)
    turnos: list[Turno] = []
    ts_pendente: int | None = None
    atual: Turno | None = None

    def abrir(texto_inicial: str, falante: str | None) -> None:
        nonlocal atual, ts_pendente
        fechar()
        atual = Turno(
            indice=len(turnos),
            texto=texto_inicial.strip(),
            inicio_seg=ts_pendente,
            falante=falante,
            origem_falante="explicito" if falante else "desconhecido",
            confianca=1.0 if falante else 0.0,
        )
        ts_pendente = None

    def fechar() -> None:
        nonlocal atual
        if atual is not None and atual.texto.strip():
            atual.texto = re.sub(r"\s+", " ", atual.texto).strip()
            turnos.append(atual)
        atual = None

    for linha in texto.splitlines():
        if not linha.strip():
            continue

        m_ts = _RE_TS_SOZINHO.match(linha)
        if m_ts:
            segundos = ts_para_segundos(m_ts.group(1))
            if formato == "corrido":
                # Sem marca de turno, o próprio timestamp delimita o bloco.
                ts_pendente = segundos
                abrir("", None)
            elif atual is None or atual.inicio_seg is None:
                ts_pendente = segundos
                if atual is not None:
                    atual.inicio_seg = segundos
            else:
                ts_pendente = segundos
            continue

        m_seta = _RE_TURNO_SETA.match(linha)
        if m_seta:
            abrir(m_seta.group(1), None)
            continue

        nome = _nome_de_turno(linha)
        if nome and formato == "nomeado":
            resto = _RE_TURNO_NOMEADO.match(linha).group(2)
            abrir(resto, nome)
            continue

        m_pref = _RE_TS_PREFIXO.match(linha)
        if m_pref:
            segundos = ts_para_segundos(m_pref.group(1))
            corpo = m_pref.group(2)
            if atual is None:
                ts_pendente = segundos
                abrir(corpo, None)
            else:
                if atual.inicio_seg is None:
                    atual.inicio_seg = segundos
                atual.texto = f"{atual.texto} {corpo}"
            continue

        if atual is None:
            # Linha antes de qualquer marca de turno (cabeçalho da gravação).
            if turnos or _RE_CABECALHO_DATA.search(linha):
                continue
            abrir(linha, None)
        else:
            atual.texto = f"{atual.texto} {linha.strip()}"

    fechar()
    for i, t in enumerate(turnos):
        t.indice = i
    return turnos


# --------------------------------------------------------------------------- #
# Atribuição de falantes
# --------------------------------------------------------------------------- #


def _sem_acento(palavra: str) -> str:
    base = unicodedata.normalize("NFKD", (palavra or "").lower().strip())
    return "".join(c for c in base if not unicodedata.combining(c))


def _vocativos(
    texto: str,
    nomes: list[str],
    ignorar_spans: list[tuple[int, int]] | None = None,
) -> list[tuple[str, bool, str]]:
    """Nomes chamados no texto. Retorna (nome, é_na_primeira_frase, trecho).

    Um vocativo é evidência **negativa** forte para o turno onde aparece (ninguém
    chama a si mesmo) e evidência **positiva** para o turno anterior quando abre a
    fala: 'Perfeito, Cris.' responde a quem acabou de falar.

    `ignorar_spans` exclui trechos que só *parecem* vocativo: em 'aqui é o
    Cristian, ...' a vírgula depois do nome não faz dele um chamamento.
    """
    achados: list[tuple[str, bool, str]] = []
    if not texto:
        return achados
    ignorar = ignorar_spans or []
    primeira_frase = re.split(r"(?<=[.!?])\s", texto, maxsplit=1)[0]

    # Índice por forma sem acento: o ASR escreve 'Mônica' e o cadastro, 'Monica'.
    por_forma: dict[str, str] = {}
    for nome in nomes:
        por_forma.setdefault(_sem_acento(nome.split()[0]), nome)
        por_forma.setdefault(_sem_acento(nome), nome)

    for m in re.finditer(r"[\wÀ-ÿ]+", texto):
        nome = por_forma.get(_sem_acento(m.group(0)))
        if not nome:
            continue
        if any(ini <= m.start() < fim for ini, fim in ignorar):
            continue
        antes = texto[max(0, m.start() - 40) : m.start()]
        depois = texto[m.end() : m.end() + 2]
        # Vocativo verdadeiro tem vírgula antes ou pontuação logo depois.
        pontuado = bool(re.search(r"[,:;]\s*$", antes)) or depois.strip()[:1] in {
            ",", ".", "!", "?",
        }
        if not pontuado:
            continue
        achados.append(
            (
                nome,
                m.start() < len(primeira_frase),
                texto[max(0, m.start() - 30) : m.end() + 20].strip(),
            )
        )
    return achados


def sugerir_falantes(
    turnos: list[Turno], nomes_conhecidos: list[str]
) -> list[Sugestao]:
    """Evidências de autoria por turno, ordenadas por score. Não altera os turnos.

    Só considera nomes da lista `nomes_conhecidos` — nunca inventa participante a
    partir de uma palavra capitalizada solta no meio do texto.
    """
    nomes = [n for n in (nomes_conhecidos or []) if n and n.strip()]
    if not nomes or not turnos:
        return []

    sugestoes: list[Sugestao] = []
    excluidos: dict[int, set[str]] = {t.indice: set() for t in turnos}

    for turno in turnos:
        if turno.origem_falante == "explicito":
            continue

        # Auto-apresentação é a evidência mais forte que existe.
        spans_auto: list[tuple[int, int]] = []
        for m in _RE_AUTO_APRESENTACAO.finditer(turno.texto):
            candidato = _casar_nome(m.group(1), nomes)
            if candidato:
                spans_auto.append(m.span())
                sugestoes.append(
                    Sugestao(
                        indice_turno=turno.indice,
                        falante=candidato,
                        score=0.95,
                        motivo="auto-apresentação",
                        trecho=m.group(0),
                    )
                )

        for nome, na_abertura, trecho in _vocativos(turno.texto, nomes, spans_auto):
            # Quem é chamado não é quem fala.
            excluidos[turno.indice].add(nome)
            if na_abertura and turno.indice > 0:
                anterior = turnos[turno.indice - 1]
                if anterior.origem_falante == "explicito":
                    continue
                sugestoes.append(
                    Sugestao(
                        indice_turno=anterior.indice,
                        falante=nome,
                        score=0.7,
                        motivo="vocativo de resposta no turno seguinte",
                        trecho=trecho,
                    )
                )

    # Uma sugestão contradita por vocativo no próprio turno é descartada.
    validas = [s for s in sugestoes if s.falante not in excluidos.get(s.indice_turno, set())]
    validas.sort(key=lambda s: (-s.score, s.indice_turno))
    return validas


def _casar_nome(bruto: str, nomes: list[str]) -> str | None:
    alvo = _sem_acento(bruto)
    for nome in nomes:
        if _sem_acento(nome.split()[0]) == alvo or _sem_acento(nome) == alvo:
            return nome
    return None


def aplicar_sugestoes(
    turnos: list[Turno],
    sugestoes: list[Sugestao],
    *,
    limiar: float = LIMIAR_ATRIBUICAO,
) -> list[Turno]:
    """Grava no turno apenas a melhor sugestão que passe do limiar.

    Turno sem sugestão suficiente permanece desconhecido — de propósito. Chutar o
    dono de uma pendência é pior que registrar que o dono não foi identificado.
    """
    melhor: dict[int, Sugestao] = {}
    for s in sugestoes:
        if s.score < limiar:
            continue
        atual = melhor.get(s.indice_turno)
        if atual is None or s.score > atual.score:
            melhor[s.indice_turno] = s

    for turno in turnos:
        if turno.origem_falante == "explicito":
            continue
        s = melhor.get(turno.indice)
        if s is None:
            continue
        turno.falante = s.falante
        turno.origem_falante = "sugerido"
        turno.confianca = s.score
    return turnos


# --------------------------------------------------------------------------- #
# Correção de nomes próprios do ASR
# --------------------------------------------------------------------------- #


def _similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, _sem_acento(a), _sem_acento(b)).ratio()


def corrigir_nomes_asr(
    texto: str,
    nomes_conhecidos: list[str],
    *,
    lexico: tuple[str, ...] = LEXICO_PADRAO,
    apelidos: dict[str, str] | None = None,
) -> ResultadoCorrecao:
    """Reescreve nomes próprios que o ASR errou ('Veli' → 'VLI').

    Só corrige quando a evidência é folgada: mesma inicial, tamanho parecido e
    similaridade acima de `LIMIAR_ASR`. Casos de apelido ou primeiro nome de nome
    composto ('Cris' → 'Cristian') saem em `sugestoes`, não aplicados — decidir
    isso exige contexto da conversa, não regra.

    `apelidos` é o retorno dessa decisão: o mapa que a skill confirmou é aplicado
    na segunda passada, e aí 'Perfeito, Cris.' passa a valer como vocativo.
    """
    alvos = [n for n in list(nomes_conhecidos or []) + list(lexico) if n and n.strip()]
    if not (texto or "").strip() or not alvos:
        return ResultadoCorrecao(texto=texto or "")

    conhecidos_norm = {_sem_acento(a) for a in alvos}
    for alvo in alvos:
        conhecidos_norm.add(_sem_acento(alvo.split()[0]))

    candidatos: dict[str, int] = {}
    for token in re.findall(r"\b[A-ZÀ-Ý][\wÀ-ÿ]{2,20}\b", texto):
        if _sem_acento(token) in conhecidos_norm:
            continue
        candidatos[token] = candidatos.get(token, 0) + 1

    correcoes: list[Correcao] = []
    sugestoes: list[Correcao] = []
    substituicoes: dict[str, str] = {}

    # Apelidos já confirmados pela skill entram como correção, não como sugestão.
    confirmados = {k: v for k, v in (apelidos or {}).items() if k and v}
    for apelido, completo in confirmados.items():
        ocorrencias = candidatos.pop(apelido, 0)
        if not ocorrencias:
            continue
        substituicoes[apelido] = completo
        correcoes.append(
            Correcao(apelido, completo, round(_similaridade(apelido, completo), 3), ocorrencias)
        )

    for token, ocorrencias in candidatos.items():
        melhor_alvo = None
        melhor_score = 0.0
        for alvo in alvos:
            for forma in {alvo, alvo.split()[0]}:
                score = _similaridade(token, forma)
                if score > melhor_score:
                    melhor_score, melhor_alvo = score, forma
        if not melhor_alvo:
            continue

        t_norm, a_norm = _sem_acento(token), _sem_acento(melhor_alvo)
        if t_norm and a_norm and a_norm.startswith(t_norm):
            # Apelido / abreviação: decisão de contexto, não de regra.
            sugestoes.append(Correcao(token, melhor_alvo, round(melhor_score, 3), ocorrencias))
            continue

        mesma_inicial = t_norm[:1] == a_norm[:1]
        tamanho_ok = abs(len(t_norm) - len(a_norm)) <= 3
        if melhor_score >= LIMIAR_ASR and mesma_inicial and tamanho_ok:
            substituicoes[token] = melhor_alvo
            correcoes.append(Correcao(token, melhor_alvo, round(melhor_score, 3), ocorrencias))

    novo = texto
    for errado, certo in substituicoes.items():
        novo = re.sub(rf"(?<![\wÀ-ÿ]){re.escape(errado)}(?![\wÀ-ÿ])", certo, novo)

    correcoes.sort(key=lambda c: -c.ocorrencias)
    sugestoes.sort(key=lambda c: -c.ocorrencias)
    return ResultadoCorrecao(texto=novo, correcoes=correcoes, sugestoes=sugestoes)


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #


def normalizar_transcricao(
    texto: str,
    nomes_conhecidos: list[str] | None = None,
    *,
    apelidos: dict[str, str] | None = None,
) -> dict:
    """Pipeline determinístico completo. É o que a skill chama antes de julgar.

    Roda duas vezes: a primeira sem `apelidos`, para a skill ler `sugestoes_asr` e
    decidir; a segunda com o mapa confirmado, que melhora a atribuição de falantes.
    """
    nomes = list(nomes_conhecidos or [])
    correcao = corrigir_nomes_asr(texto, nomes, apelidos=apelidos)
    turnos = segmentar_turnos(correcao.texto)
    sugestoes = sugerir_falantes(turnos, nomes)
    aplicar_sugestoes(turnos, sugestoes)

    return {
        "metadados": extrair_metadados_cabecalho(texto),
        "formato_detectado": detectar_formato(texto),
        "turnos": [t.para_dict() for t in turnos],
        "total_turnos": len(turnos),
        "turnos_sem_falante": sum(1 for t in turnos if not t.falante),
        "correcoes_asr": [vars(c) for c in correcao.correcoes],
        "sugestoes_asr": [vars(c) for c in correcao.sugestoes],
        "sugestoes_falante": [vars(s) for s in sugestoes],
    }


def turnos_para_markdown(turnos: list[Turno]) -> str:
    """Transcrição legível com âncora e falante — entrada das skills 2 a 5."""
    linhas: list[str] = []
    for t in turnos:
        falante = t.falante or FALANTE_DESCONHECIDO
        marca = "" if t.origem_falante == "explicito" else f" ~{t.confianca:.2f}"
        linhas.append(f"**[t={t.ancora}] {falante}{marca}:** {t.texto}")
    return "\n\n".join(linhas)


def blocos_de_tempo(turnos: list[Turno], *, minutos: int = 10) -> list[dict]:
    """Agrupa os turnos em janelas de tempo.

    Serve para ancorar "temas discutidos" em trechos reais da reunião: cada tema
    aponta para uma janela, em vez de flutuar sobre o texto inteiro. Turno sem
    timestamp cai na janela do turno anterior.
    """
    if not turnos:
        return []

    janela = max(1, minutos) * 60
    blocos: list[dict] = []
    atual_seg = 0
    for turno in turnos:
        if turno.inicio_seg is not None:
            atual_seg = turno.inicio_seg
        indice = atual_seg // janela
        if not blocos or blocos[-1]["indice"] != indice:
            blocos.append(
                {
                    "indice": indice,
                    "inicio_seg": indice * janela,
                    "inicio": formatar_ancora(indice * janela),
                    "fim": formatar_ancora((indice + 1) * janela),
                    "turnos": [],
                    "falantes": [],
                }
            )
        blocos[-1]["turnos"].append(turno.indice)
        if turno.falante and turno.falante not in blocos[-1]["falantes"]:
            blocos[-1]["falantes"].append(turno.falante)

    for bloco in blocos:
        bloco["total_turnos"] = len(bloco["turnos"])
    return blocos


def resumo_estrutural(turnos: list[Turno], nomes_conhecidos: list[str] | None = None) -> dict:
    """Fatos do cabeçalho de uma ata — todos derivados, nenhum inferido.

    `duracao_seg` é o início do último turno, não o fim da reunião: a transcrição
    não diz quando a última fala terminou. Por isso o rótulo é "pelo menos".
    """
    if not turnos:
        return {
            "duracao_seg": None,
            "duracao_texto": "não determinada",
            "participantes": [],
            "citados_sem_falar": [],
            "total_turnos": 0,
            "turnos_sem_falante": 0,
        }

    participantes = [f["falante"] for f in contar_falas(turnos)]

    # Quem aparece na fala mas nunca falou: esteve na pauta, não na reunião.
    citados: list[str] = []
    if nomes_conhecidos:
        corpo = " ".join(t.texto for t in turnos)
        presentes = {_sem_acento(p) for p in participantes}
        for nome in nomes_conhecidos:
            primeiro = nome.split()[0]
            if _sem_acento(nome) in presentes or _sem_acento(primeiro) in presentes:
                continue
            padrao = rf"(?<![\wÀ-ÿ]){re.escape(primeiro)}(?![\wÀ-ÿ])"
            if re.search(padrao, corpo, flags=re.IGNORECASE) and nome not in citados:
                citados.append(nome)

    ultimo = max((t.inicio_seg for t in turnos if t.inicio_seg is not None), default=None)
    return {
        "duracao_seg": ultimo,
        "duracao_texto": (
            f"pelo menos {formatar_ancora(ultimo)}" if ultimo else "não determinada"
        ),
        "participantes": participantes,
        "citados_sem_falar": citados,
        "total_turnos": len(turnos),
        "turnos_sem_falante": sum(1 for t in turnos if not t.falante),
    }


def bloco_fatos_reuniao(texto: str, nomes_conhecidos: list[str] | None = None) -> str:
    """Cabeçalho factual pronto para injetar num prompt de ata.

    Existe para que o modelo **não precise inventar** data, duração ou lista de
    participantes: ele recebe o que foi medido e o que ficou indeterminado.

    Corrige os nomes do ASR antes de medir. Sem isso o cabeçalho diverge do resto:
    o vocativo 'Linda,' não casaria com a 'Lindia' do cadastro e ela sumiria da
    lista de participantes.
    """
    nomes = list(nomes_conhecidos or [])
    corrigido = corrigir_nomes_asr(texto, nomes).texto
    turnos = segmentar_turnos(corrigido)
    aplicar_sugestoes(turnos, sugerir_falantes(turnos, nomes))
    meta = extrair_metadados_cabecalho(texto)
    resumo = resumo_estrutural(turnos, nomes)

    participantes = ", ".join(resumo["participantes"]) or "nenhum identificado"
    citados = ", ".join(resumo["citados_sem_falar"]) or "nenhum"
    return "\n".join(
        [
            f"- Título da gravação: {meta['titulo'] or 'não informado'}",
            f"- Data/hora: {meta['data_reuniao'] or 'não informada'}"
            + (f" ({meta['fuso']})" if meta["fuso"] else ""),
            f"- Duração: {resumo['duracao_texto']}",
            f"- Turnos de fala: {resumo['total_turnos']} "
            f"({resumo['turnos_sem_falante']} sem falante identificado)",
            f"- Participantes identificados: {participantes}",
            f"- Citados que não falaram: {citados}",
        ]
    )


def contar_falas(turnos: list[Turno]) -> list[dict]:
    """Contagem por falante, no formato que `nlp.py` já publica na ata."""
    contagem: dict[str, int] = {}
    for t in turnos:
        if not t.falante:
            continue
        contagem[t.falante] = contagem.get(t.falante, 0) + 1
    ordenado = sorted(contagem.items(), key=lambda kv: -kv[1])
    return [{"falante": nome, "falas": n} for nome, n in ordenado[:12]]
