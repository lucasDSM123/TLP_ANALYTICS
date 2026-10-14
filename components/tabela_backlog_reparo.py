"""
Tabelas e gráfico da aba "Backlog Reparo" — mesmo visual das demais tabelas do
site (cabeçalho em degradê de marca, pílulas coloridas, linha de total).

Regra de cor do "backlog em dias": acima da meta (config.META_BACKLOG_DIAS,
1,4 dia) = vermelho; até a meta = verde.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
from components.charts import FONTE, _tema
from components.estilo_tabela import (
    CABECALHO_BG, TOTAL_BG, _hex_para_rgba, pill, pill_contraste, pill_total, wrapper_tabela,
)
from services.backlog_reparo import DIAS_SEMANA, acima_da_meta, nome_cluster, ordenar_clusters

VERDE = "#15803D"
VERDE_BG = "rgba(34,197,94,0.16)"
SEP_HEAD = "border-left:1px solid rgba(255,255,255,0.28);"


def _sep_body() -> str:
    return f"border-left:1px solid {config.CARD_BORDER};"


def _vazio(v) -> bool:
    return v is None or pd.isna(v)


def _i(v) -> str:
    return "–" if _vazio(v) else f"{int(v):,}".replace(",", ".")


def _d(v, casas=2) -> str:
    return "–" if _vazio(v) else f"{float(v):.{casas}f}".replace(".", ",")


def _pct(v) -> str:
    return "–" if _vazio(v) else f"{float(v):.1f}%".replace(".", ",")


def _pill_dias(v) -> str:
    """Pílula do backlog em dias: vermelha acima da meta, verde até a meta."""
    if _vazio(v):
        return "–"
    if acima_da_meta(v):
        return pill(_d(v), config.TLP_RED, _hex_para_rgba(config.TLP_RED, 0.13))
    return pill(_d(v), VERDE, VERDE_BG)


def _pill_dias_total(v) -> str:
    """Mesma pílula, mas para a linha de total (fundo em degradê → balão branco)."""
    if _vazio(v):
        return pill_total("–")
    return pill_contraste(_d(v), config.TLP_RED if acima_da_meta(v) else VERDE)


# ---------------------------------------------------------------------
# Informações de cabeçalho (chips)
# ---------------------------------------------------------------------
def _chip(rotulo: str, valor: str) -> str:
    return (
        f"<span style='display:inline-flex; gap:6px; align-items:center; padding:3px 10px; border-radius:999px; "
        f"background:{_hex_para_rgba(config.TLP_ORANGE, 0.10)}; color:{config.TEXT}; font-size:12px;'>"
        f"<span style='color:{config.TEXT_MUTED};'>{rotulo}</span><b>{valor}</b></span>"
    )


def barra_titulo(titulo: str, chips: list[tuple[str, str]]) -> str:
    chips_html = "".join(_chip(r, v) for r, v in chips if v)
    return (
        "<div style='display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:2px 0 10px 0;'>"
        f"<span style='font-weight:800; font-size:13px; letter-spacing:0.6px; color:{config.TEXT};'>{titulo}</span>"
        f"{chips_html}</div>"
    )


# ---------------------------------------------------------------------
# Tabela "Backlog atual"
# ---------------------------------------------------------------------
def render_tabela_atual(clusters: pd.DataFrame, total: dict | None, empreiteira: str, chips: list) -> None:
    th = "style='text-align:center; padding:8px 6px; font-size:12px; letter-spacing:0.4px;'"

    def grupo(titulo, span, sep=True):
        return f"<th colspan='{span}' style='text-align:center; padding:8px 6px; {SEP_HEAD if sep else ''}'>{titulo}</th>"

    def sub(txt, sep=False):
        return f"<th style='text-align:center; padding:6px; font-size:11px; opacity:0.92; {SEP_HEAD if sep else ''}'>{txt}</th>"

    def rowspan(txt, sep=True, esquerda=False):
        alinh = "left" if esquerda else "center"
        return (f"<th rowspan='2' style='text-align:{alinh}; padding:8px 10px; font-size:12px; "
                f"{SEP_HEAD if sep else ''}'>{txt}</th>")

    linha1 = (
        rowspan("CLUSTER", sep=False, esquerda=True)
        + grupo("ENCERRADOS", 1)
        + grupo("VOZ", 2) + grupo("BANDA LARGA", 2) + grupo("TV", 2) + grupo("TOTAL", 2)
        + rowspan("TMR") + rowspan("ABERTA<br>MASSIVA") + rowspan("MASSIVA<br>ANÁLISE")
        + rowspan("TOTAL<br>GERAL") + rowspan("PEND AGEND.<br>/ RETEN")
        + grupo("OUTLIERS", 6)
    )
    linha2 = (
        sub("BD / TEC = PU", True)
        + sub("BD's", True) + sub("DIAS") + sub("BD's", True) + sub("DIAS")
        + sub("BD's", True) + sub("DIAS") + sub("BD's", True) + sub("DIAS")
        + sub("TOTAL", True) + sub("%") + sub("≥ 5 DIAS") + sub("%") + sub("≥ 10 DIAS") + sub("%")
    )

    def linha(r, i) -> str:
        bg = config.CARD if i % 2 == 0 else config.SURFACE
        sep = _sep_body()
        n = "font-weight:600;"
        enc = "–" if _vazio(r["enc_bd"]) else f"{_i(r['enc_bd'])} / {_i(r['enc_tec'])} = <b>{_d(r['enc_pu'], 1)}</b>"
        pend10 = "color:" + (config.TLP_RED if not _vazio(r["outl_10d"]) and r["outl_10d"] > 0 else config.TEXT) + ";"
        return (
            f"<tr style='background:{bg};'>"
            f"<td style='text-align:left; padding:8px 12px; font-weight:800; color:{config.TLP_ORANGE}; "
            f"border-left:3px solid {config.TLP_ORANGE};'>{nome_cluster(r['cluster'])}</td>"
            f"<td style='{sep} {n} white-space:nowrap;'>{enc}</td>"
            f"<td style='{sep} {n}'>{_i(r['voz_bd'])}</td><td>{_pill_dias(r['voz_dias'])}</td>"
            f"<td style='{sep} {n}'>{_i(r['bl_bd'])}</td><td>{_pill_dias(r['bl_dias'])}</td>"
            f"<td style='{sep} {n}'>{_i(r['tv_bd'])}</td><td>{_pill_dias(r['tv_dias'])}</td>"
            f"<td style='{sep} font-weight:800;'>{_i(r['total_bd'])}</td><td>{_pill_dias(r['total_dias'])}</td>"
            f"<td style='{sep} {n}'>{r['tmr'] if not _vazio(r['tmr']) else '–'}</td>"
            f"<td style='{n}'>{_i(r['aberta_massiva'])}</td><td style='{n}'>{_i(r['massiva_analise'])}</td>"
            f"<td style='font-weight:800;'>{_i(r['total_geral'])}</td>"
            f"<td style='{n}'>{_i(r['pend_agend_reten'])}</td>"
            f"<td style='{sep} {n}'>{_i(r['outl_total'])}</td><td style='color:{config.TEXT_MUTED};'>{_pct(r['outl_pct'])}</td>"
            f"<td style='{n}'>{_i(r['outl_5d'])}</td><td style='color:{config.TEXT_MUTED};'>{_pct(r['outl_5d_pct'])}</td>"
            f"<td style='{n} {pend10}'>{_i(r['outl_10d'])}</td><td style='color:{config.TEXT_MUTED};'>{_pct(r['outl_10d_pct'])}</td>"
            "</tr>"
        )

    def linha_total(t: dict) -> str:
        enc = "–" if _vazio(t["enc_bd"]) else f"{_i(t['enc_bd'])} / {_i(t['enc_tec'])} = {_d(t['enc_pu'], 1)}"
        P = pill_total
        return (
            f"<tr style='{TOTAL_BG()}'>"
            f"<td style='text-align:left; padding:10px 12px; font-weight:800; color:#FFFFFF;'>TOTAL {empreiteira}</td>"
            f"<td style='white-space:nowrap;'>{P(enc)}</td>"
            f"<td>{P(_i(t['voz_bd']))}</td><td>{_pill_dias_total(t['voz_dias'])}</td>"
            f"<td>{P(_i(t['bl_bd']))}</td><td>{_pill_dias_total(t['bl_dias'])}</td>"
            f"<td>{P(_i(t['tv_bd']))}</td><td>{_pill_dias_total(t['tv_dias'])}</td>"
            f"<td>{P(_i(t['total_bd']))}</td><td>{_pill_dias_total(t['total_dias'])}</td>"
            f"<td>{P(t['tmr'] if not _vazio(t['tmr']) else '–')}</td>"
            f"<td>{P(_i(t['aberta_massiva']))}</td><td>{P(_i(t['massiva_analise']))}</td>"
            f"<td>{P(_i(t['total_geral']))}</td><td>{P(_i(t['pend_agend_reten']))}</td>"
            f"<td>{P(_i(t['outl_total']))}</td><td>{P(_pct(t['outl_pct']))}</td>"
            f"<td>{P(_i(t['outl_5d']))}</td><td>{P(_pct(t['outl_5d_pct']))}</td>"
            f"<td>{P(_i(t['outl_10d']))}</td><td>{P(_pct(t['outl_10d_pct']))}</td>"
            "</tr>"
        )

    corpo = "".join(linha(r, i) for i, r in enumerate(clusters.to_dict("records")))
    corpo += linha_total(total) if total else ""

    tabela = (
        f"<table style='width:100%; min-width:1250px; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{linha1}</tr><tr style='{CABECALHO_BG()}'>{linha2}</tr></thead>"
        f"<tbody style='text-align:center;'>{corpo}</tbody></table>"
    )
    st.markdown(barra_titulo("BACKLOG ATUAL", chips) + wrapper_tabela(tabela), unsafe_allow_html=True)
    st.caption(f"🟢 até {str(config.META_BACKLOG_DIAS).replace('.', ',')} dia(s) de backlog · "
               f"🔴 acima da meta. Backlog em dias = BDs ÷ média produtiva dos últimos 6 dias úteis.")


# ---------------------------------------------------------------------
# Tabela "Fila D0" (caixa atual x meta de backlog + produção TT)
# ---------------------------------------------------------------------
def render_tabela_fila_d0(linhas: list[dict], total: dict | None, empreiteira: str, dia_amanha: str = "") -> None:
    if not linhas:
        return

    def cor_fila(v):
        return config.TLP_RED if acima_da_meta(v) else VERDE

    def pill_fila(v):
        if _vazio(v):
            return "–"
        if acima_da_meta(v):
            return pill(_d(v), config.TLP_RED, _hex_para_rgba(config.TLP_RED, 0.13))
        return pill(_d(v), VERDE, VERDE_BG)

    def pill_gap(v):
        # gap <= 0: a meta não cobre a caixa atual (vermelho); positivo = folga (verde)
        if _vazio(v):
            return "–"
        r = round(v)
        if r <= 0:
            return pill(_i(r), config.TLP_RED, _hex_para_rgba(config.TLP_RED, 0.13))
        return pill(_i(r), VERDE, VERDE_BG)

    def pill_gap_total(v):
        return pill_total("–") if _vazio(v) else pill_contraste(_i(round(v)), config.TLP_RED if round(v) <= 0 else VERDE)

    cab = ["CLUSTER", "CAIXA<br>ATUAL", "FILA D0", "RITMO", "META<br>BACKLOG", "GAP", "TT<br>ATRIBUÍDO",
           "ESTEIRA D0", "ENCERRADOS<br>BD / TEC = PU", "TT<br>NOK", "PROJEÇÃO<br>TT",
           f"ENTRANTE MÉD.<br>{dia_amanha}", f"BDs<br>AMANHÃ {dia_amanha}", f"FILA<br>AMANHÃ {dia_amanha}"]
    head = "".join(
        f"<th style='text-align:{'left' if i == 0 else 'center'}; padding:10px 10px; font-size:12px; "
        f"letter-spacing:0.4px; {SEP_HEAD if i in (6, 11) else ''}'>{c}</th>" for i, c in enumerate(cab)
    )

    def linha(r, i):
        bg = config.CARD if i % 2 == 0 else config.SURFACE
        sep, n = _sep_body(), "font-weight:600;"
        return (
            f"<tr style='background:{bg};'>"
            f"<td style='text-align:left; padding:8px 12px; font-weight:800; color:{config.TLP_ORANGE}; "
            f"border-left:3px solid {config.TLP_ORANGE};'>{nome_cluster(r['cluster'])}</td>"
            f"<td style='{n}'>{_i(r['caixa'])}</td><td>{pill_fila(r['fila'])}</td>"
            f"<td style='{n}'>{_i(r['ritmo'] and round(r['ritmo']))}</td>"
            f"<td style='{n}'>{_i(r['meta'] and round(r['meta']))}</td><td>{pill_gap(r['gap'])}</td>"
            f"<td style='{sep} {n}'>{_i(r['tt_atrib'])}</td>"
            f"<td style='{n}'>{_i(r['esteira'])}</td>"
            f"<td style='{n} white-space:nowrap;'>{_enc(r)}</td>"
            f"<td style='{n} color:{config.TLP_RED};'>{_i(r['tt_nok'])}</td>"
            f"<td style='{n}'>{_i(r['tt_proj'])}</td>"
            f"<td style='{sep} {n}'>{_i(r0(r['ent_med']))}</td>"
            f"<td style='{n}'>{_i(r0(r['bd_amanha']))}</td><td>{pill_fila(r['fila_amanha'])}</td></tr>"
        )

    def r0(v):
        return None if _vazio(v) else round(v)

    def _enc(r, negrito=True):
        """'25 / 18 = 1,4' (igual ao relatório da Vivo)."""
        if _vazio(r["enc_bd"]):
            return "–"
        pu = _d(r["enc_pu"], 1)
        return f"{_i(r['enc_bd'])} / {_i(r['enc_tec'])} = " + (f"<b>{pu}</b>" if negrito else pu)

    corpo = "".join(linha(r, i) for i, r in enumerate(linhas))
    if total:
        P = pill_total
        corpo += (
            f"<tr style='{TOTAL_BG()}'>"
            f"<td style='text-align:left; padding:10px 12px; font-weight:800; color:#FFFFFF;'>TOTAL {empreiteira}</td>"
            f"<td>{P(_i(total['caixa']))}</td><td>{_pill_dias_total(total['fila'])}</td>"
            f"<td>{P(_i(r0(total['ritmo'])))}</td><td>{P(_i(r0(total['meta'])))}</td>"
            f"<td>{pill_gap_total(total['gap'])}</td><td>{P(_i(total['tt_atrib']))}</td>"
            f"<td>{P(_i(total['esteira']))}</td><td style='white-space:nowrap;'>{P(_enc(total, negrito=False))}</td>"
            f"<td>{P(_i(total['tt_nok']))}</td><td>{P(_i(total['tt_proj']))}</td>"
            f"<td>{P(_i(r0(total['ent_med'])))}</td><td>{P(_i(r0(total['bd_amanha'])))}</td>"
            f"<td>{_pill_dias_total(total['fila_amanha'])}</td></tr>"
        )

    tabela = (
        f"<table style='width:100%; min-width:1150px; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{head}</tr></thead>"
        f"<tbody style='text-align:center;'>{corpo}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)
    fator = str(config.FATOR_META_BACKLOG).replace(".", ",")
    st.caption(
        f"Fila D0 = backlog em dias · Ritmo = Caixa ÷ Fila D0 · Meta backlog = Ritmo × {fator} · Gap = Meta − Caixa "
        "(🔴 gap ≤ 0). Amanhã: BDs = Caixa atual − Projeção TT + Entrante médio; Fila = BDs ÷ Ritmo. "
        "TT atribuído (caixa total do TT), Esteira D0 (o que ainda resta para tratar), NOK e Projeção vêm da matriz de Produção TT; Encerrados vêm do relatório da Vivo."
    )


# ---------------------------------------------------------------------
# Tabela "Backlog histórico"
# ---------------------------------------------------------------------
def render_tabela_historico(hist: pd.DataFrame, janela: int, empreiteira: str) -> None:
    if hist.empty:
        st.info("Ainda não há histórico gravado para este filtro.")
        return

    datas = sorted(hist["data"].unique())
    mostrar = datas[-janela:]
    mapa = {(r.cluster, r.data): (r.bd, r.dias) for r in hist.itertuples()}
    clusters = ordenar_clusters(hist.loc[~hist["eh_total"], "cluster"])

    def seta(cluster, data):
        atual = mapa.get((cluster, data), (None, None))[0]
        ant = mapa.get((cluster, data - pd.Timedelta(days=1)), (None, None))[0]
        if _vazio(atual) or _vazio(ant) or atual == ant:
            return ""
        sobe = atual > ant
        cor = config.TLP_RED if sobe else VERDE
        return f" <span style='color:{cor}; font-size:10px;'>{'▲' if sobe else '▼'}</span>"

    th_datas = "".join(
        f"<th colspan='2' style='text-align:center; padding:8px 4px; {SEP_HEAD}'>{pd.Timestamp(d):%d/%m}"
        f"<br><span style='font-weight:500; font-size:11px; opacity:0.9;'>{DIAS_SEMANA[pd.Timestamp(d).weekday()]}</span></th>"
        for d in mostrar
    )
    sub = "".join(
        f"<th style='padding:5px; font-size:11px; {SEP_HEAD}'>BD</th><th style='padding:5px; font-size:11px;'>DIAS</th>"
        for _ in mostrar
    )

    def celulas(cluster, total=False):
        out = []
        for d in mostrar:
            bd, dias = mapa.get((cluster, d), (None, None))
            sep = "" if total else _sep_body()
            if total:
                out.append(f"<td>{pill_total(_i(bd))}</td><td>{_pill_dias_total(dias)}</td>")
            else:
                out.append(f"<td style='{sep} font-weight:700;'>{_i(bd)}{seta(cluster, d)}</td><td>{_pill_dias(dias)}</td>")
        return "".join(out)

    corpo = ""
    for i, c in enumerate(clusters):
        bg = config.CARD if i % 2 == 0 else config.SURFACE
        corpo += (
            f"<tr style='background:{bg};'><td style='text-align:left; padding:8px 12px; font-weight:800; "
            f"color:{config.TLP_ORANGE}; border-left:3px solid {config.TLP_ORANGE};'>{nome_cluster(c)}</td>{celulas(c)}</tr>"
        )
    if (hist["cluster"] == "TOTAL").any():
        corpo += (
            f"<tr style='{TOTAL_BG()}'><td style='text-align:left; padding:10px 12px; font-weight:800; "
            f"color:#FFFFFF;'>TOTAL {empreiteira}</td>{celulas('TOTAL', total=True)}</tr>"
        )

    tabela = (
        f"<table style='width:100%; min-width:{180 + 118 * len(mostrar)}px; border-collapse:collapse; font-size:13px; "
        f"color:{config.TEXT};'><thead>"
        f"<tr style='{CABECALHO_BG()}'><th rowspan='2' style='text-align:left; padding:8px 12px;'>CLUSTER</th>{th_datas}</tr>"
        f"<tr style='{CABECALHO_BG()}'>{sub}</tr></thead>"
        f"<tbody style='text-align:center;'>{corpo}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)
    st.caption("▲ backlog subiu e ▼ caiu em relação ao dia anterior. Cada dia mostra o backlog medido no início da manhã.")


# ---------------------------------------------------------------------
# Gráfico: barras = BD / média produtiva · linha = backlog em dias
# ---------------------------------------------------------------------
def grafico_historico(serie: pd.DataFrame) -> go.Figure:
    """`serie`: colunas data, bd, coef, dias de UM cluster (ou do TOTAL), em ordem de data."""
    serie = serie.sort_values("data")
    x = serie["data"].dt.strftime("%d/%m").tolist()
    bd, coef, dias = serie["bd"].astype(float), serie["coef"].astype(float), serie["dias"].astype(float)
    meta = config.META_BACKLOG_DIAS

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=x, y=bd, name="BD (backlog)", marker=dict(color=_hex_para_rgba(config.TLP_ORANGE, 0.30),
                                                   line=dict(color=config.TLP_ORANGE, width=1)),
        text=bd.map(lambda v: "" if pd.isna(v) else f"{int(v)}"), textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color=config.TEXT_MUTED), width=0.62,
        hovertemplate="BD: <b>%{y:.0f}</b><extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=x, y=coef, name="Média produtiva", marker=dict(color=_hex_para_rgba(config.CHART_BA, 0.85)), width=0.28,
        hovertemplate="Média produtiva: <b>%{y:.1f}</b><extra></extra>",
    ), secondary_y=False)

    cores = [config.TLP_RED if (not pd.isna(v) and v > meta) else "#22C55E" for v in dias]
    fig.add_trace(go.Scatter(
        x=x, y=dias, name="Backlog em dias", mode="lines+markers+text",
        line=dict(color=config.TEXT, width=2, shape="spline", smoothing=0.6),
        marker=dict(size=9, color=cores, line=dict(color="#FFFFFF", width=1.5)),
        text=dias.map(lambda v: "" if pd.isna(v) else f"{v:.2f}".replace(".", ",")), textposition="top center",
        textfont=dict(size=10, color=config.TEXT, family=FONTE),
        hovertemplate="Dias: <b>%{y:.2f}</b><extra></extra>",
    ), secondary_y=True)

    # Escalas: barras ocupam a metade de baixo; a linha de dias flutua acima delas.
    max_bd = max(float(bd.max()), float(coef.max())) if len(bd) else 1.0
    d_lo, d_hi = min(float(dias.min()), meta), max(float(dias.max()), meta)
    amp = max(d_hi - d_lo, 0.3)
    fig.update_yaxes(range=[0, max_bd / 0.52], showgrid=True, gridcolor=config.CARD_BORDER, secondary_y=False,
                     title_text="BDs")
    fig.update_yaxes(range=[d_lo - amp * 2.0, d_hi + amp * 0.35], showgrid=False, showticklabels=False,
                     secondary_y=True)

    # Linha da meta como série (aparece na legenda; um rótulo solto ficava cortado na borda direita)
    fig.add_trace(go.Scatter(
        x=[x[0], x[-1]], y=[meta, meta], mode="lines", name=f"Meta {str(meta).replace('.', ',')} dia",
        line=dict(color=config.TLP_RED, width=1.6, dash="dash"), hoverinfo="skip",
    ), secondary_y=True)

    _tema(fig, altura=440)
    fig.update_layout(
        barmode="overlay", hovermode="x unified", bargap=0.25,
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(tickangle=-45 if len(x) > 14 else 0, type="category")
    try:  # cantos arredondados nas barras (plotly >= 5.24); ignora versões antigas
        fig.update_traces(marker_cornerradius=5, selector=dict(type="bar"))
    except ValueError:
        pass
    return fig
