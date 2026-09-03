import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.charts import (
    grafico_eficacia_diaria, grafico_produtividade_diaria, cabecalho_grafico_combo, opcoes_grafico,
)
from components.tabelas import tabela_fechamento_diario, tabela_consolidado_grupo, tabela_comparativo_mensal
from components.print_button import area_com_print, sanitizar_chave
from services.grupos import serie_diaria_por_grupo, resumo_mes_por_grupo, resumo_mes_total
from services import historico_mensal

# Dimensões disponíveis para o fechamento mensal — rótulo exibido -> nome da coluna no df
DIMENSOES = {"Estado": "Estado", "Cluster": "Cluster"}

_MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}


def _rotulo_mes_atual(df_dia_grupo: pd.DataFrame) -> str:
    """Nome do mês corrente (em maiúsculas) com base na data mais recente
    presente na série diária do grupo — usado como cabeçalho da coluna
    'mês atual' na tabela comparativa."""
    if df_dia_grupo.empty or "Data" not in df_dia_grupo.columns:
        return "MÊS ATUAL"
    try:
        return _MESES_PT.get(df_dia_grupo["Data"].max().month, "MÊS ATUAL")
    except AttributeError:
        return "MÊS ATUAL"


def _linha_total_para_comparativo(linha_total: dict) -> dict:
    """Converte a linha de total (chaves em PT-BR, como vem de
    resumo_mes_por_grupo/_linha_resumo_soma) para o formato de chaves
    usado em services.historico_mensal (minúsculas/sem acento), permitindo
    comparar o mês corrente (calculado ao vivo) com o mês anterior
    (congelado)."""
    return {
        "eficacia": linha_total.get("Eficácia"),
        "concluida": linha_total.get("Concluída"),
        "improdutiva": linha_total.get("Improdutiva"),
        "tecnicos": linha_total.get("Técnicos"),
        "atribuicao": linha_total.get("Atribuição"),
        "pu": linha_total.get("PU"),
    }


def _com_total_mes(df_dia: pd.DataFrame, linha_total: dict, coluna_grupo: str) -> pd.DataFrame:
    """Anexa a linha 'Total Mês' (vinda de resumo_mes_por_grupo) ao final
    da série diária de um grupo, no formato esperado por tabela_fechamento_diario."""
    if df_dia.empty:
        return df_dia
    total = {"Data": "Total Mês"}
    total.update({k: v for k, v in linha_total.items() if k != coluna_grupo})
    return pd.concat([df_dia, pd.DataFrame([total])], ignore_index=True)


def _cor_grupo(indice: int, valor: str, coluna_grupo: str) -> str:
    """Cor do grupo: fixa (marca) para Estado, cíclica na paleta do site para outras dimensões (ex.: Cluster)."""
    if coluna_grupo == "Estado":
        return "#00C9A7" if valor == "SC" else config.TLP_ORANGE
    return config.CHART_COLORWAY[indice % len(config.CHART_COLORWAY)]


