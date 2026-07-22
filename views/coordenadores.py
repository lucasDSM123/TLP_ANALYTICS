import streamlit as st

from components.header import secao_titulo
from components.charts import grafico_ranking, grafico_atribuicao_pu
from components.tabela_coordenador import render_tabela_coordenadores
from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo
from services.coordenador_tabela import tabela_coordenadores


def render(df, indicadores: Indicadores):
    secao_titulo("Coordenadores", "Performance consolidada por coordenador")

    ranking = metricas_por_grupo(df, "Coordenador")

    if ranking.empty:
        st.warning("Nenhum dado de coordenador encontrado na base.")
        return

    hc = indicadores.hc_real()
    caixa = indicadores.caixa_total()
    eficacia = indicadores.eficacia()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Coordenadores", ranking.shape[0])
    col2.metric("HC Ativo Total", hc["HC"])
    col3.metric("Caixa Total", f"{caixa['TOTAL']:,}".replace(",", "."))
    col4.metric("Eficácia Geral", f"{eficacia['GERAL']:.0%}")

    st.markdown("<br>", unsafe_allow_html=True)

    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        st.plotly_chart(
            grafico_ranking(ranking, "Concluído OK", "Top 15 — Concluído OK"),
            width='stretch',
        )

    with col_tab:
        tabela = ranking.sort_values("Concluído OK", ascending=False).copy()
        tabela["Eficácia"] = tabela["Eficácia"] * 100
        st.dataframe(
            tabela,
            width='stretch',
            hide_index=True,
            column_config={
                "Eficácia": st.column_config.NumberColumn("Eficácia", format="%.1f%%"),
                "PU": st.column_config.NumberColumn("PU", format="%.2f"),
            },
        )

    st.divider()
    secao_titulo("Atribuição x PU", "Evolução diária — Atribuição (Caixa/HC) vs Produtividade Unitária")
    st.plotly_chart(grafico_atribuicao_pu(df), width='stretch')

    st.divider()

    # ====== TABELA DETALHADA: COORDENADOR x SUPERVISOR ======
    secao_titulo(
        "Produção por Coordenador",
        "Coordenador → Supervisor, com subtotal por cluster/região (Meta = HC Ativo × 3)",
    )
    render_tabela_coordenadores(tabela_coordenadores(df))
