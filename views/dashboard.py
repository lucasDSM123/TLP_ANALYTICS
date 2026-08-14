import streamlit as st

from components.cards import card
from components.header import secao_titulo
from components.charts import grafico_status_pizza, grafico_comparativo_ba_tt, grafico_pareto_causa, opcoes_grafico
from components.tabelas import tabela_matriz_expansivel
from components.tabela_analise_p import tabela_analise_p_cluster_cidade
from components.analise_indicador import render_analise_indicador
from components.seletor_indicador import seletor_indicador_topo
from components.print_button import area_com_print
from services.indicadores import Indicadores
from services.grupos import status_counts, matriz_producao, matriz_producao_cluster_cidade
from services.analise_p import matriz_analise_p_cluster_cidade
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

    # ====== INDICADORES PRINCIPAIS ======
    secao_titulo("Indicadores Principais", "Visão consolidada da operação")

    with area_com_print("dashboard_cards_principais", nome_arquivo="indicadores_principais"):
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
            card("PU", f"{pu['GERAL']:.2f}", "#7B8CDE")
        with col6:
            card("PROJEÇÃO PU", f"{projecao_pu['GERAL']:.2f}", "#7B8CDE")

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

    # ====== COMPARATIVO BA VS TT ======
    secao_titulo("Comparativo BA vs TT", "Desempenho lado a lado das duas filas técnicas")

    with area_com_print("dashboard_comparativo_ba_tt", nome_arquivo="comparativo_ba_tt"):
        col_ba, col_tt = st.columns(2)

        with col_ba:
            st.markdown(f"<h4 style='color: #00C9A7;'>BA</h4>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                card("Eficácia BA", f"{eficacia['BA']:.0%}", config.TLP_ORANGE)
            with c2:
                card("Média Atrib.", f"{media['BA']:.2f}", "#00C9A7")
            with c3:
                card("PU BA", f"{pu['BA']:.2f}", config.TLP_GOLD)

        with col_tt:
            st.markdown(f"<h4 style='color: {config.TLP_ORANGE};'>TT</h4>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                card("Eficácia TT", f"{eficacia['TT']:.0%}", config.TLP_ORANGE)
            with c2:
                card("Média Atrib.", f"{media['TT']:.2f}", "#7B8CDE")
            with c3:
                card("PU TT", f"{pu['TT']:.2f}", "#FF5C5C")

    st.divider()

    # ====== MATRIZES DE PRODUÇÃO POR CLUSTER / CIDADE (BA / TT) ======
    secao_titulo("Produção por Cluster", "Detalhamento por cluster e cidade — filas BA e TT")

    def _linha_total(df_matriz):
        """Extrai a linha 'Total' da matriz flat (matriz_producao) como
        dict pronto pra tabela expansível (troca a chave 'Cluster' por
        'Nome')."""
        if df_matriz.empty:
            return None
        linha = df_matriz[df_matriz["Cluster"] == "Total"]
        if linha.empty:
            return None
        total = linha.iloc[0].to_dict()
        total["Nome"] = total.pop("Cluster")
        return total

    matriz_ba = matriz_producao(df, lado="BA")
    grupos_ba = matriz_producao_cluster_cidade(df, lado="BA")
    with area_com_print("dashboard_matriz_ba", nome_arquivo="producao_ba"):
        tabela_matriz_expansivel(
            grupos_ba, "PRODUÇÃO BA", cor_titulo="#00C9A7",
            total=_linha_total(matriz_ba), id_tabela="producao_ba",
        )

    st.write("")

    matriz_tt = matriz_producao(df, lado="TT")
    grupos_tt = matriz_producao_cluster_cidade(df, lado="TT")
    with area_com_print("dashboard_matriz_tt", nome_arquivo="producao_tt"):
        tabela_matriz_expansivel(
            grupos_tt, "PRODUÇÃO TT", cor_titulo=config.TLP_ORANGE,
            total=_linha_total(matriz_tt), id_tabela="producao_tt",
        )

    st.divider()

    # ====== GRÁFICOS ======
    secao_titulo("Visão Analítica", "Distribuição de status e evolução diária")

    with area_com_print("dashboard_grafico_status", nome_arquivo="status_geral"):
        st.plotly_chart(grafico_status_pizza(status_counts(df)), width='stretch', config=opcoes_grafico("status_geral"))

    st.write("")
    secao_titulo("Análise P por Cluster", "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6), com quebra por cidade")
    contagem_cluster, percentual_cluster, resumo_cluster = indicadores.analise_p_cluster()
    grupos_analise_p = matriz_analise_p_cluster_cidade(df)

    def _linha_total_p(df_resumo, chave_grupo="Cluster"):
        """Extrai a linha 'Total Geral' de contagem_cluster/percentual_cluster
        como dict pronto pra tabela expansível (troca a chave do
        agrupamento por 'Nome')."""
        if df_resumo.empty:
            return None
        linha = df_resumo[df_resumo[chave_grupo] == "Total Geral"]
        if linha.empty:
            return None
        total = linha.iloc[0].to_dict()
        total["Nome"] = total.pop(chave_grupo)
        return total

    with area_com_print("dashboard_analise_p_cluster", nome_arquivo="analise_p_por_cluster"):
        tabela_analise_p_cluster_cidade(
            grupos_analise_p, resumo=resumo_cluster,
            total_contagem=_linha_total_p(contagem_cluster),
            total_percentual=_linha_total_p(percentual_cluster),
            id_tabela="dashboard_analise_p",
        )

    secao_titulo("Pareto de Pendências por Causa", "Atividades não concluídas agrupadas por causa — BA vs TT")
    with area_com_print("dashboard_grafico_pareto", nome_arquivo="pareto_pendencias"):
        st.plotly_chart(grafico_pareto_causa(df), width='stretch', config=opcoes_grafico("pareto_pendencias"))

    st.divider()

    # ====== INDICADOR EM FOCO ======
    # Fica logo acima de "Detalhamento", afetando apenas a quebra por
    # cluster/hora/dia mostrada nessa seção — não interfere nos cards e
    # gráficos acima (Indicadores Principais, Comparativo, Produção,
    # Visão Analítica), que continuam refletindo os filtros do topo do
    # site normalmente.
    secao_titulo("Indicador em Foco", "Clique em um indicador para filtrar o detalhamento abaixo")
    _, chave_ativa, escolha_ativa, _ = seletor_indicador_topo(df)

    st.divider()

    # ====== DETALHAMENTO DO INDICADOR SELECIONADO ACIMA ======
    if chave_ativa:
        secao_titulo(
            f"Detalhamento — {escolha_ativa}",
            "Quebra por cluster, evolução ao longo do dia e comparativo dia a dia do indicador selecionado acima",
        )
        render_analise_indicador(df, chave_ativa, escolha_ativa)
    else:
        secao_titulo("Detalhamento por Indicador", "Selecione um indicador em foco acima para ver a quebra por cluster, hora e dia")
        st.info("Nenhum indicador em foco no momento. Clique em um indicador em \"Indicador em Foco\", acima, para detalhar aqui.")

    st.divider()

    # ====== RESUMO GERAL ======
    with st.expander("📊 Detalhes Adicionais"):
        with area_com_print("dashboard_detalhes_adicionais", nome_arquivo="detalhes_adicionais"):
            col1, col2, col3 = st.columns(3)

            with col1:
                card("Suspensa", caixa["SUSPENSA"], "#9EA4B5")
                card("Cancelada", caixa["CANCELADA"], config.TLP_RED)

            with col2:
                card("Média Atribuição Geral", f"{media['GERAL']:.2f}", "#7B8CDE")
                card("Concluído Geral", concluido["GERAL"], config.TLP_GOLD)

            with col3:
                card("Projeção BA", projecao["BA"], "#00C9A7")
                card("Projeção TT", projecao["TT"], "#FF5C5C")
                card("Projeção PU", f"{projecao_pu['GERAL']:.2f}", "#7B8CDE")