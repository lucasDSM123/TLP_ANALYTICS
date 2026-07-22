import streamlit as st

from components.header import secao_titulo
from components.charts import grafico_ranking
from components.tabela_analise_p import tabela_analise_p
from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo, metricas_por_tecnico
from services.loader import opcoes_filtro, aplicar_filtro
from services.analise_p import matriz_analise_p, classificacao_tecnicos


def render(df, indicadores: Indicadores):
    secao_titulo("Supervisores", "Performance por supervisor, com segmentação Coordenador → Supervisor → Técnico")

    # ====== SEGMENTAÇÃO EM CASCATA: COORDENADOR → SUPERVISOR → TÉCNICO ======
    col1, col2, col3 = st.columns(3)

    with col1:
        coordenadores = opcoes_filtro(df, "Coordenador")
        coord_sel = st.selectbox("Coordenador", coordenadores, key="sup_coord")
    df_coord = aplicar_filtro(df, "Coordenador", coord_sel)

    with col2:
        supervisores = opcoes_filtro(df_coord, "Supervisor")
        sup_sel = st.selectbox("Supervisor", supervisores, key="sup_supervisor")
    df_sup = aplicar_filtro(df_coord, "Supervisor", sup_sel)

    with col3:
        tecnicos = opcoes_filtro(df_sup, "Técnico")
        tec_sel = st.selectbox("Técnico", tecnicos, key="sup_tecnico")
    df_filtrado = aplicar_filtro(df_sup, "Técnico", tec_sel)

    ranking = metricas_por_grupo(df_filtrado, "Supervisor")

    if ranking.empty:
        st.warning("Nenhum dado de supervisor encontrado para este filtro.")
        return

    ind_filtrado = Indicadores(df_filtrado)
    hc = ind_filtrado.hc_real()
    pu = ind_filtrado.pu()
    projecao = ind_filtrado.projecao()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Supervisores", ranking.shape[0])
    col2.metric("HC Ativo", hc["HC"])
    col3.metric("PU Médio", f"{pu['GERAL']:.2f}")
    col4.metric("Projeção", f"{projecao['GERAL']:,}".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)

    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        st.plotly_chart(
            grafico_ranking(ranking, "PU", "Top 15 — Produtividade (PU)"),
            width='stretch',
        )

    with col_tab:
        tabela = ranking.sort_values("PU", ascending=False).copy()
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

    # ====== MATRIZ DE TÉCNICOS E SEUS INDICADORES (por Supervisor) ======
    # Acompanha a segmentação escolhida acima (Coordenador → Supervisor →
    # Técnico):
    #   - nenhum Supervisor específico escolhido -> matriz Análise P por Supervisor
    #   - Supervisor selecionado (sem Técnico) -> matriz com TODOS os
    #     técnicos daquele supervisor e TODOS os indicadores de cada um
    #     (Caixa Total, Concluído OK/NOK, Eficácia, PU, Esteira, Iniciada,
    #     Projeção, além da Classificação P)
    #   - Técnico específico escolhido -> cartões individuais do técnico

    if tec_sel != "Todos":
        secao_titulo(
            "Indicadores do Técnico",
            f"Detalhamento individual — {tec_sel}",
        )
        tabela_tec = classificacao_tecnicos(df_filtrado)
        linha = tabela_tec[tabela_tec["Técnico"] == tec_sel]
        if linha.empty:
            st.info("Sem atividades para este técnico nos filtros atuais.")
        else:
            ind_tec = Indicadores(df_filtrado)
            caixa_tec = ind_tec.caixa_total()
            conc_tec = ind_tec.concluido()
            efic_tec = ind_tec.eficacia()
            qtd = int(linha.iloc[0]["Concluídas"])
            classe = linha.iloc[0]["Classificação"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Classificação P", classe)
            c2.metric("Concluídas", qtd)
            c3.metric("Caixa Total", caixa_tec["TOTAL"])
            c4.metric("Eficácia", f"{efic_tec['GERAL']:.0%}")

    elif sup_sel != "Todos":
        secao_titulo(
            "Matriz de Técnicos — Supervisor selecionado",
            f"Todos os técnicos de **{sup_sel}** e seus indicadores completos",
        )
        matriz_tec = metricas_por_tecnico(df_filtrado)
        if matriz_tec.empty:
            st.info("Sem técnicos com atividades para este supervisor nos filtros atuais.")
        else:
            matriz_tec = matriz_tec.sort_values("PU", ascending=False).copy()
            colunas_exibir = [c for c in [
                "Técnico", "Classificação P", "Caixa Total", "Concluído OK", "Concluído NOK",
                "Eficácia", "PU", "Esteira", "Iniciada", "Projeção", "Cluster",
            ] if c in matriz_tec.columns]
            matriz_tec_fmt = matriz_tec[colunas_exibir].copy()
            matriz_tec_fmt["Eficácia"] = matriz_tec_fmt["Eficácia"] * 100
            st.dataframe(
                matriz_tec_fmt,
                width='stretch',
                hide_index=True,
                column_config={
                    "Eficácia": st.column_config.NumberColumn("Eficácia", format="%.1f%%"),
                    "PU": st.column_config.NumberColumn("PU", format="%.2f"),
                },
            )
            st.plotly_chart(
                grafico_ranking(matriz_tec[["Técnico", "PU"]], "PU", f"Técnicos de {sup_sel} — PU"),
                width='stretch',
            )

    else:
        secao_titulo(
            "Análise P — Produtividade por Técnico",
            "Classificação dos técnicos pela quantidade de atividades concluídas (P0 = 0 concluídas … >P3 = mais de 3). Selecione um Supervisor acima para ver a matriz completa de técnicos.",
        )
        matriz_sup = matriz_analise_p(df_filtrado, coluna_grupo="Supervisor")
        tabela_analise_p(matriz_sup, "Supervisor", "Produtividade por Supervisor — Técnico (Análise P)")

        with st.expander("Ver também agrupado por Coordenador"):
            matriz_coord = matriz_analise_p(df_filtrado, coluna_grupo="Coordenador")
            tabela_analise_p(matriz_coord, "Coordenador", "Produtividade por Coordenador — Técnico (Análise P)")
