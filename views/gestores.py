import streamlit as st

from components.header import secao_titulo
from components.charts import grafico_media_atribuida_pu, grafico_ranking
from components.tabela_analise_p import tabela_analise_p_cluster
from components.tabela_coordenador import render_tabela_coordenadores
from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo, metricas_por_tecnico
from services.coordenador_tabela import tabela_coordenadores
from services.loader import opcoes_filtro, aplicar_filtro
from services.analise_p import classificacao_tecnicos


def render(df, indicadores: Indicadores):
    secao_titulo("Gestores", "Coordenadores e Supervisores — visão consolidada e segmentada")

    # ====== SEGMENTAÇÃO EM CASCATA: COORDENADOR → SUPERVISOR → TÉCNICO ======
    col1, col2, col3 = st.columns(3)

    with col1:
        coordenadores_opcoes = opcoes_filtro(df, "Coordenador")
        coord_sel = st.selectbox("Coordenador", coordenadores_opcoes, key="gestor_coord")
    df_coord = aplicar_filtro(df, "Coordenador", coord_sel)

    with col2:
        supervisores_opcoes = opcoes_filtro(df_coord, "Supervisor")
        sup_sel = st.selectbox("Supervisor", supervisores_opcoes, key="gestor_supervisor")
    df_sup = aplicar_filtro(df_coord, "Supervisor", sup_sel)

    with col3:
        tecnicos_opcoes = opcoes_filtro(df_sup, "Técnico")
        tec_sel = st.selectbox("Técnico", tecnicos_opcoes, key="gestor_tecnico")
    df_filtrado = aplicar_filtro(df_sup, "Técnico", tec_sel)

    st.markdown("<br>", unsafe_allow_html=True)

    # ====== RESUMO — NÍVEL COORDENADOR (base geral, sem a segmentação acima) ======
    ranking_coord = metricas_por_grupo(df, "Coordenador")

    if ranking_coord.empty:
        st.warning("Nenhum dado de coordenador encontrado na base.")
        return

    hc = indicadores.hc_real()
    caixa = indicadores.caixa_total()
    eficacia = indicadores.eficacia()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Coordenadores", ranking_coord.shape[0])
    col2.metric("HC Ativo Total", hc["HC"])
    col3.metric("Caixa Total", f"{caixa['TOTAL']:,}".replace(",", "."))
    col4.metric("Eficácia Geral", f"{eficacia['GERAL']:.0%}")

    # ====== RESUMO — NÍVEL SUPERVISOR (respeitando a segmentação acima) ======
    ranking_sup = metricas_por_grupo(df_filtrado, "Supervisor")
    ind_filtrado = Indicadores(df_filtrado)

    if not ranking_sup.empty:
        hc_f = ind_filtrado.hc_real()
        pu_f = ind_filtrado.pu()
        projecao_f = ind_filtrado.projecao()

        st.caption("Considerando a segmentação Coordenador → Supervisor → Técnico selecionada acima")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Supervisores", ranking_sup.shape[0])
        col2.metric("HC Ativo (filtro)", hc_f["HC"])
        col3.metric("PU Médio (filtro)", f"{pu_f['GERAL']:.2f}")
        col4.metric("Projeção (filtro)", f"{projecao_f['GERAL']:,}".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)

    # ====== ANÁLISE P — COORDENADOR, depois SUPERVISOR ======
    secao_titulo("Análise P por Coordenador", "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6)")
    contagem_coord, percentual_coord, resumo_coord = indicadores.analise_p_cluster(coluna_grupo="Coordenador")
    tabela_analise_p_cluster(contagem_coord, percentual_coord, resumo_coord, coluna_grupo="Coordenador")

    st.markdown("<br>", unsafe_allow_html=True)

    secao_titulo("Análise P por Supervisor", "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6)")
    if df_filtrado.empty:
        st.info("Sem dados de supervisor para os filtros atuais.")
    else:
        contagem_sup, percentual_sup, resumo_sup = ind_filtrado.analise_p_cluster(coluna_grupo="Supervisor")
        tabela_analise_p_cluster(contagem_sup, percentual_sup, resumo_sup, coluna_grupo="Supervisor")

    st.divider()

    secao_titulo("Média Atribuída x PU", "Comparativo por coordenador")
    st.plotly_chart(grafico_media_atribuida_pu(ranking_coord, coluna_grupo="Coordenador"), width='stretch')

    st.divider()

    # ====== PRODUÇÃO POR COORDENADOR, seguida da MATRIZ DE TÉCNICOS ======
    secao_titulo(
        "Produção por Coordenador",
        "Coordenador → Supervisor, com subtotal por cluster/região (Meta = HC Ativo × 3)",
    )
    render_tabela_coordenadores(tabela_coordenadores(df))

    st.markdown("<br>", unsafe_allow_html=True)

    secao_titulo("Indicadores Principais por Técnico", "Todos os técnicos do filtro atual e seus indicadores completos")
    matriz_geral = metricas_por_tecnico(df_filtrado)
    if matriz_geral.empty:
        st.info("Sem técnicos com atividades para os filtros atuais.")
    else:
        matriz_geral = matriz_geral.sort_values("PU", ascending=False).copy()
        colunas_exibir = [c for c in [
            "Técnico", "Supervisor", "Classificação P", "Caixa Total", "Concluído OK", "Concluído NOK",
            "Eficácia", "PU", "Esteira", "Iniciada", "Projeção", "Cluster",
        ] if c in matriz_geral.columns]
        matriz_fmt = matriz_geral[colunas_exibir].copy()
        matriz_fmt["Eficácia"] = matriz_fmt["Eficácia"] * 100
        st.dataframe(
            matriz_fmt,
            width='stretch',
            hide_index=True,
            column_config={
                "Eficácia": st.column_config.NumberColumn("Eficácia", format="%.1f%%"),
                "PU": st.column_config.NumberColumn("PU", format="%.2f"),
            },
        )

    st.divider()

    # ====== DETALHAMENTO CONFORME SEGMENTAÇÃO ESCOLHIDA ACIMA ======
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
            caixa_tec = ind_filtrado.caixa_total()
            efic_tec = ind_filtrado.eficacia()
            qtd = int(linha.iloc[0]["Concluídas"])
            classe = linha.iloc[0]["Classificação"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Classificação P", classe)
            c2.metric("Concluídas", qtd)
            c3.metric("Caixa Total", caixa_tec["TOTAL"])
            c4.metric("Eficácia", f"{efic_tec['GERAL']:.0%}")

    elif sup_sel != "Todos":
        secao_titulo(
            "Ranking de Técnicos — Supervisor selecionado",
            f"Técnicos de **{sup_sel}** ordenados por PU",
        )
        matriz_tec = metricas_por_tecnico(df_filtrado)
        if matriz_tec.empty:
            st.info("Sem técnicos com atividades para este supervisor nos filtros atuais.")
        else:
            st.plotly_chart(
                grafico_ranking(matriz_tec[["Técnico", "PU"]], "PU", f"Técnicos de {sup_sel} — PU"),
                width='stretch',
            )
