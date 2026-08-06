import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import (
    CABECALHO_BG, TOTAL_BG, SUBTOTAL_BG, pill, pill_total,
    cor_faixa, cor_faixa_bg, wrapper_tabela,
)


def _seta(valor: float, alvo: float = config.META_PU_ALVO) -> str:
    return "▲" if valor >= alvo else "▼"


def _seta_gap(valor: float) -> str:
    return "▲" if valor >= 0 else "▼"


def _celula_linha(row: dict, negrito: bool = False, tamanho: str = "13px") -> str:
    peso = "800" if negrito else "600"
    eficacia_pct = f"{row['Eficácia']:.0%}"

    txt_pu = f"{_seta(row['PU'])} {row['PU']:.2f}"
    txt_proj_pu = f"{_seta(row['Projeção PU'])} {row['Projeção PU']:.2f}"
    txt_gap = f"{_seta_gap(row['Gap'])} {row['Gap']:+d}"

    caixa_fmt = f"{row['Caixa Total']:,}".replace(",", ".")
    esteira_fmt = f"{row['Esteira']:,}".replace(",", ".")
    projecao_fmt = f"{row['Projeção']:,}".replace(",", ".")

    return "".join([
        f"<td style='text-align:left; font-weight:{peso}; font-size:{tamanho}; color:{config.TEXT};'>{row['Nome']}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{row['HC Ativo']}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{caixa_fmt}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{esteira_fmt}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{row['Média Atribuição']:.2f}</td>",
        f"<td>{pill(txt_pu, cor_faixa(row['PU'], config.META_PU_ALVO), cor_faixa_bg(row['PU'], config.META_PU_ALVO))}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho}; color:#15803D;'>{row['Concluída BA']}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho}; color:{config.TLP_ORANGE};'>{row['Concluída TT']}</td>",
        f"<td style='font-weight:800; font-size:{tamanho}; color:{config.TEXT};'>{row['Concluída Total']}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho}; color:{config.TLP_RED};'>{row['Não Concluída']}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{row['Iniciada']}</td>",
        f"<td>{pill(eficacia_pct, cor_faixa(row['Eficácia'], config.META_EFICACIA_ALVO), cor_faixa_bg(row['Eficácia'], config.META_EFICACIA_ALVO))}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{projecao_fmt}</td>",
        f"<td>{pill(txt_proj_pu, cor_faixa(row['Projeção PU'], config.META_PU_ALVO), cor_faixa_bg(row['Projeção PU'], config.META_PU_ALVO))}</td>",
        f"<td style='font-weight:{peso}; font-size:{tamanho};'>{row['Meta']}</td>",
        f"<td>{pill(txt_gap, '#15803D' if row['Gap'] >= 0 else config.TLP_RED, 'rgba(34,197,94,0.14)' if row['Gap'] >= 0 else 'rgba(232,57,29,0.10)')}</td>",
    ])


def _celula_total_geral(row: dict) -> str:
    """
    Linha TOTAL GERAL — fundo no gradiente de marca. TODOS os valores usam
    `pill_total` (balão branco opaco + texto preto em negrito), de forma
    uniforme — sem variar a cor por indicador, só pra destacar o número
    com contraste máximo sobre o gradiente laranja/vermelho.
    """
    eficacia_pct = f"{row['Eficácia']:.0%}"

    txt_pu = f"{_seta(row['PU'])} {row['PU']:.2f}"
    txt_proj_pu = f"{_seta(row['Projeção PU'])} {row['Projeção PU']:.2f}"
    txt_gap = f"{_seta_gap(row['Gap'])} {row['Gap']:+d}"

    caixa_fmt = f"{row['Caixa Total']:,}".replace(",", ".")
    esteira_fmt = f"{row['Esteira']:,}".replace(",", ".")
    projecao_fmt = f"{row['Projeção']:,}".replace(",", ".")
    media_fmt = f"{row['Média Atribuição']:.2f}"

    return "".join([
        f"<td colspan='2' style='text-align:left; font-weight:800; font-size:14px; color:#FFFFFF;'>{row['Nome']}</td>",
        f"<td>{pill_total(row['HC Ativo'])}</td>",
        f"<td>{pill_total(caixa_fmt)}</td>",
        f"<td>{pill_total(esteira_fmt)}</td>",
        f"<td>{pill_total(media_fmt)}</td>",
        f"<td>{pill_total(txt_pu)}</td>",
        f"<td>{pill_total(row['Concluída BA'])}</td>",
        f"<td>{pill_total(row['Concluída TT'])}</td>",
        f"<td>{pill_total(row['Concluída Total'])}</td>",
        f"<td>{pill_total(row['Não Concluída'])}</td>",
        f"<td>{pill_total(row['Iniciada'])}</td>",
        f"<td>{pill_total(eficacia_pct)}</td>",
        f"<td>{pill_total(projecao_fmt)}</td>",
        f"<td>{pill_total(txt_proj_pu)}</td>",
        f"<td>{pill_total(row['Meta'])}</td>",
        f"<td>{pill_total(txt_gap)}</td>",
    ])