def render(df, indicadores):

    secao_titulo("Acumulado Mês", "Fechamento mensal consolidado — réplica do PAINEL do Excel/Power BI")

    # ====== RESUMO GERAL DO PERÍODO FILTRADO ======
    hc = indicadores.hc_real()
    concluido = indicadores.concluido()
    eficacia = indicadores.eficacia()

    # PU e Atribuição do resumo geral seguem a MESMA regra do Total das
    # tabelas abaixo (soma da Concluída/Caixa Total/Técnicos de cada dia e
    # só então divide) — NÃO usar indicadores.pu()/media_atribuicao() direto
    # aqui, pois eles contam Técnicos como únicos do período inteiro (um
    # número bem menor que a soma diária), o que inflava o PU exibido no
    # card muito acima do valor real (visto na matriz/Total logo abaixo).
    total_geral = resumo_mes_total(df) or {}
    pu_geral = total_geral.get("PU", 0.0)
    atribuicao_geral = total_geral.get("Atribuição", 0.0)

    with area_com_print("acumulado_mes_cards_resumo", nome_arquivo="resumo_geral_acumulado_mes"):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            card("TÉCNICOS", hc["HC"], config.TLP_ORANGE, f"BA: {hc['BA']} | TT: {hc['TT']}")
        with col2:
            card("CONCLUÍDA", f"{concluido['OK']:,}".replace(",", "."), "#15803D")
        with col3:
            card("IMPRODUTIVA", f"{concluido['NOK']:,}".replace(",", "."), config.TLP_RED)
        with col4:
            card("EFICÁCIA", f"{eficacia['GERAL']:.0%}", config.TLP_GOLD, f"Meta: {config.META_EFICACIA_ALVO:.0%}")
        with col5:
            card("ATRIBUIÇÃO", f"{atribuicao_geral:.2f}", "#7B8CDE", f"Meta: {config.META_ATRIBUICAO_ALVO:.1f}")
        with col6:
            card("PU", f"{pu_geral:.2f}", "#00C9A7", f"Meta: {config.META_PU_ALVO:.1f}")

    st.divider()

    # ====== SELETOR DE DIMENSÃO (Estado ou Cluster) ======
    dimensoes_disponiveis = {rotulo: col for rotulo, col in DIMENSOES.items() if col in df.columns}

    if not dimensoes_disponiveis:
        st.info("Nenhuma coluna de agrupamento (Estado/Cluster) disponível na base filtrada.")
        return

    rotulo_dim = st.radio(
        "Agrupar fechamento por",
        options=list(dimensoes_disponiveis.keys()),
        horizontal=True,
        key="acumulado_mes_dimensao",
    )
    coluna_grupo = dimensoes_disponiveis[rotulo_dim]

    st.divider()

    # ====== CONSOLIDADO POR GRUPO (Estado ou Cluster) ======
    secao_titulo(f"Consolidado por {rotulo_dim}", f"Totais acumulados do mês — cada {rotulo_dim.lower()} e o Total geral")
    resumo_grupo = resumo_mes_por_grupo(df, coluna_grupo)
    with area_com_print("acumulado_mes_consolidado", nome_arquivo=f"consolidado_por_{coluna_grupo}"):
        tabela_consolidado_grupo(resumo_grupo, f"TOTAL DO MÊS POR {rotulo_dim.upper()}", coluna_grupo)

    st.divider()

    # ====== FECHAMENTO DIÁRIO DETALHADO POR GRUPO ======
    secao_titulo("Fechamento Diário", f"Detalhamento dia a dia por {rotulo_dim.lower()}, com o total do mês ao final")

    serie_grupo = serie_diaria_por_grupo(df, coluna_grupo)

    if resumo_grupo.empty or serie_grupo.empty:
        st.info("Sem dados para os filtros selecionados.")
    else:
        grupos = [g for g in resumo_grupo[coluna_grupo] if g != "Total"]
        abas = st.tabs(grupos) if grupos else []

        for i, (aba, grupo) in enumerate(zip(abas, grupos)):
            with aba:
                df_dia_grupo = (
                    serie_grupo[serie_grupo[coluna_grupo] == grupo]
                    .drop(columns=[coluna_grupo])
                    .sort_values("Data")
                )
                linha_total = resumo_grupo[resumo_grupo[coluna_grupo] == grupo].iloc[0].to_dict()
                cor = _cor_grupo(i, grupo, coluna_grupo)

                mes_anterior = historico_mensal.fechamento_mes_anterior(
                    grupo, coluna_grupo, data_referencia=df_dia_grupo["Data"].max() if not df_dia_grupo.empty else None,
                )
                if mes_anterior:
                    with area_com_print(f"acumulado_mes_comparativo_{grupo}",
                                         nome_arquivo=f"comparativo_mensal_{grupo}"):
                        tabela_comparativo_mensal(
                            grupo, mes_anterior, _linha_total_para_comparativo(linha_total),
                            rotulo_mes_anterior=historico_mensal.rotulo_mes_anterior(
                                df_dia_grupo["Data"].max() if not df_dia_grupo.empty else None,
                            ),
                            rotulo_mes_atual=_rotulo_mes_atual(df_dia_grupo),
                        )
                    st.write("")

                with area_com_print(f"acumulado_mes_fechamento_{grupo}",
                                     nome_arquivo=f"fechamento_diario_{grupo}"):
                    tabela_fechamento_diario(
                        _com_total_mes(df_dia_grupo, linha_total, coluna_grupo),
                        f"FECHAMENTO DIÁRIO — {grupo}", cor_titulo=cor,
                    )

                num_dias = len(df_dia_grupo)
                largura_minima = max(760, num_dias * 65)

                chave_efic = sanitizar_chave(f"acumulado_mes_eficacia_{grupo}")
                with area_com_print(f"acumulado_mes_eficacia_{grupo}",
                                     nome_arquivo=f"eficacia_diaria_{grupo}"):
                    st.markdown(
                        f"<style>.st-key-{chave_efic} [data-testid='stPlotlyChart']"
                        f"{{min-width:{largura_minima}px;}}</style>"
                        + cabecalho_grafico_combo("Eficácia Diária", [
                            ("Concluída", "#15803D", "barra"),
                            ("Improdutiva", config.TLP_RED, "barra"),
                            ("Eficácia %", config.TEXT_MUTED, "linha"),
                        ]),
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        grafico_eficacia_diaria(df_dia_grupo), width='stretch',
                        key=f"acumulado_mes_eficacia_chart_{grupo}",
                        config=opcoes_grafico(f"eficacia_diaria_{grupo}"),
                    )

                st.write("")

                chave_prod = sanitizar_chave(f"acumulado_mes_produtividade_{grupo}")
                with area_com_print(f"acumulado_mes_produtividade_{grupo}",
                                     nome_arquivo=f"produtividade_diaria_{grupo}"):
                    st.markdown(
                        f"<style>.st-key-{chave_prod} [data-testid='stPlotlyChart']"
                        f"{{min-width:{largura_minima}px;}}</style>"
                        + cabecalho_grafico_combo("Produtividade Diária", [
                            ("Técnicos", config.TEXT, "barra"),
                            ("PU", config.TLP_ORANGE, "linha"),
                        ]),
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        grafico_produtividade_diaria(df_dia_grupo), width='stretch',
                        key=f"acumulado_mes_produtividade_chart_{grupo}",
                        config=opcoes_grafico(f"produtividade_diaria_{grupo}"),
                    )
