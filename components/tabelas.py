import pandas as pd
import streamlit as st

import config


def _cor_eficacia(valor: float) -> str:
    """Retorna a cor (verde/dourado/vermelho) de acordo com a faixa de eficácia."""
    if valor >= 0.80:
        return "#22C55E"
    if valor >= 0.60:
        return config.TLP_GOLD
    return config.TLP_RED


def tabela_matriz(df_matriz: pd.DataFrame, titulo: str, cor_titulo: str = None):
    """
    Renderiza a matriz de produção (BA ou TT) como uma tabela HTML estilizada,
    no padrão visual do dashboard, com destaque de cor na coluna Eficácia e
    a linha de Total em negrito.
    """
    cor_titulo = cor_titulo or config.TLP_ORANGE

    if df_matriz.empty:
        st.markdown(
            f"<h4 style='color:{cor_titulo};'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    colunas = ["Cluster", "HC Ativo", "Caixa Tot", "Esteira", "Bucket",
               "Média Atrib.", "PU", "OK", "NOK", "Iniciada", "Eficácia",
               "Proj.", "Proj. PU"]

    # NOTA: todo o HTML abaixo é montado SEM indentação (linhas começando na
    # coluna 0) de propósito. Se strings HTML multi-linha passadas para
    # st.markdown tiverem 4+ espaços de indentação, o parser de Markdown do
    # Streamlit interpreta parte do conteúdo como bloco de código e quebra o
    # HTML no meio (o efeito visual é texto solto como "</tbody>" aparecendo
    # na tela, com a tabela cortada).

    linhas_html = []
    for _, row in df_matriz.iterrows():
        is_total = row["Cluster"] == "Total"
        peso = "700" if is_total else "500"
        bg = "rgba(255,106,0,0.08)" if is_total else "transparent"
        borda_topo = f"border-top: 1px solid {config.CARD_BORDER};" if is_total else ""

        eficacia_pct = f"{row['Eficácia']:.0%}"
        cor_efic = _cor_eficacia(row["Eficácia"])

        celulas = "".join([
            f"<td style=\"text-align:left; font-weight:{peso};\">{row['Cluster']}</td>",
            f"<td>{row['HC Ativo']}</td>",
            f"<td>{row['Caixa Tot']}</td>",
            f"<td>{row['Esteira']}</td>",
            f"<td>{row['Bucket']}</td>",
            f"<td>{row['Média Atrib.']:.2f}</td>",
            f"<td>{row['PU']:.2f}</td>",
            f"<td style=\"color:#22C55E;\">{row['OK']}</td>",
            f"<td style=\"color:{config.TLP_RED};\">{row['NOK']}</td>",
            f"<td>{row['Iniciada']}</td>",
            f"<td style=\"color:{cor_efic}; font-weight:600;\">{eficacia_pct}</td>",
            f"<td>{row['Proj.']}</td>",
            f"<td>{row['Proj. PU']:.2f}</td>",
        ])

        linhas_html.append(f"<tr style=\"background:{bg}; {borda_topo}\">{celulas}</tr>")

    header_html = "".join(
        f"<th style='text-align:{'left' if c == 'Cluster' else 'center'};'>{c.upper()}</th>"
        for c in colunas
    )

    html = (
        f"<h4 style=\"color:{cor_titulo}; margin-bottom:6px;\">{titulo}</h4>"
        f"<div style=\"overflow-x:auto; border:1px solid {config.CARD_BORDER}; border-radius:10px;\">"
        f"<table style=\"width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};\">"
        f"<thead><tr style=\"background:{config.SURFACE}; color:{config.TEXT_MUTED};\">{header_html}</tr></thead>"
        f"<tbody style=\"text-align:center;\">{''.join(linhas_html)}</tbody>"
        f"</table>"
        f"</div>"
    )

    st.markdown(html, unsafe_allow_html=True)
