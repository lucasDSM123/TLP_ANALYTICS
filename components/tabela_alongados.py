import pandas as pd
import streamlit as st

import config
from components.cards import card


def render_stats_bar(stats: dict):
    """Linha de cards com os números gerais da aba (mesmo padrão visual dos
    outros KPIs do site)."""
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        card("Atividades Alongadas", stats["alongadas"], config.TLP_RED)
    with col2:
        card("% de Alongados", f"{stats['pct']:.1f}%", config.TLP_RED)
    with col3:
        card("Total Atividades", stats["total"], "#2E63C7")
    with col4:
        card("Manhã (alon.)", stats["manha"], config.TLP_GOLD)
    with col5:
        card("Tarde (alon.)", stats["tarde"], config.TLP_GOLD)


def render_tabelas_cluster(contagem: pd.DataFrame, percentual: pd.DataFrame):
    """Duas tabelas lado a lado: contagem de alongadas por faixa de duração
    e o percentual equivalente sobre o total de atividades do cluster."""
    col_cnt, col_pct = st.columns(2)

    with col_cnt:
        st.markdown("**Contagem por Cluster**")
        if contagem.empty:
            st.info("Sem atividades alongadas para este filtro.")
        else:
            st.dataframe(contagem, width='stretch', hide_index=True)

    with col_pct:
        st.markdown("**Percentual por Cluster**")
        if percentual.empty:
            st.info("Sem atividades alongadas para este filtro.")
        else:
            fmt = {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in percentual.columns if c != "Cluster"}
            st.dataframe(percentual, width='stretch', hide_index=True, column_config=fmt)


def render_detalhe(detalhe: pd.DataFrame):
    if detalhe.empty:
        st.info("Nenhuma atividade alongada para este filtro.")
        return
    st.dataframe(detalhe, width='stretch', hide_index=True)


def render_ranking(ranking: pd.DataFrame):
    if ranking.empty:
        st.info("Nenhum técnico com atividades alongadas para este filtro.")
        return
    st.dataframe(
        ranking,
        width='stretch',
        hide_index=True,
        column_config={
            "% Alon.": st.column_config.NumberColumn("% Alon.", format="%.1f%%"),
        },
    )
