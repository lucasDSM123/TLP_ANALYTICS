import pandas as pd
import streamlit as st

import config
from services import analise_indicador as ai
from components.charts import grafico_evolucao_temporal, grafico_ranking


def render_analise_indicador(df: pd.DataFrame, chave: str, escolha: str):
    """
    Detalhamento do indicador ativo (selecionado na barra de pills do topo
    da página — ver `seletor_indicador_topo`): mostra a quebra por
    Cluster, a evolução ao longo do dia (por faixa horária) com linha de
    média, e o comparativo dia a dia, sempre para o indicador escolhido
    no topo.

    `df` aqui é a base ORIGINAL (não filtrada pelo indicador ativo), pois
    as funções de `services.analise_indicador` já aplicam o filtro do
    indicador internamente, de forma equivalente ao filtro cruzado do
    Power BI.
    """
    meta = ai.INDICADORES[chave]

    tab_cluster, tab_temporal, tab_dia = st.tabs(
        ["📊 Por Cluster", "⏱️ Ao Longo do Dia", "📅 Dia a Dia"]
    )

    with tab_cluster:
        if "Lado" in df.columns:
            dados_ba = ai.valores_por_cluster_lado(df, chave, "BA")
            dados_tt = ai.valores_por_cluster_lado(df, chave, "TT")

            col_ba, col_tt = st.columns(2)
            with col_ba:
                st.markdown(f"<h5 style='color:{config.CHART_BA};'>BA</h5>", unsafe_allow_html=True)
                if dados_ba.empty:
                    st.info("Sem dados de BA para esse indicador com os filtros atuais.")
                else:
                    st.plotly_chart(
                        grafico_ranking(dados_ba, meta["coluna_valor"], f"{escolha} por Cluster — BA"),
                        width="stretch",
                    )
            with col_tt:
                st.markdown(f"<h5 style='color:{config.CHART_TT};'>TT</h5>", unsafe_allow_html=True)
                if dados_tt.empty:
                    st.info("Sem dados de TT para esse indicador com os filtros atuais.")
                else:
                    st.plotly_chart(
                        grafico_ranking(dados_tt, meta["coluna_valor"], f"{escolha} por Cluster — TT"),
                        width="stretch",
                    )
        else:
            dados_cluster = ai.valores_por_cluster(df, chave)
            if dados_cluster.empty:
                st.info("Sem dados suficientes para esse indicador com os filtros atuais.")
            else:
                st.plotly_chart(
                    grafico_ranking(dados_cluster, meta["coluna_valor"], f"{escolha} por Cluster"),
                    width="stretch",
                )

    with tab_temporal:
        if meta["tipo"] != "contagem":
            st.info(
                f"**{escolha}** é uma taxa/média calculada sobre o dia inteiro — "
                "não faz sentido quebrar por faixa de horário. Veja as abas "
                "'Por Cluster' ou 'Dia a Dia'."
            )
        else:
            serie = ai.serie_faixa_horaria(df, meta["filtro"])
            if serie.empty:
                st.info("Sem coluna de horário de término disponível nos dados filtrados.")
            else:
                media = serie["Quantidade"].mean()
                st.plotly_chart(
                    grafico_evolucao_temporal(serie, media, f"{escolha} ao Longo do Dia"),
                    width="stretch",
                )

    with tab_dia:
        serie_dia = ai.serie_diaria(df, chave)
        if serie_dia.empty:
            st.info("Apenas uma data disponível nos filtros atuais — selecione 'Todas' no filtro de Data para comparar dia a dia.")
        else:
            media = serie_dia["Quantidade"].mean()
            st.plotly_chart(
                grafico_evolucao_temporal(serie_dia, media, f"{escolha} — Comparativo Diário"),
                width="stretch",
            )
