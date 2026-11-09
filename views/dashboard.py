import pandas as pd
import streamlit as st

from components.cards import card
from components.header import secao_titulo
from components.charts import grafico_status_pizza, grafico_comparativo_ba_tt, grafico_pareto_causa, opcoes_grafico
from components.tabelas import tabela_matriz, tabela_matriz_expansivel
from components.tabela_analise_p import tabela_analise_p_cluster_cidade, tabela_analise_p_coordenador_supervisor_tecnico
from components.tabela_coordenador import render_tabela_coordenadores
from services.coordenador_tabela import tabela_coordenadores, total_geral
from components.print_button import area_com_print, legenda_producao_ou_fechamento, contexto_legenda_filtros, legenda_filtros
from services.indicadores import Indicadores
from services.grupos import status_counts, matriz_producao, matriz_producao_cluster_cidade, matriz_geral_cluster, metricas_por_tecnico
from services.analise_p import matriz_analise_p_cluster_cidade, matriz_analise_p_coordenador_supervisor_tecnico
import config


def render(df, indicadores: Indicadores):

    hc_real = indicadores.hc_real()
    caixa = indicadores.caixa_total()
    concluido = indicadores.concluido()
    eficacia = indicadores.eficacia()
    pu = indicadores.pu()
    projecao = indicadores.projecao()
    esteira = indicadores.esteira()
    bucket = indicadores.bucket()
    iniciada = indicadores.iniciada()
    media = indicadores.media_atribuicao()
    projecao_pu = indicadores.projecao_pu()
    pu_vivo = indicadores.pu_vivo()
    projecao_pu_vivo = indicadores.projecao_pu_vivo()

    # ====== INDICADORES PRINCIPAIS ======
    secao_titulo("Indicadores Principais", "Visão consolidada da operação")

    # Legenda automática (texto que acompanha a imagem ao copiar): reflete
    # TODOS os filtros marcados na barra do topo (Estado, Data, Cluster,
    # Cidade, Coordenador) — "TODOS" / "TODAS AS DATAS" quando nada
    # estiver marcado (visão geral, sem recorte).
    _ctx_legenda = contexto_legenda_filtros()
    _estado_legenda = _ctx_legenda["estado"]
    _data_legenda = _ctx_legenda["data"]
    _sufixo_legenda = _ctx_legenda["sufixo"]
    _datas_sel = _ctx_legenda["datas_sel"]

    with area_com_print(
        "dashboard_cards_principais", nome_arquivo="indicadores_principais",
        legenda_template=legenda_producao_ou_fechamento(
            "PRODUÇÃO GERAL | {estado}{sufixo} | {data} {hora}",
            "FECHAMENTO GERAL | {estado}{sufixo} | {data} {hora}",
            _datas_sel,
        ),
        legenda_vars={"estado": _estado_legenda, "data": _data_legenda, "sufixo": _sufixo_legenda},
    ):
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            card("HC ATIVO", hc_real["HC"], config.TLP_ORANGE, f"BA: {hc_real['BA']} | TT: {hc_real['TT']}")
        with col2:
            card("CAIXA TOTAL", f"{caixa['TOTAL']:,}".replace(",", "."), "#00C9A7", "Atividades válidas")
        with col3:
            card("CONCLUÍDO OK", f"{concluido['OK']:,}".replace(",", "."), config.TLP_GOLD,
                 f"NOK: {concluido['NOK']:,}".replace(",", "."))
        with col4:
            card("NÃO CONCLUÍDA", f"{concluido['NOK']:,}".replace(",", "."), config.TLP_RED, "Concluído NOK")
        with col5:
            card("PU", f"{pu['GERAL']:.2f}", "#7B8CDE",
                 pu_site=pu["GERAL"], pu_vivo_valor=pu_vivo["GERAL"])
        with col6:
            card("PROJEÇÃO PU", f"{projecao_pu['GERAL']:.2f}", "#7B8CDE",
                 pu_site=projecao_pu["GERAL"], pu_vivo_valor=projecao_pu_vivo["GERAL"],
                 rotulo_vivo="Proj. PU Vivo")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            card("EFICÁCIA", f"{eficacia['GERAL']:.0%}", config.TLP_RED, "Taxa de conclusão")
        with col2:
            card("PROJEÇÃO", f"{projecao['GERAL']:,}".replace(",", "."), "#FF5C5C",
                 f"BA: {projecao['BA']} | TT: {projecao['TT']}")
        with col3:
            card("MÉDIA ATRIBUÍDA", f"{media['GERAL']:.2f}", "#00C9A7")
        with col4:
            card("BUCKET", bucket["TOTAL"], config.TLP_GOLD, f"BA: {bucket['BA']} | TT: {bucket['TT']}")
        with col5:
            card("ESTEIRA", esteira["TOTAL"], "#7B8CDE", f"BA: {esteira['BA']} | TT: {esteira['TT']}")
        with col6:
            card("INICIADA", iniciada["TOTAL"], "#FF5C5C", f"BA: {iniciada['BA']} | TT: {iniciada['TT']}")

    st.divider()

    # ====== INDICADORES POR CLUSTER (cards principais distribuídos por cluster) ======
    secao_titulo("Indicadores por Cluster", "Os indicadores principais distribuídos por cluster (BA + TT juntos)")

    with area_com_print(
        "dashboard_matriz_geral_cluster", nome_arquivo="indicadores_por_cluster",
        **legenda_filtros("INDICADORES POR CLUSTER", "FECHAMENTO INDICADORES POR CLUSTER"),
    ):
        tabela_matriz(matriz_geral_cluster(df), "Indicadores por Cluster")

    st.divider()

    # ====== PRODUÇÃO POR COORDENADOR (BA + TT consolidado, já destrinchado por supervisor) ======
    secao_titulo(
        "Produção por Coordenador",
        "Visão consolidada (BA + TT) por coordenador e supervisor",
    )
    with area_com_print(
        "dashboard_matriz_coordenadores", nome_arquivo="producao_por_coordenador",
        legenda_template=legenda_producao_ou_fechamento(
            "PRODUÇÃO + ESTEIRA + EFICÁCIA - BA/TT | {estado}{sufixo} (POR GESTÃO) | {data} {hora}",
            "FECHAMENTO PRODUÇÃO BA/TT | {estado}{sufixo} (POR COORDENADOR) | {data} {hora}",
            _datas_sel,
        ),
        legenda_vars={"estado": _estado_legenda, "data": _data_legenda, "sufixo": _sufixo_legenda},
    ):
        render_tabela_coordenadores(tabela_coordenadores(df), total_geral(df))

    st.divider()

    # ====== COMPARATIVO BA VS TT ======
    secao_titulo("Comparativo BA vs TT", "Desempenho lado a lado das duas filas técnicas")

    with area_com_print(
        "dashboard_comparativo_ba_tt", nome_arquivo="comparativo_ba_tt",
        **legenda_filtros("COMPARATIVO BA x TT"),
    ):
        col_ba, col_tt = st.columns(2)

        with col_ba:
            st.markdown(f"<h4 style='color: #00C9A7;'>BA</h4>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                card("Eficácia BA", f"{eficacia['BA']:.0%}", config.TLP_ORANGE)
            with c2:
                card("Média Atrib.", f"{media['BA']:.2f}", "#00C9A7")
            with c3:
                card("PU BA", f"{pu['BA']:.2f}", config.TLP_GOLD,
                     pu_site=pu["BA"], pu_vivo_valor=pu_vivo["BA"])

        with col_tt:
            st.markdown(f"<h4 style='color: {config.TLP_ORANGE};'>TT</h4>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                card("Eficácia TT", f"{eficacia['TT']:.0%}", config.TLP_ORANGE)
            with c2:
                card("Média Atrib.", f"{media['TT']:.2f}", "#7B8CDE")
            with c3:
                card("PU TT", f"{pu['TT']:.2f}", "#FF5C5C",
                     pu_site=pu["TT"], pu_vivo_valor=pu_vivo["TT"])

    st.divider()

    # ====== MATRIZES DE PRODUÇÃO (BA / TT) — Cluster / Coordenador ======
    secao_titulo("Produção", "Detalhamento das filas BA e TT — escolha a visão abaixo")

    # Cada visão usa a mesma matriz de produção, só muda o agrupamento:
    # (coluna do 1º nível, coluna do 2º nível, rótulo da coluna, rótulo do clique)
    VISOES_PRODUCAO = {
        "Cluster": ("Cluster", "Cidade", "CLUSTER / CIDADE", "Cluster"),
        "Coordenador": ("Coordenador", "Supervisor", "COORDENADOR / SUPERVISOR", "Coordenador"),
    }
    visao_prod = st.segmented_control(
        "Visão da produção", options=list(VISOES_PRODUCAO), default="Cluster",
        key="dashboard_visao_producao",
    ) or "Cluster"
    col_g, col_sg, rotulo_grupo, rotulo_clique = VISOES_PRODUCAO[visao_prod]
    chave_visao = visao_prod.lower()
    sufixo_visao = "" if visao_prod == "Cluster" else f" (POR {visao_prod.upper()})"

    def _linha_total(df_matriz):
        """Extrai a linha 'Total' da matriz flat (matriz_producao) como
        dict pronto pra tabela expansível (troca a chave 'Cluster' —
        nome fixo da coluna de rótulo em matriz_producao — por 'Nome')."""
        if df_matriz.empty:
            return None
        linha = df_matriz[df_matriz["Cluster"] == "Total"]
        if linha.empty:
            return None
        total = linha.iloc[0].to_dict()
        total["Nome"] = total.pop("Cluster")
        return total

    for lado, cor in (("BA", "#00C9A7"), ("TT", config.TLP_ORANGE)):
        matriz_lado = matriz_producao(df, lado=lado, coluna_grupo=col_g)
        grupos_lado = matriz_producao_cluster_cidade(
            df, lado=lado, coluna_grupo=col_g, coluna_subgrupo=col_sg
        )
        with area_com_print(
            f"dashboard_matriz_{lado.lower()}_{chave_visao}",
            nome_arquivo=f"producao_{lado.lower()}_{chave_visao}",
            legenda_template=legenda_producao_ou_fechamento(
                f"PRODUÇÃO + ESTEIRA + EFICÁCIA - {lado}{sufixo_visao} | {{estado}}{{sufixo}} | {{data}} {{hora}}",
                f"FECHAMENTO PRODUÇÃO {lado}{sufixo_visao} | {{estado}}{{sufixo}} | {{data}} {{hora}}",
                _datas_sel,
            ),
            legenda_vars={"estado": _estado_legenda, "data": _data_legenda, "sufixo": _sufixo_legenda},
        ):
            tabela_matriz_expansivel(
                grupos_lado, f"PRODUÇÃO {lado}", cor_titulo=cor,
                total=_linha_total(matriz_lado), id_tabela=f"producao_{lado.lower()}_{chave_visao}",
                rotulo_grupo=rotulo_grupo, rotulo_clique=rotulo_clique,
            )
            st.markdown(
                f"<p style='margin:14px 0 2px; font-size:13px; font-weight:600; color:{config.TEXT_MUTED};'>"
                f"Pareto de Pendências — {lado}</p>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                grafico_pareto_causa(df, lado), width='stretch',
                config=opcoes_grafico(f"pareto_pendencias_{lado.lower()}"),
            )

        if lado == "BA":
            st.write("")

    st.divider()

    # ====== GRÁFICOS ======
    secao_titulo("Visão Analítica", "Distribuição de status e evolução diária")

    with area_com_print(
        "dashboard_grafico_status", nome_arquivo="status_geral",
        **legenda_filtros("STATUS GERAL"),
    ):
        st.plotly_chart(grafico_status_pizza(status_counts(df)), width='stretch', config=opcoes_grafico("status_geral"))

    st.write("")
    secao_titulo(
        "Análise P",
        "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6) — escolha a visão abaixo",
    )

    visao_p = st.segmented_control(
        "Visão da Análise P",
        options=["Cluster / Cidade", "Coordenador / Supervisor / Técnico"],
        default="Cluster / Cidade", key="dashboard_visao_analise_p",
    ) or "Cluster / Cidade"

    # Mesmo escopo da Análise P dos cards/resumo (services.indicadores):
    # Contratada = "TLP" e excluindo Supervisor = "BUCKET" — técnicos do
    # bucket não entram na classificação P0..>P3 (obras não concluídas do
    # bucket voltam como sobra pro balde, não contam produtividade do técnico).
    df_analise_p = df
    if "Contratada" in df_analise_p.columns:
        df_analise_p = df_analise_p[df_analise_p["Contratada"] == "TLP"]
    if "Supervisor" in df_analise_p.columns:
        df_analise_p = df_analise_p[df_analise_p["Supervisor"] != "BUCKET"]

    def _linha_total_p(df_resumo, chave_grupo="Cluster"):
        """Extrai a linha 'Total Geral' de contagem/percentual como dict
        pronto pra tabela expansível (troca a chave do agrupamento por
        'Nome')."""
        if df_resumo.empty:
            return None
        linha = df_resumo[df_resumo[chave_grupo] == "Total Geral"]
        if linha.empty:
            return None
        total = linha.iloc[0].to_dict()
        total["Nome"] = total.pop(chave_grupo)
        return total

    if visao_p == "Cluster / Cidade":
        contagem_cluster, percentual_cluster, resumo_cluster = indicadores.analise_p_cluster()
        grupos_analise_p = matriz_analise_p_cluster_cidade(df_analise_p)

        with area_com_print(
            "dashboard_analise_p_cluster", nome_arquivo="analise_p_por_cluster",
            # PZERO parcial (hoje) / FECHAMENTO PZERO (data de ontem pra trás).
            **legenda_filtros("PZERO parcial", "FECHAMENTO PZERO", ligacao=" "),
        ):
            tabela_analise_p_cluster_cidade(
                grupos_analise_p, resumo=resumo_cluster,
                total_contagem=_linha_total_p(contagem_cluster),
                total_percentual=_linha_total_p(percentual_cluster),
                id_tabela="dashboard_analise_p",
            )
    else:
        _, _, resumo_coord = indicadores.analise_p_cluster(coluna_grupo="Coordenador")
        grupos_analise_p_cst = matriz_analise_p_coordenador_supervisor_tecnico(df_analise_p)

        with area_com_print(
            "dashboard_analise_p_coord_sup_tec", nome_arquivo="analise_p_coordenador_supervisor_tecnico",
            **legenda_filtros("PZERO parcial", "FECHAMENTO PZERO", ligacao=" "),
        ):
            tabela_analise_p_coordenador_supervisor_tecnico(
                grupos_analise_p_cst, resumo=resumo_coord,
                id_tabela="dashboard_analise_p_cst",
            )

    st.divider()

    # ====== INDICADORES PRINCIPAIS POR TÉCNICO ======
    secao_titulo("Indicadores Principais por Técnico", "Todos os técnicos do filtro atual e seus indicadores completos")
    matriz_tecnicos = metricas_por_tecnico(df)
    if matriz_tecnicos.empty:
        st.info("Sem técnicos com atividades para os filtros atuais.")
    else:
        matriz_tecnicos = matriz_tecnicos.sort_values("PU", ascending=False).copy()
        colunas_exibir = [c for c in [
            "Técnico", "Supervisor", "Classificação P", "Caixa Total", "Concluído OK", "Concluído NOK",
            "Eficácia", "PU", "Esteira", "Iniciada", "Projeção", "Cluster",
        ] if c in matriz_tecnicos.columns]
        matriz_fmt = matriz_tecnicos[colunas_exibir].copy()
        matriz_fmt["Eficácia"] = matriz_fmt["Eficácia"] * 100
        with area_com_print(
            "dashboard_matriz_tecnicos", nome_arquivo="indicadores_por_tecnico",
            **legenda_filtros("INDICADORES POR TÉCNICO"),
        ):
            st.dataframe(
                matriz_fmt,
                width="stretch",
                hide_index=True,
                column_config={
                    "Eficácia": st.column_config.NumberColumn("Eficácia", format="%.1f%%"),
                    "PU": st.column_config.NumberColumn("PU", format="%.2f"),
                },
            )
