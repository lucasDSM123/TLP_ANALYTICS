import pandas as pd
import streamlit as st

import config
from components.cards import card

_CORES_FAIXA = {
    "P0": config.TLP_RED,
    "P1": config.TLP_ORANGE,
    "P2": config.TLP_GOLD,
    "P3": "#00C9A7",
    ">P3": "#22C55E",
}
_FAIXAS = ["P0", "P1", "P2", "P3", ">P3"]


def tabela_analise_p(df_matriz: pd.DataFrame, coluna_grupo: str, titulo: str = "Análise P — Produtividade"):
    """
    Renderiza a matriz P0..>P3 como tabela HTML estilizada, réplica visual
    da tabela "PRODUTIVIDADE POR SUPERVISOR - TÉCNICO" do Power BI (uma
    coluna por faixa, cores por faixa, linha de TOTAL em destaque).
    """
    if df_matriz.empty or coluna_grupo not in df_matriz.columns:
        st.info(f"Sem dados de {coluna_grupo} para os filtros atuais.")
        return

    linhas_html = []
    for _, row in df_matriz.iterrows():
        is_total = str(row[coluna_grupo]).upper() == "TOTAL"
        peso = "700" if is_total else "500"
        bg = "rgba(255,106,0,0.08)" if is_total else "transparent"
        borda = f"border-top: 2px solid {config.CARD_BORDER};" if is_total else ""

        celulas = [f"<td style=\"text-align:left; font-weight:{peso};\">{row[coluna_grupo]}</td>"]
        for faixa in _FAIXAS:
            cor = _CORES_FAIXA[faixa]
            valor = int(row[faixa])
            celulas.append(f"<td style=\"color:{cor}; font-weight:{peso};\">{valor}</td>")
        linhas_html.append(f"<tr style=\"background:{bg}; {borda}\">{''.join(celulas)}</tr>")

    header_html = f"<th style=\"text-align:left;\">{coluna_grupo.upper()}</th>" + "".join(
        f"<th style=\"text-align:center; color:{_CORES_FAIXA[f]};\">{f}</th>" for f in _FAIXAS
    )

    html = (
        f"<h5 style=\"color:{config.TEXT}; margin-bottom:6px;\">{titulo}</h5>"
        f"<div style=\"overflow-x:auto; border:1px solid {config.CARD_BORDER}; border-radius:10px;\">"
        f"<table style=\"width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};\">"
        f"<thead><tr style=\"background:{config.SURFACE}; color:{config.TEXT_MUTED};\">{header_html}</tr></thead>"
        f"<tbody style=\"text-align:center;\">{''.join(linhas_html)}</tbody>"
        f"</table>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


_FAIXAS_DETALHADO = ["P0", "P1", "P2", "P3", "P4", "P5", "P≥6"]
_CORES_FAIXA_DETALHADO = {
    "P0": config.TLP_RED,
    "P1": config.TLP_ORANGE,
    "P2": config.TLP_GOLD,
    "P3": "#00C9A7",
    "P4": "#7B8CDE",
    "P5": "#3B82F6",
    "P≥6": "#22C55E",
}


def _tabela_html(df_tabela: pd.DataFrame, coluna_grupo: str, formato_percentual: bool = False) -> str:
    linhas_html = []
    for _, row in df_tabela.iterrows():
        is_total = str(row[coluna_grupo]).upper() in ("TOTAL", "TOTAL GERAL")
        peso = "700" if is_total else "500"
        bg = "rgba(255,106,0,0.08)" if is_total else "transparent"
        borda = f"border-top: 2px solid {config.CARD_BORDER};" if is_total else ""

        celulas = [f"<td style=\"text-align:left; font-weight:{peso};\">{row[coluna_grupo]}</td>"]
        for faixa in _FAIXAS_DETALHADO:
            cor = _CORES_FAIXA_DETALHADO[faixa]
            valor = row[faixa]
            texto = f"{valor:.1f}%" if formato_percentual else f"{int(valor)}"
            celulas.append(f"<td style=\"color:{cor}; font-weight:{peso};\">{texto}</td>")
        if not formato_percentual and "TOTAL" in df_tabela.columns:
            celulas.append(f"<td style=\"font-weight:{peso}; color:{config.TEXT};\">{int(row['TOTAL'])}</td>")
        linhas_html.append(f"<tr style=\"background:{bg}; {borda}\">{''.join(celulas)}</tr>")

    colunas_extra_header = "<th style=\"text-align:center;\">TOTAL</th>" if (not formato_percentual and "TOTAL" in df_tabela.columns) else ""
    header_html = f"<th style=\"text-align:left;\">{coluna_grupo.upper()}</th>" + "".join(
        f"<th style=\"text-align:center; color:{_CORES_FAIXA_DETALHADO[f]};\">{f}{'%' if formato_percentual else ''}</th>"
        for f in _FAIXAS_DETALHADO
    ) + colunas_extra_header

    return (
        f"<div style=\"overflow-x:auto; border:1px solid {config.CARD_BORDER}; border-radius:10px;\">"
        f"<table style=\"width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT};\">"
        f"<thead><tr style=\"background:{config.SURFACE}; color:{config.TEXT_MUTED};\">{header_html}</tr></thead>"
        f"<tbody style=\"text-align:center;\">{''.join(linhas_html)}</tbody>"
        f"</table>"
        f"</div>"
    )


def tabela_analise_p_cluster(contagem: pd.DataFrame, percentual: pd.DataFrame, resumo: dict, coluna_grupo: str = "Cluster"):
    """
    Renderiza a Análise P por Cluster: cards de resumo (Técnicos P0 / P1 /
    Total) + tabela de contagem e tabela de percentual lado a lado —
    réplica visual do site de referência (Power BI).
    """
    if contagem.empty or percentual.empty:
        st.info(f"Sem dados de Análise P por {coluna_grupo} para os filtros atuais.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        card("TÉCNICOS P0", resumo["P0"], config.TLP_RED)
    with c2:
        card("TÉCNICOS P1", resumo["P1"], config.TLP_ORANGE)
    with c3:
        card("TOTAL TÉCNICOS", resumo["TOTAL"], "#7B8CDE")

    st.write("")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Contagem por {coluna_grupo}</h5>", unsafe_allow_html=True)
        st.markdown(_tabela_html(contagem, coluna_grupo, formato_percentual=False), unsafe_allow_html=True)
    with col_b:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Percentual por {coluna_grupo}</h5>", unsafe_allow_html=True)
        st.markdown(_tabela_html(percentual, coluna_grupo, formato_percentual=True), unsafe_allow_html=True)