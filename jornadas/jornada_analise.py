"""Jornada 2 — Análise Organizacional (Tomador + Especialista + lentes)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.analisador import analisar_problema, avaliar_com_especialista_ia, salvar_analises
from core.documentos import (
    TIPOS_UPLOAD,
    DocumentoEntrada,
    anexar_documento_sessao,
    extrair_texto_arquivo,
    montar_bloco_documentos,
)
from core.especialista_ia import ESPECIALISTA_IA, nome_especialista
from core.leitor_perfis import (
    adicionar_novas_personas,
    atualizar_personas_da_pasta,
    carregar_ou_converter_perfis,
    listar_curriculos_existentes,
    listar_novos_curriculos,
)
from core.lentes_continuidade import (
    DEFAULT_LENTES,
    LENTES,
    normalizar_lentes,
    rotulo_lente,
)
from core.openai_client import get_api_key
from core.utils import PESSOAS_DIR
from jornadas.comum import lista_bullets, render_cabecalho


@st.cache_data(show_spinner=False)
def _carregar_perfis_cached(force_flag: int) -> list[dict]:
    _ = force_flag
    return carregar_ou_converter_perfis()


def _rotulo_tomador(perfil: dict) -> str:
    nome = perfil.get("nome") or perfil.get("id") or "Sem nome"
    cargo = perfil.get("cargo") or ""
    return f"{nome} — {cargo}" if cargo else nome


def _invalidar_cache_perfis() -> None:
    st.session_state["perfis_cache_bust"] = st.session_state.get("perfis_cache_bust", 0) + 1
    st.cache_data.clear()


def _obter_atas_anexadas() -> list[dict]:
    atas = st.session_state.get("atas_anexadas")
    if isinstance(atas, list) and atas:
        return atas
    if st.session_state.get("ata_gerada_texto"):
        return [
            {
                "nome": st.session_state.get("ata_gerada_nome") or "ata_gerada.md",
                "texto": st.session_state["ata_gerada_texto"],
            }
        ]
    return []


def _painel_atas_multiplas() -> list[DocumentoEntrada]:
    """Upload e gestão de várias atas/documentos (.txt, .csv, .docx)."""
    if "atas_anexadas" not in st.session_state:
        st.session_state["atas_anexadas"] = _obter_atas_anexadas()

    st.subheader("Atas e documentos")
    st.caption(
        "Anexe uma ou várias atas (.txt, .csv, .docx). "
        "O Tomador analisa o registro escrito sem ter participado das reuniões."
    )

    uploads = st.file_uploader(
        "Adicionar atas / documentos (múltiplos)",
        type=TIPOS_UPLOAD,
        accept_multiple_files=True,
        key="jornada_analise_atas_multi",
    )

    if st.button("Incluir arquivos selecionados", disabled=not uploads):
        adicionados = 0
        for arq in uploads or []:
            try:
                doc = extrair_texto_arquivo(arq.name, arq.getvalue())
                st.session_state["atas_anexadas"] = anexar_documento_sessao(
                    st.session_state.get("atas_anexadas") or [],
                    nome=doc.nome,
                    texto=doc.texto,
                )
                adicionados += 1
            except Exception as exc:  # noqa: BLE001
                st.warning(f"{arq.name}: {exc}")
        if adicionados:
            st.success(f"{adicionados} arquivo(s) incluído(s).")
            st.rerun()

    atas = list(st.session_state.get("atas_anexadas") or [])
    docs: list[DocumentoEntrada] = []

    if atas:
        st.markdown(f"**{len(atas)} arquivo(s) anexado(s)**")
        remover: list[str] = []
        for i, item in enumerate(atas):
            nome = item.get("nome") or f"documento_{i+1}"
            cols = st.columns([4, 1])
            with cols[0]:
                with st.expander(nome, expanded=False):
                    preview = (item.get("texto") or "")[:4000]
                    st.text(preview + ("…" if len(item.get("texto") or "") > 4000 else ""))
            with cols[1]:
                if st.button("Remover", key=f"rm_ata_{i}_{nome}"):
                    remover.append(nome)
            docs.append(DocumentoEntrada(nome=nome, texto=item.get("texto") or ""))

        if remover:
            st.session_state["atas_anexadas"] = [
                a for a in atas if a.get("nome") not in remover
            ]
            st.rerun()

        if st.button("Limpar todas as atas"):
            st.session_state["atas_anexadas"] = []
            st.session_state.pop("ata_gerada_texto", None)
            st.session_state.pop("ata_gerada_nome", None)
            st.rerun()
    else:
        st.info("Nenhuma ata anexada ainda. Envie arquivos acima ou gere na jornada 1.")

    return docs


def _painel_atualizar_personas(perfis: list[dict]) -> None:
    """Dois botões: buscar novos .txt em pessoas/ ou atualizar os já cadastrados."""
    with st.expander("Personas", expanded=False):
        st.caption(
            f"Os currículos ficam na pasta `{PESSOAS_DIR.name}/`. "
            "Coloque os arquivos `.txt` lá e use os botões abaixo — "
            "não é preciso enviar nada pela tela."
        )

        novos = listar_novos_curriculos()
        existentes = listar_curriculos_existentes()

        if perfis:
            st.markdown(
                "**Já no sistema:** "
                + ", ".join(_rotulo_tomador(p) for p in perfis)
            )
        else:
            st.info("Nenhuma persona convertida ainda.")

        if novos:
            st.info(
                f"{len(novos)} arquivo(s) novo(s) em `{PESSOAS_DIR.name}/`: "
                + ", ".join(c.caminho.name for c in novos)
            )
        else:
            st.caption("Nenhum arquivo novo pendente de inclusão.")

        b1, b2 = st.columns(2)
        with b1:
            if st.button(
                "Adicionar personas",
                type="primary",
                use_container_width=True,
                key="btn_adicionar_persona",
                disabled=not novos,
                help="Converte automaticamente os .txt novos encontrados na pasta pessoas/",
            ):
                if not get_api_key():
                    st.error("Configure `OPENAI_API_KEY` no `.env`.")
                    return
                status = st.empty()
                try:
                    adicionados, nomes = adicionar_novas_personas(
                        progresso=lambda msg: status.info(msg),
                    )
                    status.empty()
                    _invalidar_cache_perfis()
                    if adicionados:
                        st.success(
                            f"{len(adicionados)} persona(s) adicionada(s): "
                            + ", ".join(nomes)
                        )
                        st.rerun()
                    else:
                        st.info("Nenhum arquivo novo para adicionar.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao adicionar: {exc}")

        with b2:
            if st.button(
                "Atualizar pessoas",
                use_container_width=True,
                key="btn_atualizar_persona",
                disabled=not existentes,
                help="Relê a pasta pessoas/ e regenera os perfis já cadastrados",
            ):
                if not get_api_key():
                    st.error("Configure `OPENAI_API_KEY` no `.env`.")
                    return
                status = st.empty()
                try:
                    atualizados, nomes = atualizar_personas_da_pasta(
                        forcar=True,
                        progresso=lambda msg: status.info(msg),
                    )
                    status.empty()
                    _invalidar_cache_perfis()
                    if atualizados:
                        st.success(
                            f"{len(atualizados)} persona(s) atualizada(s): "
                            + ", ".join(nomes)
                        )
                        st.rerun()
                    else:
                        st.info("Nenhuma persona existente para atualizar.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao atualizar: {exc}")


def render() -> None:
    render_cabecalho(
        "Jornada Análise: o Tomador interpreta problema/ata (mesmo sem ter participado) "
        "e o Especialista IA avalia essa visão."
    )

    if "perfis_cache_bust" not in st.session_state:
        st.session_state.perfis_cache_bust = 0

    if not get_api_key():
        st.warning("Configure `OPENAI_API_KEY` no `.env`.")

    with st.spinner("Carregando tomadores…"):
        try:
            perfis = _carregar_perfis_cached(st.session_state.perfis_cache_bust)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Falha ao carregar perfis: {exc}")
            return

    _painel_atualizar_personas(perfis)

    if not perfis:
        st.info(
            f"Nenhum currículo em `{PESSOAS_DIR.name}/`. "
            "Coloque arquivos `.txt` nessa pasta e use **Adicionar personas**."
        )
        return

    if st.session_state.pop("veio_da_ata", False):
        n = len(_obter_atas_anexadas())
        st.success(
            f"Resumo da ata preenchido no pedido de ajuda "
            f"({n} ata(s) anexada(s)). Revise Tomadores/lentes e clique em Analisar."
        )

    opcoes = {p["id"]: _rotulo_tomador(p) for p in perfis}
    ids_todos = list(opcoes.keys())
    perfil_ids = st.multiselect(
        "Tomadores de Decisão",
        options=ids_todos,
        default=ids_todos,
        format_func=lambda pid: opcoes[pid],
        help="Selecione uma ou várias pessoas. Por padrão, todas estão habilitadas.",
        key="jornada_analise_tomadores",
    )
    perfis_sel = [p for p in perfis if p["id"] in perfil_ids]

    if not perfis_sel:
        st.warning("Selecione ao menos um Tomador de Decisão.")
        return

    lentes_sel = st.multiselect(
        "Lentes de continuidade",
        options=list(LENTES.keys()),
        default=list(DEFAULT_LENTES),
        format_func=rotulo_lente,
    )
    lentes_ativas = normalizar_lentes(lentes_sel)

    with st.sidebar:
        st.divider()
        st.subheader(f"Painel dos Tomadores ({len(perfis_sel)})")
        for perfil in perfis_sel:
            with st.expander(_rotulo_tomador(perfil), expanded=len(perfis_sel) == 1):
                st.markdown(f"**Cargo:** {perfil.get('cargo') or '—'}")
                st.markdown(f"**Empresa:** {perfil.get('empresa') or '—'}")
                st.markdown(f"**Experiência:** {perfil.get('anos_experiencia', 0)} anos")
                if perfil.get("especialidades"):
                    st.markdown("**Especialidades**")
                    st.write(", ".join(perfil["especialidades"]))
                if perfil.get("formacao"):
                    st.markdown("**Formação**")
                    lista_bullets(perfil["formacao"])
                if perfil.get("perfil_analitico"):
                    st.markdown("**Resumo**")
                    st.write(perfil["perfil_analitico"])
        st.markdown("**Lentes:** " + ", ".join(LENTES[i]["nome"] for i in lentes_ativas))
        st.caption(f"2ª voz: {nome_especialista()}")
        st.caption(ESPECIALISTA_IA.get("perfil_analitico", "")[:180] + "…")

    problema = st.text_area(
        "Problema / pedido de ajuda",
        height=140,
        key="jornada_analise_problema",
    )
    contexto = st.text_area(
        "Contexto adicional (opcional)",
        height=100,
        key="jornada_analise_contexto",
    )

    docs_lidos = _painel_atas_multiplas()
    nomes_docs = [d.nome for d in docs_lidos]
    docs_bloco = montar_bloco_documentos(docs_lidos) if docs_lidos else ""

    if st.button("Analisar", type="primary"):
        if not problema.strip() and not docs_bloco.strip():
            st.error("Informe um problema ou anexe/gere pelo menos um documento.")
            return
        if not get_api_key():
            st.error("OPENAI_API_KEY não configurada.")
            return

        resultados: list[dict] = []
        total = len(perfis_sel)
        progresso = st.progress(0.0, text="Iniciando análises…")

        for i, perfil in enumerate(perfis_sel):
            nome = perfil.get("nome") or perfil.get("id") or f"Tomador {i+1}"
            progresso.progress(
                i / total,
                text=f"Tomador {i+1}/{total}: {nome} analisando…",
            )
            try:
                analise_tomador = analisar_problema(
                    perfil,
                    problema,
                    contexto,
                    documentos=docs_bloco,
                    lentes=lentes_ativas,
                )
            except Exception as exc:  # noqa: BLE001
                progresso.empty()
                st.error(f"Erro no Tomador ({nome}): {exc}")
                return

            progresso.progress(
                (i + 0.5) / total,
                text=f"Especialista IA avaliando a visão de {nome}…",
            )
            avaliacao = None
            try:
                avaliacao = avaliar_com_especialista_ia(
                    perfil=perfil,
                    problema=problema,
                    contexto=contexto,
                    analise_tomador=analise_tomador,
                    documentos=docs_bloco,
                    lentes=lentes_ativas,
                )
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Especialista indisponível para {nome}: {exc}")

            resultados.append(
                {
                    "id": perfil.get("id"),
                    "nome": nome,
                    "analise": analise_tomador,
                    "avaliacao": avaliacao,
                }
            )

        progresso.progress(1.0, text="Análises concluídas.")
        progresso.empty()

        # Compatibilidade com jornada 3: bloco consolidado das vozes.
        blocos_tomador = []
        blocos_esp = []
        for r in resultados:
            blocos_tomador.append(f"### {r['nome']}\n\n{r['analise']}")
            if r.get("avaliacao"):
                blocos_esp.append(f"### Avaliação sobre {r['nome']}\n\n{r['avaliacao']}")

        nomes = [r["nome"] for r in resultados]
        st.session_state["analises_multiplas"] = resultados
        st.session_state["analise_tomador"] = "\n\n".join(blocos_tomador)
        st.session_state["avaliacao_especialista"] = (
            "\n\n".join(blocos_esp) if blocos_esp else None
        )
        st.session_state["analise_comparativa"] = None
        st.session_state["nome_tomador"] = " · ".join(nomes)
        st.session_state["problema_atual"] = problema
        st.session_state["contexto_atual"] = contexto
        st.session_state["documentos_atual"] = docs_bloco
        st.session_state["nomes_docs"] = nomes_docs
        st.session_state["lentes_atual"] = lentes_ativas

    if not st.session_state.get("analise_tomador"):
        return

    st.divider()
    st.subheader("Resultado da análise")
    nome_tomador = st.session_state.get("nome_tomador", "Tomador")
    avaliacao = st.session_state.get("avaliacao_especialista")
    multiplas = st.session_state.get("analises_multiplas") or []

    if st.button("Salvar análises (.docx)"):
        try:
            caminho = salvar_analises(
                nome_tomador=nome_tomador,
                problema=st.session_state.get("problema_atual", ""),
                contexto=st.session_state.get("contexto_atual", ""),
                analise_tomador=st.session_state["analise_tomador"],
                avaliacao_especialista=avaliacao,
                analise_comparativa=st.session_state.get("analise_comparativa"),
                documentos=st.session_state.get("documentos_atual", ""),
            )
            st.session_state["ultimo_arquivo_salvo"] = str(caminho)
            st.success(f"Salvo em `outputs/{caminho.name}`")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Erro ao salvar: {exc}")

    if st.session_state.get("ultimo_arquivo_salvo"):
        path = Path(st.session_state["ultimo_arquivo_salvo"])
        if path.exists():
            st.download_button(
                "Baixar relatório (.docx)",
                data=path.read_bytes(),
                file_name=path.name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

    if multiplas:
        st.caption(f"{len(multiplas)} Tomador(es): {nome_tomador}")
        for r in multiplas:
            st.markdown(
                f'<div class="voz-tomador"><h3>Tomador de Decisão — {r["nome"]}</h3></div>',
                unsafe_allow_html=True,
            )
            st.markdown(r["analise"])
            st.markdown(
                f'<div class="voz-especialista"><h3>{nome_especialista()} '
                f'(sobre {r["nome"]})</h3></div>',
                unsafe_allow_html=True,
            )
            if r.get("avaliacao"):
                st.markdown(r["avaliacao"])
            else:
                st.warning(f"Avaliação do especialista indisponível para {r['nome']}.")
            st.divider()
    else:
        st.markdown(
            f'<div class="voz-tomador"><h3>Tomador de Decisão — {nome_tomador}</h3></div>',
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state["analise_tomador"])

        st.markdown(
            f'<div class="voz-especialista"><h3>{nome_especialista()}</h3></div>',
            unsafe_allow_html=True,
        )
        if avaliacao:
            st.markdown(avaliacao)
        else:
            st.warning("Avaliação do especialista indisponível.")

    st.info("Para a comparação técnica das vozes, vá à jornada **3 · Análise Comparativa**.")
