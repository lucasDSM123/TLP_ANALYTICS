"""Tabelas da aba "Atribuição" — mesmo visual (cabeçalho em gradiente, subtotal por
cluster, TOTAL GERAL em destaque) das demais tabelas do site."""
import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import (
    CABECALHO_BG, SUBTOTAL_BG, TOTAL_BG, pill, pill_contraste, pill_total, wrapper_tabela,
)
from services.atribuicao import HORARIOS


def _dec(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _gap_pill(valor: int, sobre_gradiente: bool = False) -> str:
    """GAP > 0 = faltam técnicos (vermelho); < 0 = sobra (verde); 0 = equilibrado."""
    if valor > 0:
        cor, fundo, txt = config.TLP_RED, "rgba(232,57,29,0.12)", f"+{valor}"
    elif valor < 0:
        cor, fundo, txt = "#15803D", "rgba(34,197,94,0.16)", f"{valor}"
    else:
        cor, fundo, txt = config.TEXT, "rgba(0,0,0,0.05)", "0"
    return pill_contraste(txt, cor) if sobre_gradiente else pill(txt, cor, fundo)


def _atrib_pill(valor: float, sobre_gradiente: bool = False) -> str:
    """Atividades por técnico: acima da meta (config.META_ATRIBUICAO_ALVO) = sobrecarga (vermelho)."""
    cor = config.TLP_RED if valor > config.META_ATRIBUICAO_ALVO else config.TEXT
    if sobre_gradiente:
        return pill_contraste(_dec(valor), cor)
    return f"<span style='font-weight:800; color:{cor};'>{_dec(valor)}</span>"


def _pct_carga(pct: float, sobre_gradiente: bool = False) -> str:
    """Carga por técnico em %: 100% = ideal (1 atividade por técnico). Acima de 100% = atividade
    a mais (vermelho); abaixo = técnico com folga."""
    texto = f"{pct * 100:.0f}%"
    cor = config.TLP_RED if pct > 1 else "#15803D"
    if sobre_gradiente:
        return pill_contraste(texto, cor)
    fundo = "rgba(232,57,29,0.12)" if pct > 1 else "rgba(34,197,94,0.16)"
    return pill(texto, cor, fundo)


def _cel_horario(r, h: str, estilo: str = "linha") -> str:
    """Célula de um horário.
    - "linha" (bucket): apenas o nº de atividades.
    - "cluster" (subtotal) e "geral": "atividades / HC GERAL = %". O HC é o total da própria linha
      (coluna HC), igual para todos os horários — acompanha o HC geral que o site mostra.
    """
    ativ, hc_geral = int(r[h]), int(r["HC"])
    if estilo == "geral":
        cor_txt, cor_hc, peso = "#FFFFFF", "#FFFFFF", 800
    else:
        cor_txt, cor_hc, peso = config.TEXT, config.TLP_ORANGE, (800 if estilo == "cluster" else 600)
    if estilo == "linha":  # linhas de bucket: só o nº de atividades (cálculo fica nos totais)
        if ativ == 0:
            return f"<td style='color:{config.TEXT_MUTED};'>0</td>"
        return f"<td style='font-size:12.5px; font-weight:{peso}; color:{cor_txt};'>{ativ}</td>"
    if ativ == 0 and hc_geral == 0:
        return f"<td style='color:{config.TEXT_MUTED};'>0</td>"
    pct = (ativ / hc_geral) if hc_geral else 0.0
    resultado = _pct_carga(pct, sobre_gradiente=(estilo == "geral")) if hc_geral else "—"
    return (
        f"<td style='white-space:nowrap; font-size:12.5px;'>"
        f"<span style='font-weight:{peso}; color:{cor_txt};'>{ativ}</span>"
        f"<span style='color:{cor_txt}; opacity:.7;'> / </span>"
        f"<span style='font-weight:800; color:{cor_hc};'>{hc_geral}</span>"
        f"<span style='color:{cor_txt}; opacity:.7;'> = </span>{resultado}</td>"
    )


def nota_carga_por_tecnico():
    """Texto explicativo exibido logo abaixo da tabela."""
    st.markdown(
        f"<div style='margin-top:10px; padding:10px 14px; border-left:4px solid {config.TLP_ORANGE}; "
        f"background:rgba(0,0,0,0.03); border-radius:6px; font-size:12.5px; color:{config.TEXT}; line-height:1.55;'>"
        "<b>Como ler os percentuais dos totais:</b> cada janela mostra "
        "<i>atividades ÷ HC geral</i> do cluster (o HC é o total de técnicos da coluna HC, o mesmo para todas "
        "as janelas, e muda ao longo do dia conforme o HC do site).<br>"
        "• <b>100%</b> = ideal: há 1 atividade por técnico, a quantidade certa.<br>"
        "• <b style='color:#15803D;'>Abaixo de 100%</b> = há técnicos com folga nessa janela (poucas atividades para o HC).<br>"
        "• <b style='color:" + config.TLP_RED + ";'>Acima de 100%</b> = <b>alerta</b>: há mais atividades "
        "do que técnicos, ou seja, sobrecarga naquela janela."
        "</div>",
        unsafe_allow_html=True,
    )


def tabela_quadro(quadro: pd.DataFrame):
    """Quadro de um dia: Cluster > Bucket × horário, com TOTAL, HC, GAP, HC NEC e Atribuição."""
    if quadro.empty:
        st.info("Sem dados para este dia.")
        return

    cab = (
        "<th style='text-align:center;'>CLUSTER</th><th style='text-align:left;'>BUCKET</th>"
        + "".join(f"<th>{h}</th>" for h in HORARIOS)
        + "<th style='border-left:2px solid rgba(255,255,255,0.35);'>TOTAL</th><th>HC</th><th>GAP</th>"
        "<th>HC NEC</th><th>ATRIB.</th>"
    )

    # Nº de buckets por cluster: a célula do cluster ocupa todas as linhas do grupo (rowspan)
    # e o nome fica centralizado na célula, na horizontal e na vertical.
    qtd_buckets = quadro[quadro["tipo"] == "bucket"].groupby("cluster").size().to_dict()
    linhas, cluster_anterior, i = [], None, 0
    for _, r in quadro.iterrows():
        if r["tipo"] == "bucket":
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            i += 1
            cel = []
            if r["cluster"] != cluster_anterior:
                cel.append(
                    f"<td rowspan='{qtd_buckets[r['cluster']]}' style='text-align:center; vertical-align:middle; "
                    f"font-weight:800; color:{config.TLP_ORANGE}; background:{config.CARD};'>{r['cluster']}</td>"
                )
            cluster_anterior = r["cluster"]
            cel.append(f"<td style='text-align:left; font-weight:700; color:{config.TEXT};'>{r['bucket']}</td>")
            cel += [_cel_horario(r, h) for h in HORARIOS]
            cel += [
                f"<td style='font-weight:800; color:{config.TEXT}; border-left:2px solid {config.CARD_BORDER};'>{r['TOTAL']}</td>",
                f"<td style='font-weight:800; color:{config.TEXT};'>{r['HC']}</td>",
                f"<td>{_gap_pill(r['GAP'])}</td>",
                f"<td style='font-weight:800; color:{config.TEXT};'>{r['HC_NEC']}</td>",
                f"<td>{_atrib_pill(r['ATRIB'])}</td>",
            ]
            linhas.append(f"<tr style='{bg}'>{''.join(cel)}</tr>")
        elif r["tipo"] == "cluster":
            cel = [f"<td colspan='2' style='text-align:left; font-weight:800; color:{config.TEXT};'>TOTAL {r['cluster']}</td>"]
            cel += [_cel_horario(r, h, "cluster") for h in HORARIOS]
            cel += [
                f"<td style='font-weight:800; color:{config.TEXT}; border-left:2px solid {config.CARD_BORDER};'>{r['TOTAL']}</td>",
                f"<td style='font-weight:800; color:{config.TEXT};'>{r['HC']}</td>",
                f"<td>{_gap_pill(r['GAP'])}</td>",
                f"<td style='font-weight:800; color:{config.TEXT};'>{r['HC_NEC']}</td>",
                f"<td>{_atrib_pill(r['ATRIB'])}</td>",
            ]
            linhas.append(f"<tr style='{SUBTOTAL_BG()}'>{''.join(cel)}</tr>")
        else:  # geral
            cel = ["<td colspan='2' style='text-align:left; font-weight:800; color:#FFFFFF;'>TOTAL GERAL</td>"]
            cel += [_cel_horario(r, h, "geral") for h in HORARIOS]
            cel += [
                f"<td style='border-left:2px solid rgba(255,255,255,0.35);'>{pill_total(r['TOTAL'])}</td>",
                f"<td>{pill_total(r['HC'])}</td>",
                f"<td>{_gap_pill(r['GAP'], sobre_gradiente=True)}</td>",
                f"<td>{pill_total(r['HC_NEC'])}</td>",
                f"<td>{_atrib_pill(r['ATRIB'], sobre_gradiente=True)}</td>",
            ]
            linhas.append(f"<tr style='{TOTAL_BG()}'>{''.join(cel)}</tr>")

    tabela = (
        f"<table style='width:100%; min-width:1500px; border-collapse:collapse; font-size:13.5px; "
        f"color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{cab}</tr></thead><tbody>{''.join(linhas)}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)
    nota_carga_por_tecnico()


def tabela_resumo_dias(quadros: list[tuple[str, pd.DataFrame]]):
    """Resumo por cluster dos dias lado a lado (D0, D+1, D+2): Atividades, HC NEC, HC e GAP."""
    if not quadros:
        st.info("Sem dados.")
        return

    cab1 = "<th rowspan='2' style='text-align:left;'>CLUSTER</th>" + "".join(
        f"<th colspan='4' style='text-align:center; border-left:2px solid rgba(255,255,255,0.35);'>{rot}</th>"
        for rot, _ in quadros
    )
    cab2 = "".join(
        "<th style='border-left:2px solid rgba(255,255,255,0.35);'>ATIV.</th><th>HC NEC</th><th>HC</th><th>GAP</th>"
        for _ in quadros
    )

    base = quadros[0][1]
    nomes = [(r["cluster"], r["tipo"]) for _, r in base.iterrows() if r["tipo"] in ("cluster", "geral")]
    linhas = []
    for idx, (nome, tipo) in enumerate(nomes):
        eh_total = tipo == "geral"
        cel = [
            f"<td style='text-align:left; font-weight:800; color:{'#FFFFFF' if eh_total else config.TEXT};'>{nome}</td>"
        ]
        for _, q in quadros:
            r = q[(q["tipo"] == tipo) & (q["cluster"] == nome)].iloc[0]
            esq = f"border-left:2px solid {'rgba(255,255,255,0.35)' if eh_total else config.CARD_BORDER};"
            if eh_total:
                cel += [
                    f"<td style='{esq}'>{pill_total(r['TOTAL'])}</td>", f"<td>{pill_total(r['HC_NEC'])}</td>",
                    f"<td>{pill_total(r['HC'])}</td>", f"<td>{_gap_pill(r['GAP'], True)}</td>",
                ]
            else:
                cel += [
                    f"<td style='{esq} color:{config.TEXT};'>{r['TOTAL']}</td>",
                    f"<td style='font-weight:800; color:{config.TEXT};'>{r['HC_NEC']}</td>",
                    f"<td style='color:{config.TEXT};'>{r['HC']}</td>", f"<td>{_gap_pill(r['GAP'])}</td>",
                ]
        if eh_total:
            estilo = TOTAL_BG()
        else:
            estilo = f"background:{config.CARD if idx % 2 == 0 else config.SURFACE};"
        linhas.append(f"<tr style='{estilo}'>{''.join(cel)}</tr>")

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{cab1}</tr><tr style='{CABECALHO_BG()}'>{cab2}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)