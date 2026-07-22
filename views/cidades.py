import streamlit as st

from components.header import secao_titulo
from components.charts import grafico_ranking, grafico_producao_dia
from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo
from services.loader import opcoes_filtro, aplicar_filtro


def render(df, indicadores: Indicadores):
    secao_titulo("Cidades", "Produção por cidade, com filtro de estado")

    estados = opcoes_filtro(df, "Estado")
    estado_sel = st.selectbox("Filtrar por Estado", estados, key="cid_estado")

    df_filtrado = aplicar_filtro(df, "Estado", estado_sel)
    ranking = metricas_por_grupo(df_filtrado, "Cidade")

    if ranking.empty:
        st.warning("Nenhum dado de cidade encontrado para este filtro.")
        return

    ind_filtrado = Indicadores(df_filtrado)
    caixa = ind_filtrado.caixa_total()
    esteira = ind_filtrado.esteira()
    iniciada = ind_filtrado.iniciada()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cidades", ranking.shape[0])
    col2.metric("Caixa Total", f"{caixa['TOTAL']:,}".replace(",", "."))
    col3.metric("Esteira", f"{esteira['TOTAL']:,}".replace(",", "."))
    col4.metric("Iniciada", f"{iniciada['TOTAL']:,}".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)

    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        st.plotly_chart(
            grafico_ranking(ranking, "Caixa Total", "Top 15 — Caixa Total"),
            width='stretch',
        )

    with col_tab:
        tabela = ranking.sort_values("Caixa Total", ascending=False).copy()
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
    secao_titulo("Produção Diária", "Filtro aplicado acima")
    st.plotly_chart(grafico_producao_dia(df_filtrado), width='stretch')
