import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.charts import grafico_media_atribuida_pu, grafico_ranking, opcoes_grafico
from components.tabela_analise_p import tabela_analise_p_coordenador_supervisor_tecnico
from components.tabela_coordenador import render_tabela_coordenadores
from components.tabelas import tabela_matriz_expansivel
from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo, metricas_por_tecnico, matriz_producao, matriz_producao_cluster_cidade
from services.coordenador_tabela import tabela_coordenadores, total_geral
from services.loader import opcoes_filtro, aplicar_filtro
from services.analise_p import classificacao_tecnicos, matriz_analise_p_coordenador_supervisor_tecnico
from components.print_button import area_com_print, legenda_producao_ou_fechamento, contexto_legenda_filtros


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

    with area_com_print("gestores_cards_coordenador", nome_arquivo="resumo_coordenadores"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            card("Coordenadores", ranking_coord.shape[0], config.TLP_ORANGE, icon="🧑\u200d💼")
        with col2:
            card("HC Ativo Total", hc["HC"], "#7B8CDE")
        with col3:
            card("Caixa Total", f"{caixa['TOTAL']:,}".replace(",", "."), "#00C9A7")
        with col4:
            card("Eficácia Geral", f"{eficacia['GERAL']:.0%}", config.TLP_RED)

    # ====== RESUMO — NÍVEL SUPERVISOR (respeitando a segmentação acima) ======
    ranking_sup = metricas_por_grupo(df_filtrado, "Supervisor")
    ind_filtrado = Indicadores(df_filtrado)

    if not ranking_sup.empty:
        hc_f = ind_filtrado.hc_real()
        pu_f = ind_filtrado.pu()
        projecao_f = ind_filtrado.projecao()

        st.caption("Considerando a segmentação Coordenador → Supervisor → Técnico selecionada acima")
        with area_com_print("gestores_cards_supervisor", nome_arquivo="resumo_supervisores_filtro"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                card("Supervisores", ranking_sup.shape[0], config.TLP_GOLD)
            with col2:
                card("HC Ativo (filtro)", hc_f["HC"], "#7B8CDE")
            with col3:
                card("PU Médio (filtro)", f"{pu_f['GERAL']:.2f}", "#00C9A7")
            with col4:
                card("Projeção (filtro)", f"{projecao_f['GERAL']:,}".replace(",", "."), "#FF5C5C")

    st.markdown("<br>", unsafe_allow_html=True)

    # ====== ANÁLISE P — agora só a versão expansível (Coordenador -> Supervisor -> Técnico), mais abaixo ======
    # Usa ind_filtrado (já respeita Coordenador/Supervisor/Técnico) pra bater
    # com a mesma segmentação da tabela expansível mais abaixo.
    _, _, resumo_coord = ind_filtrado.analise_p_cluster(coluna_grupo="Coordenador")


    secao_titulo("Média Atribuída x PU", "Comparativo por coordenador")
    with area_com_print("gestores_grafico_atribuicao_pu", nome_arquivo="atribuicao_pu_por_coordenador"):
        st.plotly_chart(
            grafico_media_atribuida_pu(ranking_coord, coluna_grupo="Coordenador"), width='stretch',
            config=opcoes_grafico("atribuicao_pu_por_coordenador"),
        )

    st.divider()

    # ====== PRODUÇÃO POR COORDENADOR / SUPERVISOR ======
    # Respeita a segmentação Coordenador → Supervisor → Técnico selecionada
    # acima (df_filtrado) — antes essas tabelas ficavam sempre com a base
    # inteira, então selecionar um Coordenador não tinha efeito nelas.
    secao_titulo(
        "Produção por Coordenador",
        "Visão consolidada (BA + TT) e, logo abaixo, o detalhamento expansível por fila",
    )

    # --- Matriz consolidada (BA + TT juntos, sempre expandida, com
    # subtotal por cluster/região — igual ao formato que você já usava) ---
    _ctx_legenda = contexto_legenda_filtros()
    _estado_legenda = _ctx_legenda["estado"]
    _data_legenda = _ctx_legenda["data"]
    _sufixo_legenda = _ctx_legenda["sufixo"]
    _datas_sel = _ctx_legenda["datas_sel"]

    with area_com_print(
        "gestores_matriz_coordenadores", nome_arquivo="producao_por_coordenador",
        legenda_template=legenda_producao_ou_fechamento(
            "PRODUÇÃO + ESTEIRA + EFICÁCIA - BA/TT | {estado}{sufixo} (POR GESTÃO) | {data} {hora}",
            "FECHAMENTO PRODUÇÃO BA/TT | {estado}{sufixo} (POR COORDENADOR) | {data} {hora}",
            _datas_sel,
        ),
        legenda_vars={"estado": _estado_legenda, "data": _data_legenda, "sufixo": _sufixo_legenda},
    ):
        render_tabela_coordenadores(tabela_coordenadores(df_filtrado), total_geral(df_filtrado))

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Detalhamento por fila (BA / TT), expansível por Coordenador -> Supervisor ---
    def _linha_total_producao(df_matriz):
        """Extrai a linha 'Total' da matriz flat (matriz_producao) como
        dict pronto pra tabela expansível (troca a chave 'Cluster' —
        nome fixo da coluna de rótulo em matriz_producao, mesmo quando
        agrupado por Coordenador — por 'Nome')."""
        if df_matriz.empty:
            return None
        linha = df_matriz[df_matriz["Cluster"] == "Total"]
        if linha.empty:
            return None
        total = linha.iloc[0].to_dict()
        total["Nome"] = total.pop("Cluster")
        return total

    matriz_coord_ba = matriz_producao(df_filtrado, lado="BA", coluna_grupo="Coordenador")
    grupos_coord_ba = matriz_producao_cluster_cidade(
        df_filtrado, lado="BA", coluna_grupo="Coordenador", coluna_subgrupo="Supervisor"
    )
    with area_com_print("gestores_matriz_producao_ba", nome_arquivo="producao_ba_por_coordenador"):
        tabela_matriz_expansivel(
            grupos_coord_ba, "PRODUÇÃO BA", cor_titulo="#00C9A7",
            total=_linha_total_producao(matriz_coord_ba), id_tabela="gestores_producao_ba",
            rotulo_grupo="COORDENADOR / SUPERVISOR", rotulo_clique="Coordenador",
        )

    st.write("")

    matriz_coord_tt = matriz_producao(df_filtrado, lado="TT", coluna_grupo="Coordenador")
    grupos_coord_tt = matriz_producao_cluster_cidade(
        df_filtrado, lado="TT", coluna_grupo="Coordenador", coluna_subgrupo="Supervisor"
    )
    with area_com_print("gestores_matriz_producao_tt", nome_arquivo="producao_tt_por_coordenador"):
        tabela_matriz_expansivel(
            grupos_coord_tt, "PRODUÇÃO TT", cor_titulo=config.TLP_ORANGE,
            total=_linha_total_producao(matriz_coord_tt), id_tabela="gestores_producao_tt",
            rotulo_grupo="COORDENADOR / SUPERVISOR", rotulo_clique="Coordenador",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ====== ANÁLISE P — COORDENADOR -> SUPERVISOR -> TÉCNICO (expansível) ======
    secao_titulo(
        "Análise P por Coordenador / Supervisor / Técnico",
        "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6), com quebra até o nível de técnico",
    )
    # Mesmo escopo das demais Análises P (cards / cluster): Contratada = "TLP"
    # e excluindo Supervisor = "BUCKET" — técnicos do bucket não entram na
    # classificação P0..>P3, pois são obras que, se não concluídas, sobram
    # no balde (Bucket) em vez de contar como produtividade do técnico.
    df_analise_p_cst = df_filtrado
    if "Contratada" in df_analise_p_cst.columns:
        df_analise_p_cst = df_analise_p_cst[df_analise_p_cst["Contratada"] == "TLP"]
    if "Supervisor" in df_analise_p_cst.columns:
        df_analise_p_cst = df_analise_p_cst[df_analise_p_cst["Supervisor"] != "BUCKET"]

    grupos_analise_p_cst = matriz_analise_p_coordenador_supervisor_tecnico(df_analise_p_cst)
    with area_com_print("gestores_analise_p_coord_sup_tec", nome_arquivo="analise_p_coordenador_supervisor_tecnico"):
        tabela_analise_p_coordenador_supervisor_tecnico(
            grupos_analise_p_cst, resumo=resumo_coord,
            id_tabela="gestores_analise_p_cst",
        )

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
        with area_com_print("gestores_matriz_tecnicos", nome_arquivo="indicadores_por_tecnico"):
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

            with area_com_print("gestores_cards_tecnico_detalhe", nome_arquivo=f"detalhe_tecnico_{tec_sel}"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    card("Classificação P", classe, config.TLP_GOLD)
                with c2:
                    card("Concluídas", qtd, "#00C9A7")
                with c3:
                    card("Caixa Total", caixa_tec["TOTAL"], "#7B8CDE")
                with c4:
                    card("Eficácia", f"{efic_tec['GERAL']:.0%}", config.TLP_RED)

    elif sup_sel != "Todos":
        secao_titulo(
            "Ranking de Técnicos — Supervisor selecionado",
            f"Técnicos de **{sup_sel}** ordenados por PU",
        )
        matriz_tec = metricas_por_tecnico(df_filtrado)
        if matriz_tec.empty:
            st.info("Sem técnicos com atividades para este supervisor nos filtros atuais.")
        else:
            with area_com_print("gestores_ranking_tecnicos", nome_arquivo=f"ranking_tecnicos_pu_{sup_sel}"):
                st.plotly_chart(
                    grafico_ranking(matriz_tec[["Técnico", "PU"]], "PU", f"Técnicos de {sup_sel} — PU"),
                    width='stretch',
                    config=opcoes_grafico(f"ranking_tecnicos_pu_{sup_sel}"),
                )