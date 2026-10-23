"""Tabelas da aba "Atribuição" — mesmo visual (cabeçalho em gradiente, subtotal por
cluster, TOTAL GERAL em destaque) das demais tabelas do site."""
import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import (
    CABECALHO_BG, SUBTOTAL_BG, TOTAL_BG, pill, pill_contraste, pill_total, wrapper_tabela,
)
from services.atribuicao import HORARIOS, ROTULO_TURNO


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


def _th_janela(h: str) -> str:
    """Cabeçalho de uma coluna de janela: turno (1º MANHÃ, 2º TARDE...) em cima e a janela embaixo."""
    return (
        f"<th style='line-height:1.25;'>{ROTULO_TURNO[h]}<br>"
        f"<span style='font-weight:500; font-size:11px; opacity:.85;'>{h}</span></th>"
    )


def _cel_horario(r, h: str, estilo: str = "linha") -> str:
    """Célula de uma janela de serviço.
    - "linha" (bucket): apenas o nº de atividades.
    - "cluster" (subtotal) e "geral" (sobre o gradiente): "atividades / HC = atividades por
      técnico" + GAP, tudo na mesma célula (mesmo formato do "BD / TEC = PU" do Backlog Reparo)."""
    ativ, hc, gap = int(r[h]), int(r[f"HC_{h}"]), int(r[f"GAP_{h}"])
    if estilo == "geral":
        cor_txt, cor_hc, peso = "#FFFFFF", "#FFFFFF", 800
    else:
        cor_txt, cor_hc, peso = config.TEXT, config.TLP_ORANGE, (800 if estilo == "cluster" else 600)
    if ativ == 0 and hc == 0:
        return f"<td style='color:{config.TEXT_MUTED};'>0</td>"
    if estilo == "linha":  # linhas de bucket: só o nº de atividades (cálculo fica nos totais)
        return f"<td style='font-size:12.5px; font-weight:{peso}; color:{cor_txt};'>{ativ}</td>"
    razao = f"{ativ / hc:.1f}".replace(".", ",") if hc else "—"
    return (
        f"<td style='white-space:nowrap; font-size:12.5px;'>"
        f"<span style='font-weight:{peso}; color:{cor_txt};'>{ativ}</span>"
        f"<span style='color:{cor_txt}; opacity:.7;'> / </span>"
        f"<span style='font-weight:800; color:{cor_hc};'>{hc}</span>"
        f"<span style='color:{cor_txt}; opacity:.7;'> = </span>"
        f"<span style='font-weight:{peso}; color:{cor_txt};'>{razao}</span> "
        f"{_gap_pill(gap, sobre_gradiente=(estilo == 'geral'))}</td>"
    )


def tabela_quadro(quadro: pd.DataFrame):
    """Quadro de um dia: Cluster > Bucket × horário, com TOTAL, HC, GAP, HC NEC e Atribuição."""
    if quadro.empty:
        st.info("Sem dados para este dia.")
        return

    cab = (
        "<th style='text-align:center;'>CLUSTER</th><th style='text-align:left;'>BUCKET</th>"
        + "".join(_th_janela(h) for h in HORARIOS)
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
        f"<table translate='no' class='notranslate' style='width:100%; min-width:1700px; border-collapse:collapse; font-size:13.5px; "
        f"color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{cab}</tr></thead><tbody>{''.join(linhas)}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)


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
        f"<table translate='no' class='notranslate' style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT}; text-align:center;'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{cab1}</tr><tr style='{CABECALHO_BG()}'>{cab2}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody></table>"
    )
    st.markdown(wrapper_tabela(tabela), unsafe_allow_html=True)