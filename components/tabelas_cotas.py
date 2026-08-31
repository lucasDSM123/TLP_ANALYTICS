import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import CABECALHO_BG, TOTAL_BG, pill_contraste, pill_total, wrapper_tabela


def _cor_gap_texto(valor) -> str:
    """Vermelho pra negativo, verde pra positivo, preto padrão (negrito) pra zero."""
    if valor is None or pd.isna(valor) or valor == 0:
        return config.TEXT
    return config.TLP_RED if valor < 0 else "#15803D"


def _hex_para_rgba(cor_hex: str, alpha: float) -> str:
    cor_hex = (cor_hex or "").lstrip("#")
    r, g, b = int(cor_hex[0:2], 16), int(cor_hex[2:4], 16), int(cor_hex[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _cor_pct_fundo(pct: float) -> str:
    """Fundo tingido (mais saturado que o padrão claro do site) — verde >=100%,
    accent secundário >=60%, vermelho abaixo disso. Mesma leitura de semáforo
    da matriz %AGENDADA_SLOT de referência."""
    if pd.isna(pct):
        return "rgba(0,0,0,0.03)"
    if pct >= 1.0:
        return "rgba(34,197,94,0.30)"
    if pct >= 0.6:
        return _hex_para_rgba(config.TLP_GOLD, 0.34)
    return _hex_para_rgba(config.TLP_RED, 0.26)


def tabela_distribuicao_turno(pivot_cota: pd.DataFrame, pivot_real: pd.DataFrame, pivot_gap: pd.DataFrame):
    """
    Tabela "Distribuição por Turno": uma linha por Atividade, com Cota/Ativ./Gap
    lado a lado dentro de cada Horário (colspan=3), cabeçalho em gradiente,
    números em negrito preto e Gap colorido (vermelho/verde) — mesmo padrão
    visual das demais tabelas do site.
    """
    if pivot_real.empty:
        st.info("Sem dados de turno para este dia.")
        return

    horarios = list(pivot_real.columns)
    atividades = list(pivot_real.index)

    # -------- cabeçalho (2 linhas: Horário com colspan=3, depois Cota/Ativ./Gap) --------
    header_horarios = "".join(
        f"<th colspan='3' style='text-align:center; border-left:2px solid rgba(255,255,255,0.35);'>{h}</th>"
        for h in horarios
    )
    header_sub = "".join(
        "<th style='border-left:2px solid rgba(255,255,255,0.35);'>Cota</th>"
        "<th>Ativ.</th><th>Gap</th>"
        for _ in horarios
    )

    # -------- linhas do corpo --------
    linhas_html = []
    for i, atividade in enumerate(atividades):
        bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
        celulas = [f"<td style='text-align:left; font-weight:700; color:{config.TEXT};'>{atividade}</td>"]
        for h in horarios:
            cota = int(pivot_cota.loc[atividade, h]) if h in pivot_cota.columns else 0
            real = int(pivot_real.loc[atividade, h])
            gap = int(pivot_gap.loc[atividade, h]) if h in pivot_gap.columns else 0
            cor_gap = _cor_gap_texto(gap)
            celulas.append(
                f"<td style='font-weight:700; color:{config.TEXT}; border-left:2px solid {config.CARD_BORDER};'>{cota}</td>"
                f"<td style='font-weight:700; color:{config.TEXT};'>{real}</td>"
                f"<td style='font-weight:800; color:{cor_gap};'>{gap:+d}</td>"
            )
        linhas_html.append(f"<tr style='{bg}'>{''.join(celulas)}</tr>")

    # -------- linha TOTAL --------
    total_celulas = [f"<td style='text-align:left; font-weight:800; color:#FFFFFF;'>TOTAL</td>"]
    for h in horarios:
        cota_tot = int(pivot_cota[h].sum()) if h in pivot_cota.columns else 0
        real_tot = int(pivot_real[h].sum())
        gap_tot = int(pivot_gap[h].sum()) if h in pivot_gap.columns else 0
        cor_gap_tot = "#15803D" if gap_tot > 0 else (config.TLP_RED if gap_tot < 0 else "#374151")
        total_celulas.append(
            f"<td>{pill_total(cota_tot)}</td>"
            f"<td>{pill_total(real_tot)}</td>"
            f"<td>{pill_contraste(f'{gap_tot:+d}', cor_gap_tot)}</td>"
        )
    linhas_html.append(f"<tr style='{TOTAL_BG()}'>{''.join(total_celulas)}</tr>")

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT}; text-align:center;'>"
        f"<thead>"
        f"<tr style='{CABECALHO_BG()}'><th style='text-align:left;'></th>{header_horarios}</tr>"
        f"<tr style='{CABECALHO_BG()}'><th style='text-align:left;'>Atividade</th>{header_sub}</tr>"
        f"</thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)


def tabela_matriz_agendada(matriz: pd.DataFrame, linha_total: pd.Series = None, nome_linha: str = "Cluster"):
    """
    Matriz %Agendada (Cluster ou Cidade × Horário): cabeçalho em gradiente,
    células com fundo tingido (verde/dourado/vermelho) e número em negrito
    preto, linha TOTAL em destaque no fim.
    """
    if matriz.empty:
        st.info("Sem dados para a matriz de %Agendada.")
        return

    horarios = list(matriz.columns)

    header_html = f"<th style='text-align:left;'>{nome_linha.upper()}</th>" + "".join(
        f"<th style='text-align:center;'>{h}</th>" for h in horarios
    )

    linhas_html = []
    for i, (nome_linha_atual, row) in enumerate(matriz.iterrows()):
        bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
        celulas = [f"<td style='text-align:left; font-weight:700; color:{config.TEXT};'>{nome_linha_atual}</td>"]
        for h in horarios:
            pct = row[h]
            fundo = _cor_pct_fundo(pct)
            celulas.append(
                f"<td style='background:{fundo}; font-weight:800; color:{config.TEXT}; "
                f"border-left:1px solid {config.CARD_BORDER};'>{pct * 100:.1f}%</td>"
            )
        linhas_html.append(f"<tr style='{bg}'>{''.join(celulas)}</tr>")

    if linha_total is not None:
        total_celulas = [f"<td style='text-align:left; font-weight:800; color:#FFFFFF;'>TOTAL</td>"]
        for h in horarios:
            pct = linha_total[h]
            cor = "#15803D" if pct >= 1.0 else (config.TLP_GOLD if pct >= 0.6 else config.TLP_RED)
            total_celulas.append(f"<td>{pill_contraste(f'{pct * 100:.1f}%', cor)}</td>")
        linhas_html.append(f"<tr style='{TOTAL_BG()}'>{''.join(total_celulas)}</tr>")

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)