def render_tabela_coordenadores(grupos: list, total: dict = None):
    """
    Renderiza a tabela hierárquica Coordenador -> Supervisor -> subtotal
    como HTML (célula de Coordenador mesclada com rowspan, igual ao
    Excel/Power BI original), com uma linha "TOTAL GERAL" fixa no rodapé
    (passe `total` = services.coordenador_tabela.total_geral(df)).
    """
    if not grupos:
        st.info("Sem dados de Coordenador/Supervisor para os filtros atuais.")
        return

    colunas = ["COORDENADOR", "SUPERVISOR", "HC ATIVO", "CAIXA TOTAL", "ESTEIRA",
               "MÉDIA ATRIBUIÇÃO", "PU", "BA", "TT", "TOTAL", "NÃO CONCLUÍDA", "INICIADA",
               "% EFICÁCIA", "PROJEÇÃO", "PROJEÇÃO PU", "META", "GAP"]

    linhas_html = []
    for grupo in grupos:
        supervisores = grupo["supervisores"]
        subtotal = grupo["subtotal"]
        total_linhas = len(supervisores) + 1

        primeira = True
        for idx_sup, sup in enumerate(supervisores):
            coord_td = (
                f"<td rowspan='{total_linhas}' style='text-align:left; font-weight:800; "
                f"vertical-align:middle; background:{config.SURFACE}; color:{config.TLP_ORANGE}; "
                f"border-left:3px solid {config.TLP_ORANGE};'>{grupo['coordenador']}</td>"
                if primeira else ""
            )
            linha_bg = config.CARD if idx_sup % 2 == 0 else config.SURFACE
            linhas_html.append(f"<tr style='background:{linha_bg};'>{coord_td}{_celula_linha(sup)}</tr>")
            primeira = False

        linhas_html.append(f"<tr style='{SUBTOTAL_BG}'>{_celula_linha(subtotal, negrito=True)}</tr>")

    header_html = "".join(
        f"<th rowspan='2' style='text-align:{'left' if c in ('COORDENADOR', 'SUPERVISOR') else 'center'};'>{c}</th>"
        for c in colunas[:colunas.index("BA")]
    )
    th_concluida = "<th colspan='3' style='text-align:center;'>CONCLUÍDA</th>"
    th_depois = "".join(
        f"<th rowspan='2' style='text-align:center;'>{c}</th>"
        for c in colunas[colunas.index("NÃO CONCLUÍDA"):]
    )
    linha_header_1 = header_html + th_concluida + th_depois
    linha_header_2 = (
        "<th style='text-align:center; color:#7CF3B8;'>BA</th>"
        f"<th style='text-align:center; color:{config.TLP_GOLD};'>TT</th>"
        "<th style='text-align:center; color:#FFFFFF;'>TOTAL</th>"
    )

    linha_total_html = ""
    if total:
        linha_total_html = f"<tr style='{TOTAL_BG}'>{_celula_total_geral(total)}</tr>"

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead>"
        f"<tr style='{CABECALHO_BG}'>{linha_header_1}</tr>"
        f"<tr style='{CABECALHO_BG}'>{linha_header_2}</tr>"
        f"</thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}{linha_total_html}</tbody>"
        f"</table>"
    )

    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)