import streamlit as st
import pandas as pd

import config
from components.header import secao_titulo
from components.cards import card
from components.charts import (
    grafico_pareto_generico, grafico_ranking, grafico_heatmap_causa, opcoes_grafico,
)
from components.tabela_score import tabela_score_performance
from components.print_button import area_com_print
from services.indicadores import Indicadores
from services import analitica as an

DIMENSOES_TEMPO = ["Tipo de Atividade", "Cidade", "Cluster", "Supervisor", "Coordenador"]
NIVEIS_SCORE = {"Técnico": "Técnico", "Supervisor": "Supervisor", "Coordenador": "Coordenador"}
GRUPOS_DIAGNOSTICO = ["Coordenador", "Supervisor", "Cidade", "Cluster"]


@st.cache_data(show_spinner=False)
def _score_performance_cache(df: pd.DataFrame, coluna_grupo: str, meta_pu: float, caixa_minima: int) -> pd.DataFrame:
    """Cache do Score de Performance — metricas_por_grupo (services/grupos.py)
    monta um objeto Indicadores por grupo, o que fica pesado com muitos
    técnicos (200+). Sem cache, o cálculo roda de novo a cada interação na
    página inteira (st.tabs renderiza as 3 abas em toda execução)."""
    return an.score_performance(df, coluna_grupo, meta_pu=meta_pu, caixa_minima=caixa_minima)


