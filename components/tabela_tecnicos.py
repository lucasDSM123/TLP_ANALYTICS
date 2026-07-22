import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import CABECALHO_BG, TOTAL_BG, pill, pill_contraste, cor_faixa, cor_faixa_bg, wrapper_tabela

_CORES_CLASSIFICACAO = {
    "P0": config.TLP_RED,
    "P1": config.TLP_ORANGE,
    "P2": config.TLP_GOLD,
    "P3": "#00C9A7",
    ">P3": "#22C55E",
}


def _badge_classificacao(classe: str) -> str:
    cor = _CORES_CLASSIFICACAO.get(str(classe), config.TEXT_MUTED)
    return pill(classe, cor, f"{cor}22")


def render_tabela_tecnicos(df_matriz: pd.DataFrame, total: dict = None):
    """
    Renderiza a matriz de Técnicos (usada em Supervisores, quando um
    supervisor é selecionado) no mesmo padrão visual das demais tabelas do
    site: cabeçalho em gradiente de marca, badges de alto contraste em
    Classificação P / PU / Eficácia, cores em Concluído OK/NOK e uma linha
    TOTAL GERAL no rodapé (passe `total` = dict vindo de Indicadores sobre
    o df filtrado, com HC/Caixa/Concluído/Eficácia/PU/Esteira/Iniciada/Projeção).
    """
    if df_matriz.empty:
        st.info("Sem técnicos com atividades para este filtro.")
        return

    colunas_ordem = [c for c in [
        "Técnico", "Classificação P", "Cluster", "Caixa Total", "Esteira",
        "PU", "Concluído OK", "Concluído NOK", "Iniciada", "Eficácia", "Projeção",
    ] if c in df_matriz.columns]

    linhas_html = []
    for i, (_, row) in enumerate(df_matriz.iterrows()):
        bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
        eficacia_pct = f"{row['Eficácia']:.0%}"

        celulas = []
        for c in colunas_ordem:
            if c == "Técnico":
                celulas.append(f"<td style='text-align:left; font-weight:700; color:{config.TEXT};'>{row[c]}</td>")
            elif c == "Classificação P":
                celulas.append(f"<td>{_badge_classificacao(row[c])}</td>")
            elif c == "Cluster":
                celulas.append(f"<td style='color:{config.TEXT_MUTED}; font-weight:600;'>{row[c]}</td>")
            elif c == "PU":
                celulas.append(f"<td>{pill(f'{row[c]:.2f}', cor_faixa(row[c], config.META_PU_ALVO), cor_faixa_bg(row[c], config.META_PU_ALVO))}</td>")
            elif c == "Concluído OK":
                celulas.append(f"<td style='font-weight:700; color:#15803D;'>{row[c]}</td>")
            elif c == "Concluído NOK":
                celulas.append(f"<td style='font-weight:700; color:{config.TLP_RED};'>{row[c]}</td>")
            elif c == "Eficácia":
                celulas.append(f"<td>{pill(eficacia_pct, cor_faixa(row[c], config.META_EFICACIA_ALVO), cor_faixa_bg(row[c], config.META_EFICACIA_ALVO))}</td>")
            elif c in ("Caixa Total", "Esteira", "Iniciada", "Projeção"):
                valor_fmt = f"{int(row[c]):,}".replace(",", ".")
                celulas.append(f"<td style='font-weight:700; color:{config.TEXT};'>{valor_fmt}</td>")
            else:
                celulas.append(f"<td style='font-weight:600; color:{config.TEXT};'>{row[c]}</td>")

        linhas_html.append(f"<tr style='{bg}'>{''.join(celulas)}</tr>")

    linha_total_html = ""
    if total:
        eficacia_pct_tot = f"{total['Eficácia']:.0%}"
        pu_tot_txt = f"{total['PU']:.2f}"
        celulas_total = []
        for c in colunas_ordem:
            if c == "Técnico":
                celulas_total.append("<td colspan='2' style='text-align:left; font-weight:800; font-size:14px; color:#FFFFFF;'>TOTAL GERAL</td>")
            elif c == "Classificação P":
                continue
            elif c == "Cluster":
                celulas_total.append("<td></td>")
            elif c == "PU":
                celulas_total.append(f"<td>{pill_contraste(pu_tot_txt, cor_faixa(total['PU'], config.META_PU_ALVO))}</td>")
            elif c == "Concluído OK":
                celulas_total.append(f"<td>{pill_contraste(total['Concluído OK'], '#15803D')}</td>")
            elif c == "Concluído NOK":
                celulas_total.append(f"<td>{pill_contraste(total['Concluído NOK'], config.TLP_RED)}</td>")
            elif c == "Eficácia":
                celulas_total.append(f"<td>{pill_contraste(eficacia_pct_tot, cor_faixa(total['Eficácia'], config.META_EFICACIA_ALVO))}</td>")
            elif c in ("Caixa Total", "Esteira", "Iniciada", "Projeção"):
                valor_fmt = f"{int(total[c]):,}".replace(",", ".")
                celulas_total.append(f"<td style='font-weight:800; font-size:14px; color:#FFFFFF;'>{valor_fmt}</td>")
            else:
                celulas_total.append("<td></td>")
        linha_total_html = f"<tr style='{TOTAL_BG}'>{''.join(celulas_total)}</tr>"

    header_html = "".join(
        f"<th style='text-align:{'left' if c in ('Técnico', 'Cluster') else 'center'};'>{c.upper()}</th>"
        for c in colunas_ordem
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}{linha_total_html}</tbody>"
        f"</table>"
    )

    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)
