"""
components/tabela_score.py
============================
Tabela HTML do ranking de Score de Performance (services/analitica.py ->
score_performance), no mesmo padrão visual das demais tabelas do site
(cabeçalho em degradê, pills coloridas, moldura com sombra).
"""
import pandas as pd

import config
from components.estilo_tabela import CABECALHO_BG, wrapper_tabela, pill, cor_faixa
from services.analitica import formatar_minutos

_CORES_CLASSIFICACAO = {
    "Destaque": ("#15803D", "rgba(34,197,94,0.16)"),
    "Atenção": (config.TLP_GOLD, "rgba(255,176,32,0.18)"),
    "Ofensor": (config.TLP_RED, "rgba(232,57,29,0.14)"),
}


def _cor_classificacao(classe: str):
    return _CORES_CLASSIFICACAO.get(classe, (config.TEXT_MUTED, "rgba(0,0,0,0.05)"))


def tabela_score_performance(df_score: pd.DataFrame, coluna_grupo: str, top_n: int = None) -> str:
    """Monta o HTML da tabela de ranking. Retorna string HTML pronta pra
    `st.markdown(..., unsafe_allow_html=True)`."""
    if df_score is None or df_score.empty:
        return "<p style='padding:12px;'>Sem OS suficientes neste recorte para calcular o Score (mínimo de amostras não atingido).</p>"

    dados = df_score.head(top_n) if top_n else df_score

    colunas_th = [
        "#", coluna_grupo, "Score", "Classificação", "Eficácia", "PU (méd./dia)",
        "Pontualidade", "% Não Concl.", "Reincidência", "Duração Média", "Caixa Total",
    ]
    cabecalho = "".join(
        f"<th style='{CABECALHO_BG()} padding:10px 12px; text-align:center; white-space:nowrap;'>{c}</th>"
        for c in colunas_th
    )
    cabecalho = cabecalho.replace(
        f"text-align:center; white-space:nowrap;'>{coluna_grupo}",
        f"text-align:left; white-space:nowrap;'>{coluna_grupo}",
    )

    linhas_html = []
    for i, row in dados.reset_index(drop=True).iterrows():
        cor_txt, cor_bg = _cor_classificacao(row["Classificação"])
        badge_classe = pill(row["Classificação"], cor_txt, cor_bg)
        cor_score = cor_faixa(row["Score"], bom=65, medio=45)
        cor_pontualidade = cor_faixa(row["Pontualidade"], bom=80, medio=60)
        fundo_linha = "rgba(0,0,0,0.015)" if i % 2 else "transparent"
        duracao_fmt = formatar_minutos(row.get("Duração Média (min)"))

        linhas_html.append(
            f"<tr style='background:{fundo_linha};'>"
            f"<td style='padding:8px 12px; text-align:center; color:{config.TEXT_MUTED};'>{i + 1}º</td>"
            f"<td style='padding:8px 12px; font-weight:600;'>{row[coluna_grupo]}</td>"
            f"<td style='padding:8px 12px; text-align:center; font-weight:800; color:{cor_score};'>{row['Score']:.1f}</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{badge_classe}</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{row['Eficácia'] * 100:.1f}%</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{row['PU']:.2f}</td>"
            f"<td style='padding:8px 12px; text-align:center; font-weight:600; color:{cor_pontualidade};'>{row['Pontualidade']:.1f}%</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{row['% Não Concluída']:.1f}%</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{row['Taxa Reincidência']:.1f}%</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{duracao_fmt}</td>"
            f"<td style='padding:8px 12px; text-align:center;'>{row['Caixa Total']:.0f}</td>"
            "</tr>"
        )

    tabela_html = (
        "<table style='width:100%; border-collapse:collapse; font-size:13px;'>"
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        "</table>"
    )
    return wrapper_tabela(tabela_html, altura_max=560)
