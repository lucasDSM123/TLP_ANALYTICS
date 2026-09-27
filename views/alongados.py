import streamlit as st

from components.header import secao_titulo
from components.tabela_alongados import (
    render_stats_bar, render_tabelas_cluster, render_detalhe, render_ranking,
)
from services.alongados import preparar_base, stats_gerais, tabela_cluster, detalhe_alongadas, ranking_tecnicos, CATEGORIAS, ROTULO_CATEGORIA
from services.indicadores import Indicadores


def render(df, indicadores: Indicadores):
    secao_titulo(
        "Alongados",
        "Base Zeus · Atividades com duração ≥ 1h30 — réplica da lógica do Backoffice Regional Sul",
    )

    # ---------------- filtro de categoria (BA/BD/ME/Serviço/Preventiva) ----------------
    # Multi-seleção, igual aos botões do site da Vivo — guardado em
    # session_state pra manter a escolha ao navegar entre abas.
    categorias_sel = st.multiselect(
        "Categorias",
        options=CATEGORIAS,
        default=st.session_state.get("alongados_categorias", CATEGORIAS),
        format_func=lambda c: ROTULO_CATEGORIA.get(c, c),
        key="alongados_categorias",
    )

    base = preparar_base(df, categorias=categorias_sel or None)

    if base.empty:
        st.warning("Nenhuma atividade encontrada para este filtro.")
        return

    stats = stats_gerais(base)
    render_stats_bar(stats)

    st.markdown("<br>", unsafe_allow_html=True)

    contagem, percentual = tabela_cluster(base)
    render_tabelas_cluster(contagem, percentual)

    st.markdown("<br>", unsafe_allow_html=True)

    aba_detalhe, aba_ranking = st.tabs(["Detalhe das Atividades", "Ranking de Técnicos"])
    with aba_detalhe:
        render_detalhe(detalhe_alongadas(base))
    with aba_ranking:
        render_ranking(ranking_tecnicos(base))