def render(df: pd.DataFrame, indicadores: Indicadores):
    secao_titulo(
        "Analítica",
        "Por que não concluímos, onde a operação demora mais e quem está performando bem (ou mal) — "
        "Técnico, Supervisor e Coordenador.",
    )

    if df.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    # ================================================================
    # RESUMO GERAL
    # ================================================================
    concluido = indicadores.concluido()
    caixa = indicadores.caixa_total()
    total_os = len(df)
    total_nao_concl = concluido["NOK"]
    total_cancel = caixa["CANCELADA"]
    pct_nao_concl = (total_nao_concl / caixa["TOTAL"] * 100) if caixa["TOTAL"] else 0
    resumo_dur = an.resumo_duracao_geral(df)

    with area_com_print("analitica_cards_resumo", nome_arquivo="analitica_resumo_geral"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            card("OS no Recorte", f"{total_os:,}".replace(",", "."), config.TLP_ORANGE, icon="🗂️")
        with c2:
            card("Não Concluída", f"{total_nao_concl:,}".replace(",", "."), config.TLP_RED,
                 subtitle=f"{pct_nao_concl:.1f}% da Caixa Total")
        with c3:
            card("Cancelada", f"{total_cancel:,}".replace(",", "."), config.TLP_GOLD)
        with c4:
            card("Duração Média (execução)", an.formatar_minutos(resumo_dur["media_min"]), "#7B8CDE",
                 subtitle=f"Mediana: {an.formatar_minutos(resumo_dur['mediana_min'])}", icon="⏱️")

    st.divider()

    # ================================================================
    # SEÇÃO 1 — CAUSAS DE NÃO CONCLUSÃO E CANCELAMENTO (PARETO)
    # ================================================================
    secao_titulo("Por que não concluímos?", "Pareto das causas de Não Conclusão e de Cancelamento")

    col_nc, col_ca = st.columns(2)

    with col_nc:
        st.markdown("**Não Concluída** (Causa R1)")
        pareto_nc = an.pareto_causas(df, "Não Concluída")
        with area_com_print("analitica_pareto_nao_concluida", nome_arquivo="pareto_nao_concluida"):
            st.plotly_chart(
                grafico_pareto_generico(pareto_nc, ""), width='stretch',
                config=opcoes_grafico("pareto_nao_concluida"),
            )
        if not pareto_nc.empty:
            with st.expander("Ver todas as causas"):
                st.dataframe(pareto_nc, hide_index=True, width='stretch')

    with col_ca:
        st.markdown("**Cancelada** (Motivo/Pendência)")
        pareto_ca = an.pareto_causas(df, "Cancelada")
        with area_com_print("analitica_pareto_cancelada", nome_arquivo="pareto_cancelada"):
            st.plotly_chart(
                grafico_pareto_generico(pareto_ca, ""), width='stretch',
                config=opcoes_grafico("pareto_cancelada"),
            )
        if not pareto_ca.empty:
            with st.expander("Ver todas as causas"):
                st.dataframe(pareto_ca, hide_index=True, width='stretch')

    st.caption(
        "🧭 **Natureza da causa** (classificação heurística por palavra-chave, não é uma verdade absoluta): "
        "**Externa** = fora do controle direto da operação (cliente ausente, casa fechada, chuva, endereço...); "
        "**Operacional** = ligada à rede/execução/gestão (técnica, rede externa/interna, retenção, sobra de esteira...). "
        "Use como ponto de partida pra separar 'o que o mercado nos impôs' de 'o que dá pra melhorar internamente'."
    )

    col_nat_nc, col_nat_ca = st.columns(2)
    with col_nat_nc:
        nat_nc = an.resumo_natureza_causa(df, "Não Concluída")
        if not nat_nc.empty:
            st.dataframe(nat_nc, hide_index=True, width='stretch')
    with col_nat_ca:
        nat_ca = an.resumo_natureza_causa(df, "Cancelada")
        if not nat_ca.empty:
            st.dataframe(nat_ca, hide_index=True, width='stretch')

    st.divider()

    # ================================================================
    # SEÇÃO 2 — DIAGNÓSTICO CRUZADO (CAUSA x GRUPO)
    # ================================================================
    secao_titulo(
        "Causa é geral ou concentrada em algum time?",
        "Cruzamento das causas mais frequentes com Coordenador / Supervisor / Cidade / Cluster",
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_diag = st.selectbox(
            "Status", ["Não Concluída", "Cancelada"], key="analitica_diag_status",
        )
    with col_f2:
        grupo_diag = st.selectbox(
            "Agrupar por", [g for g in GRUPOS_DIAGNOSTICO if g in df.columns], key="analitica_diag_grupo",
        )

    heatmap_dados = an.matriz_heatmap_causa(df, status_diag, grupo_diag)
    with area_com_print(
        f"analitica_heatmap_{status_diag}_{grupo_diag}",
        nome_arquivo=f"heatmap_{status_diag}_{grupo_diag}".lower().replace(" ", "_"),
    ):
        st.plotly_chart(
            grafico_heatmap_causa(heatmap_dados, ""), width='stretch',
            config=opcoes_grafico(f"heatmap_{status_diag}_{grupo_diag}"),
        )

    tabela_causa_grupo = an.causa_principal_por_grupo(df, status_diag, grupo_diag)
    if not tabela_causa_grupo.empty:
        with st.expander(f"Ver tabela detalhada — {status_diag} por {grupo_diag}"):
            st.dataframe(tabela_causa_grupo, hide_index=True, width='stretch')

    st.divider()

    # ================================================================
    # SEÇÃO 3 — TEMPO DE EXECUÇÃO (ONDE DEMORAMOS MAIS)
    # ================================================================
    secao_titulo(
        "Onde a operação demora mais?",
        "Duração real de execução em campo (Término − Início) das OS Concluídas — não confundir com tempo de "
        "espera até o início, que já é tratado na aba Chegada",
    )

    dimensao = st.selectbox(
        "Ver duração média por", [d for d in DIMENSOES_TEMPO if d in df.columns], key="analitica_dim_tempo",
    )
    tabela_tempo = an.duracao_por_grupo(df, dimensao)

    if tabela_tempo.empty:
        st.info("Sem amostras suficientes de duração para esta dimensão no recorte atual.")
    else:
        col_g, col_t = st.columns([1, 1])
        with col_g:
            with area_com_print(f"analitica_grafico_duracao_{dimensao}", nome_arquivo=f"duracao_media_por_{dimensao}"):
                st.plotly_chart(
                    grafico_ranking(
                        tabela_tempo[[dimensao, "Duração Média (min)"]], "Duração Média (min)",
                        f"Top — Duração Média por {dimensao}",
                    ),
                    width='stretch',
                    config=opcoes_grafico(f"duracao_media_por_{dimensao}"),
                )
        with col_t:
            with area_com_print(f"analitica_tabela_duracao_{dimensao}", nome_arquivo=f"tabela_duracao_por_{dimensao}"):
                st.dataframe(tabela_tempo, hide_index=True, width='stretch')

    st.divider()

    # ================================================================
    # SEÇÃO 4 — REINCIDÊNCIA / RETRABALHO
    # ================================================================
    secao_titulo("Reincidência / Retrabalho", "Quem tem mais OS com 'Defeito Repetido' — indício de retrabalho")

    dimensao_reinc = st.selectbox(
        "Ver reincidência por", [d for d in ["Técnico", "Supervisor", "Coordenador", "Cidade"] if d in df.columns],
        key="analitica_dim_reinc",
    )
    tabela_reinc = an.reincidencia_por_grupo(df, dimensao_reinc)
    tabela_reinc = tabela_reinc[tabela_reinc["Total OS"] >= 5] if not tabela_reinc.empty else tabela_reinc

    if tabela_reinc.empty:
        st.info("Sem amostras suficientes de reincidência para esta dimensão no recorte atual.")
    else:
        col_g, col_t = st.columns([1, 1])
        with col_g:
            with area_com_print(f"analitica_grafico_reinc_{dimensao_reinc}", nome_arquivo=f"reincidencia_por_{dimensao_reinc}"):
                st.plotly_chart(
                    grafico_ranking(
                        tabela_reinc[[dimensao_reinc, "Taxa Reincidência"]], "Taxa Reincidência",
                        f"Top — Taxa de Reincidência por {dimensao_reinc}",
                    ),
                    width='stretch',
                    config=opcoes_grafico(f"reincidencia_por_{dimensao_reinc}"),
                )
        with col_t:
            with area_com_print(f"analitica_tabela_reinc_{dimensao_reinc}", nome_arquivo=f"tabela_reincidencia_{dimensao_reinc}"):
                st.dataframe(tabela_reinc, hide_index=True, width='stretch')

    st.divider()

    # ================================================================
    # SEÇÃO 5 — PONTUALIDADE / CHEGADA NA JANELA
    # ================================================================
    secao_titulo(
        "Pontualidade — chegada dentro da Janela",
        "Técnico atrasado compromete o resto da agenda do dia. Aqui entra direto no diagnóstico de performance "
        "(e também pesa no Score, mais abaixo) — o detalhamento minuto a minuto continua na aba Chegada.",
    )

    dimensao_pont = st.selectbox(
        "Ver pontualidade por", [d for d in ["Técnico", "Supervisor", "Coordenador", "Cidade"] if d in df.columns],
        key="analitica_dim_pontualidade",
    )
    tabela_pont = an.pontualidade_por_grupo(df, dimensao_pont)
    tabela_pont = tabela_pont[tabela_pont["Total"] >= 5] if not tabela_pont.empty else tabela_pont
    ranking_atrasos = an.ranking_ofensores_pontualidade(df, dimensao_pont, top_n=10)

    if tabela_pont.empty:
        st.info("Sem amostras suficientes de pontualidade para esta dimensão no recorte atual.")
    else:
        geral_pont = an.pontualidade_por_grupo(df, dimensao_pont)
        pct_dentro_geral = (
            tabela_pont["Dentro"].sum() / tabela_pont["Total"].sum() * 100
        ) if tabela_pont["Total"].sum() else 0

        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            card("% Dentro da Janela (geral)", f"{pct_dentro_geral:.1f}%", "#15803D" if pct_dentro_geral >= 80 else config.TLP_GOLD)
        with cc2:
            card("OS avaliadas", f"{int(tabela_pont['Total'].sum()):,}".replace(",", "."), config.TLP_ORANGE)
        with cc3:
            card(f"{dimensao_pont}s no ranking", tabela_pont.shape[0], "#7B8CDE")

        col_g, col_t = st.columns([1, 1])
        with col_g:
            with area_com_print(f"analitica_grafico_ofensores_{dimensao_pont}", nome_arquivo=f"ofensores_atraso_{dimensao_pont}"):
                if not ranking_atrasos.empty:
                    st.plotly_chart(
                        grafico_ranking(
                            ranking_atrasos[[dimensao_pont, "% Depois"]], "% Depois",
                            f"5 Maiores Ofensores de Atraso — {dimensao_pont}", top_n=5,
                        ),
                        width='stretch', config=opcoes_grafico(f"ofensores_atraso_{dimensao_pont}"),
                    )
                else:
                    st.info("Ninguém com atraso registrado neste recorte.")
        with col_t:
            with area_com_print(f"analitica_tabela_pontualidade_{dimensao_pont}", nome_arquivo=f"tabela_pontualidade_{dimensao_pont}"):
                st.dataframe(
                    tabela_pont.sort_values("% Dentro").reset_index(drop=True),
                    hide_index=True, width='stretch',
                )

    st.divider()

    # ================================================================
    # SEÇÃO 6 — SCORE DE PERFORMANCE (RANKING TÉCNICO/SUPERVISOR/COORDENADOR)
    # ================================================================
    secao_titulo(
        "Ranking de Performance — Destaque x Atenção x Ofensor",
        "Score 0-100 combinando Eficácia, PU, % Não Concluída, Reincidência e Duração média de execução",
    )
    st.caption(
        "📐 **Como o Score é calculado:** 30% Eficácia + 20% PU médio/dia (vs. meta de "
        f"{config.META_PU_ALVO:.1f}, corrigido pra técnico-dia — ver nota abaixo) + 15% % Não Concluída + "
        "20% Pontualidade (chegada dentro da Janela) + 8% Taxa de Reincidência + 7% Duração média de execução — "
        "todos normalizados dentro do próprio recorte selecionado. Grupos com poucas OS na Caixa Total ficam de "
        "fora do ranking (amostra pequena demais pra comparar de forma justa)."
    )
    st.caption(
        "ℹ️ **Sobre o PU desta tabela:** aqui o PU é OS Concluída ÷ técnico-dia (dias efetivamente trabalhados), "
        "não o PU oficial do site (OK ÷ HC). Em recorte de vários dias por técnico, o PU oficial tende a virar uma "
        "soma do período em vez de uma taxa — essa versão é a média diária de fato."
    )

    abas = st.tabs(list(NIVEIS_SCORE.keys()))
    for aba, (rotulo, coluna_grupo) in zip(abas, NIVEIS_SCORE.items()):
        with aba:
            if coluna_grupo not in df.columns:
                st.info(f"Coluna '{coluna_grupo}' não encontrada na base.")
                continue

            caixa_minima = 5 if coluna_grupo == "Técnico" else 15
            tabela_score = _score_performance_cache(df, coluna_grupo, config.META_PU_ALVO, caixa_minima)

            if tabela_score.empty:
                st.info(f"Sem {rotulo.lower()}s com amostra suficiente (mínimo {caixa_minima} OS na Caixa Total) neste recorte.")
                continue

            n_destaque = (tabela_score["Classificação"] == "Destaque").sum()
            n_atencao = (tabela_score["Classificação"] == "Atenção").sum()
            n_ofensor = (tabela_score["Classificação"] == "Ofensor").sum()

            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                card(f"{rotulo}s Avaliados", tabela_score.shape[0], config.TLP_ORANGE)
            with cc2:
                card("Destaque", int(n_destaque), "#15803D", icon="🏆")
            with cc3:
                card("Atenção", int(n_atencao), config.TLP_GOLD, icon="⚠️")
            with cc4:
                card("Ofensor", int(n_ofensor), config.TLP_RED, icon="🚩")

            top5 = tabela_score.head(5)[[coluna_grupo, "Score"]]
            bottom5 = tabela_score.tail(5).sort_values("Score")[[coluna_grupo, "Score"]]

            col_top, col_bottom = st.columns(2)
            with col_top:
                with area_com_print(f"analitica_top5_{coluna_grupo}", nome_arquivo=f"top5_{coluna_grupo.lower()}"):
                    st.plotly_chart(
                        grafico_ranking(top5, "Score", f"Top 5 — {rotulo}", top_n=5),
                        width='stretch', config=opcoes_grafico(f"top5_{coluna_grupo.lower()}"),
                    )
            with col_bottom:
                with area_com_print(f"analitica_bottom5_{coluna_grupo}", nome_arquivo=f"bottom5_{coluna_grupo.lower()}"):
                    st.plotly_chart(
                        grafico_ranking(bottom5, "Score", f"5 Ofensores — {rotulo}", top_n=5),
                        width='stretch', config=opcoes_grafico(f"bottom5_{coluna_grupo.lower()}"),
                    )

            with area_com_print(f"analitica_tabela_score_{coluna_grupo}", nome_arquivo=f"ranking_score_{coluna_grupo.lower()}"):
                st.markdown(
                    tabela_score_performance(tabela_score, coluna_grupo), unsafe_allow_html=True,
                )
