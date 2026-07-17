import pandas as pd
import streamlit as st

import config


def _seta(valor: float, alvo: float = config.META_PU_ALVO) -> str:
    """Seta verde (▲) se valor >= alvo, vermelha (▼) se abaixo."""
    if valor >= alvo:
        return f"<span style='color:#22C55E;'>▲</span>"
    return f"<span style='color:{config.TLP_RED};'>▼</span>"

def _seta_gap(valor: float) -> str:
    if valor >= 0:
        return f"<span style='color:#22C55E;'>▲</span>"
    return f"<span style='color:{config.TLP_RED};'>▼</span>"

def _dot_eficacia(valor: float) -> str:
    cor = "#22C55E" if valor >= config.META_EFICACIA_ALVO else config.TLP_RED
    return f"<span style='color:{cor};'>●</span>"


def _celula_linha(row: dict, negrito: bool = False, bg: str = None) -> str:
    peso = "700" if negrito else "500"
    eficacia_pct = f"{row['Eficácia']:.0%}"

    return "".join([
        f"<td style=\"text-align:left; font-weight:{peso};\">{row['Nome']}</td>",
        f"<td>{row['HC Ativo']}</td>",
        f"<td>{row['Caixa Total']}</td>",
        f"<td>{row['Esteira']}</td>",
        f"<td>{row['Média Atribuição']:.2f}</td>",
        f"<td>{_seta(row['PU'])} {row['PU']:.2f}</td>",
        f"<td style=\"color:#22C55E;\">{row['Concluída BA']}</td>",
        f"<td style=\"color:{config.TLP_ORANGE};\">{row['Concluída TT']}</td>",
        f"<td style=\"color:{config.TLP_RED};\">{row['Não Concluída']}</td>",
        f"<td>{row['Iniciada']}</td>",
        f"<td>{_dot_eficacia(row['Eficácia'])} {eficacia_pct}</td>",
        f"<td>{row['Projeção']}</td>",
        f"<td>{_seta(row['Projeção PU'])} {row['Projeção PU']:.2f}</td>",
        f"<td>{row['Meta']}</td>",
        f"<td>{_seta_gap(row['Gap'])} {row['Gap']:+d}</td>",
    ])


def render_tabela_coordenadores(grupos: list):
    """
    Renderiza a tabela hierárquica Coordenador -> Supervisor -> subtotal
    como HTML (célula de Coordenador mesclada com rowspan, igual ao
    Excel/Power BI original).
    """
    if not grupos:
        st.info("Sem dados de Coordenador/Supervisor para os filtros atuais.")
        return

    colunas = ["COORDENADOR", "SUPERVISOR", "HC ATIVO", "CAIXA TOTAL", "ESTEIRA",
               "MÉDIA ATRIBUIÇÃO", "PU", "BA", "TT", "NÃO CONCLUÍDA", "INICIADA",
               "% EFICÁCIA", "PROJEÇÃO", "PROJEÇÃO PU", "META", "GAP"]

    linhas_html = []
    for grupo in grupos:
        supervisores = grupo["supervisores"]
        subtotal = grupo["subtotal"]
        total_linhas = len(supervisores) + 1

        primeira = True
        for idx_sup, sup in enumerate(supervisores):
            coord_td = (
                f"<td rowspan=\"{total_linhas}\" style=\"text-align:left; font-weight:700; "
                f"vertical-align:middle; background:{config.SURFACE};\">{grupo['coordenador']}</td>"
                if primeira else ""
            )
            linha_bg = config.CARD if idx_sup % 2 == 0 else config.SURFACE
            linhas_html.append(f"<tr style=\"background:{linha_bg};\">{coord_td}{_celula_linha(sup)}</tr>")
            primeira = False

        linhas_html.append(
            f"<tr style=\"background:rgba(255,106,0,0.08); border-top:1px solid {config.CARD_BORDER};\">"
            f"{_celula_linha(subtotal, negrito=True)}</tr>"
        )

    header_html = "".join(
        f"<th rowspan=\"2\" style=\"text-align:{'left' if c in ('COORDENADOR', 'SUPERVISOR') else 'center'};\">{c}</th>"
        for c in colunas[:colunas.index("BA")]
    )
    th_concluida = "<th colspan=\"2\" style=\"text-align:center;\">CONCLUÍDA</th>"
    th_depois = "".join(
        f"<th rowspan=\"2\" style=\"text-align:center;\">{c}</th>"
        for c in colunas[colunas.index("NÃO CONCLUÍDA"):]
    )
    linha_header_1 = header_html + th_concluida + th_depois
    linha_header_2 = (
        "<th style=\"text-align:center; color:#22C55E;\">BA</th>"
        f"<th style=\"text-align:center; color:{config.TLP_ORANGE};\">TT</th>"
    )

    html = (
        f"<div style=\"overflow-x:auto; background:{config.CARD}; border:1px solid {config.CARD_BORDER}; border-radius:10px; box-shadow:0 2px 14px rgba(20,20,30,0.06);\">"
        f"<table style=\"width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT};\">"
        f"<thead>"
        f"<tr style=\"background:{config.SURFACE}; color:{config.TEXT_MUTED};\">{linha_header_1}</tr>"
        f"<tr style=\"background:{config.SURFACE}; color:{config.TEXT_MUTED};\">{linha_header_2}</tr>"
        f"</thead>"
        f"<tbody style=\"text-align:center;\">{''.join(linhas_html)}</tbody>"
        f"</table>"
        f"</div>"
    )

    st.markdown(html, unsafe_allow_html=True)