def tabela_detalhe_cidade(tabela_detalhe: pd.DataFrame):
    """
    Detalhe Cidade > Time Slot dentro do expander de um cluster: linha
    "Total" da cidade em negrito/fundo levemente destacado, seguida das
    linhas de cada horário (indentadas), com %Agendada tingida e Delta
    colorido — mesmo padrão de cor das outras tabelas da página.
    """
    if tabela_detalhe.empty:
        st.info("Sem dados para este cluster.")
        return

    header_html = (
        "<th style='text-align:left;'>CIDADE / TIME SLOT</th>"
        "<th>COTAS ABERTAS</th><th>COTAS ATRIBUÍDAS</th><th>DELTA</th><th>%AGENDADA</th>"
    )

    linhas_html = []
    for (cidade, slot), row in tabela_detalhe.iterrows():
        eh_total = slot == "Total"
        cota = int(row["Cotas Abertas"])
        real = int(row["Cotas Atribuídas"])
        delta = int(row["Delta"])
        pct = row["%Agendada"]
        cor_delta = _cor_gap_texto(delta)
        fundo_pct = _cor_pct_fundo(pct)

        if eh_total:
            bg = "background: rgba(46,99,199,0.10); border-top:2px solid " + config.TLP_ORANGE + ";"
            rotulo = f"<td style='text-align:left; font-weight:800; color:{config.TEXT};'>{cidade}</td>"
        else:
            bg = f"background:{config.SURFACE};"
            rotulo = (
                f"<td style='text-align:left; font-style:italic; color:{config.TEXT_MUTED}; padding-left:22px;'>"
                f"{slot}</td>"
            )

        linhas_html.append(
            f"<tr style='{bg}'>"
            f"{rotulo}"
            f"<td style='font-weight:700; color:{config.TEXT};'>{cota}</td>"
            f"<td style='font-weight:700; color:{config.TEXT};'>{real}</td>"
            f"<td style='font-weight:800; color:{cor_delta};'>{delta:+d}</td>"
            f"<td style='background:{fundo_pct}; font-weight:800; color:{config.TEXT};'>{pct * 100:.1f}%</td>"
            f"</tr>"
        )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)
