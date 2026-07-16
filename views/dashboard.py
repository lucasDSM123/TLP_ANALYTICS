import streamlit as st

from components.cards import card
from components.header import secao_titulo
from components.charts import grafico_status_pizza, grafico_comparativo_ba_tt, grafico_pareto_causa
from components.tabelas import tabela_matriz
from components.tabela_analise_p import tabela_analise_p_cluster
from components.analise_indicador import render_analise_indicador
from components.seletor_indicador import seletor_indicador_topo
from services.indicadores import Indicadores
from services.grupos import status_counts, matriz_producao
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

    # ====== MATRIZES DE PRODUÇÃO POR CLUSTER (BA / TT) ======
    secao_titulo("Produção por Cluster", "Detalhamento por cluster — filas BA e TT")

    matriz_ba = matriz_producao(df, lado="BA")
    tabela_matriz(matriz_ba, "PRODUÇÃO BA", cor_titulo="#00C9A7")

    st.write("")

    matriz_tt = matriz_producao(df, lado="TT")
    tabela_matriz(matriz_tt, "PRODUÇÃO TT", cor_titulo=config.TLP_ORANGE)

    st.divider()

    # ====== GRÁFICOS ======
    secao_titulo("Visão Analítica", "Distribuição de status e evolução diária")

    st.plotly_chart(grafico_status_pizza(status_counts(df)), width='stretch')

    st.write("")
    secao_titulo("Análise P por Cluster", "Distribuição de técnicos por faixa de produtividade (P0..P5/P≥6)")
    contagem_cluster, percentual_cluster, resumo_cluster = indicadores.analise_p_cluster()
    tabela_analise_p_cluster(contagem_cluster, percentual_cluster, resumo_cluster)

    secao_titulo("Pareto de Pendências por Causa", "Atividades não concluídas agrupadas por causa — BA vs TT")
    st.plotly_chart(grafico_pareto_causa(df), width='stretch')

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