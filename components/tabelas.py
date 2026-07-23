import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import CABECALHO_BG, TOTAL_BG, pill_total, wrapper_tabela


def _cor_eficacia(valor: float) -> str:
    """Retorna a cor (verde/dourado/vermelho) de acordo com a faixa de eficácia."""
    if valor >= 0.80:
        return "#15803D"
    if valor >= 0.60:
        return config.TLP_GOLD
    return config.TLP_RED


def tabela_matriz(df_matriz: pd.DataFrame, titulo: str, cor_titulo: str = None):
    """
    Renderiza a matriz de produção (BA ou TT) como uma tabela HTML estilizada,
    no padrão visual único do site (cabeçalho em gradiente, números em
    destaque e linha de Total com fundo de marca), com badges de alto
    contraste na coluna Eficácia e nas colunas OK/NOK.
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
    for i, (_, row) in enumerate(df_matriz.iterrows()):
        is_total = row["Cluster"] == "Total"
        peso = "800" if is_total else "600"
        eficacia_pct = f"{row['Eficácia']:.0%}"
        cor_efic = _cor_eficacia(row["Eficácia"])

        if is_total:
            bg = TOTAL_BG
            cor_texto = "#FFFFFF"
            media_txt = f"{row['Média Atrib.']:.2f}"
            pu_txt = f"{row['PU']:.2f}"
            proj_pu_txt = f"{row['Proj. PU']:.2f}"
            cel_cluster = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{row['Cluster']}</td>"
            cel_hc = f"<td>{pill_total(row['HC Ativo'])}</td>"
            cel_caixa = f"<td>{pill_total(row['Caixa Tot'])}</td>"
            cel_esteira = f"<td>{pill_total(row['Esteira'])}</td>"
            cel_bucket = f"<td>{pill_total(row['Bucket'])}</td>"
            cel_media = f"<td>{pill_total(media_txt)}</td>"
            cel_pu = f"<td>{pill_total(pu_txt)}</td>"
            cel_ok = f"<td>{pill_total(row['OK'])}</td>"
            cel_nok = f"<td>{pill_total(row['NOK'])}</td>"
            cel_iniciada = f"<td>{pill_total(row['Iniciada'])}</td>"
            cel_efic = f"<td>{pill_total(eficacia_pct)}</td>"
            cel_proj = f"<td>{pill_total(row['Proj.'])}</td>"
            cel_proj_pu = f"<td>{pill_total(proj_pu_txt)}</td>"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_texto = config.TEXT
            cel_cluster = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{row['Cluster']}</td>"
            cel_hc = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['HC Ativo']}</td>"
            cel_caixa = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Caixa Tot']}</td>"
            cel_esteira = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Esteira']}</td>"
            cel_bucket = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Bucket']}</td>"
            cel_media = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Média Atrib.']:.2f}</td>"
            cel_pu = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['PU']:.2f}</td>"
            cel_ok = f"<td><span style='color:#15803D; font-weight:{peso};'>{row['OK']}</span></td>"
            cel_nok = f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{row['NOK']}</span></td>"
            cel_iniciada = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Iniciada']}</td>"
            cel_efic = f"<td><span style='color:{cor_efic}; font-weight:700;'>{eficacia_pct}</span></td>"
            cel_proj = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj.']}</td>"
            cel_proj_pu = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj. PU']:.2f}</td>"

        celulas = "".join([
            cel_cluster, cel_hc, cel_caixa, cel_esteira, cel_bucket, cel_media,
            cel_pu, cel_ok, cel_nok, cel_iniciada, cel_efic, cel_proj, cel_proj_pu,
        ])

        linhas_html.append(f"<tr style='{bg}'>{celulas}</tr>")

    header_html = "".join(
        f"<th style='text-align:{'left' if c == 'Cluster' else 'center'};'>{c.upper()}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)