import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config
from services.grupos import serie_diaria_indicadores

FONTE = "Poppins, sans-serif"


def _tema(fig: go.Figure, titulo: str = "", altura: int = 380) -> go.Figure:
    """Aplica o tema visual padrão (dark + paleta TLP) a uma figura Plotly."""
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color=config.TEXT, family=FONTE)) if titulo else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, color=config.TEXT_MUTED, size=12),
        height=altura,
        margin=dict(l=10, r=10, t=50 if titulo else 20, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=config.TEXT_MUTED)),
        colorway=config.CHART_COLORWAY,
        hoverlabel=dict(bgcolor=config.CARD, font_color=config.TEXT, font_family=FONTE),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=config.TEXT_MUTED)
    fig.update_yaxes(showgrid=True, gridcolor=config.CARD_BORDER, zeroline=False, color=config.TEXT_MUTED)
    return fig


def grafico_ranking(df: pd.DataFrame, coluna_valor: str, titulo: str = "", top_n: int = 15) -> go.Figure:
    """Gráfico de barras horizontais com o ranking top-N por uma coluna numérica."""
    if df.empty or coluna_valor not in df.columns:
        return _tema(go.Figure(), titulo)

    rotulo = df.columns[0]
    dados = df.sort_values(coluna_valor, ascending=False).head(top_n).sort_values(coluna_valor)

    fig = px.bar(
        dados,
        x=coluna_valor,
        y=rotulo,
        orientation="h",
        text=coluna_valor,
        color=coluna_valor,
        color_continuous_scale=config.CHART_GRADIENT_SCALE,
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False)
    return _tema(fig, titulo, altura=max(320, 28 * len(dados)))


def grafico_producao_dia(df: pd.DataFrame, coluna_data: str = "Data") -> go.Figure:
    """Gráfico de área com o volume de atividades por dia + linha de PU (eixo secundário)."""
    serie = serie_diaria_indicadores(df, coluna_data)
    if serie.empty:
        return _tema(go.Figure(), "Produção Diária")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=serie["Data"], y=serie["Atividades"],
            name="Atividades", mode="lines",
            line=dict(color=config.TLP_ORANGE, width=3),
            fill="tozeroy", fillcolor="rgba(255,106,0,0.15)",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=serie["Data"], y=serie["PU"],
            name="PU", mode="lines+markers+text",
            line=dict(color="#7B8CDE", width=3, dash="dot"),
            marker=dict(size=6, color="#7B8CDE"),
            text=serie["PU"].round(2),
            texttemplate="%{text}", textposition="top center",
            textfont=dict(size=10, color="#7B8CDE"),
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Atividades", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="PU", secondary_y=True, showgrid=False)
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    return _tema(fig, "Produção Diária", altura=340)


def grafico_atribuicao_pu(df: pd.DataFrame, coluna_data: str = "Data") -> go.Figure:
    """
    Gráfico "Atribuição x PU" dia a dia — réplica do gráfico do Excel/Power
    BI (linha roxa = Atribuição, linha laranja = PU, com rótulos de valor
    em cada ponto). Substitui o antigo "Eficácia x Produtividade".
    """
    serie = serie_diaria_indicadores(df, coluna_data)
    titulo = "Atribuição x PU"
    if serie.empty:
        return _tema(go.Figure(), titulo)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie["Data"], y=serie["Atribuição"],
            name="Atribuição", mode="lines+markers+text",
            line=dict(color="#7B4FDE", width=3, shape="spline"),
            marker=dict(size=6, color="#7B4FDE"),
            text=serie["Atribuição"].round(2),
            texttemplate="%{text}", textposition="top center",
            textfont=dict(size=10, color="#7B4FDE"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["Data"], y=serie["PU"],
            name="PU", mode="lines+markers+text",
            line=dict(color=config.TLP_ORANGE, width=3, shape="spline"),
            marker=dict(size=6, color=config.TLP_ORANGE),
            text=serie["PU"].round(2),
            texttemplate="%{text}", textposition="bottom center",
            textfont=dict(size=10, color=config.TLP_ORANGE),
        )
    )
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(tickangle=-30)
    return _tema(fig, titulo, altura=360)


def grafico_pareto_causa(df: pd.DataFrame) -> go.Figure:
    """
    Gráfico único de Pareto das pendências (Status = 'Não Concluída') agrupadas
    pela coluna 'CAUSA', comparando BA e TT lado a lado (colunas duplas) por
    causa, cada lado com sua linha tracejada de percentual acumulado (Pareto).
    Sem título embutido — o título/contexto já fica na seção acima, no dashboard.
    """
    dados = df[df["Status"] == "Não Concluída"]
    tab = dados.groupby(["CAUSA", "Lado"]).size().unstack(fill_value=0)

    for lado in ("BA", "TT"):
        if lado not in tab.columns:
            tab[lado] = 0

    if tab.empty:
        return _tema(go.Figure(), "")

    tab = tab.assign(TOTAL=tab["BA"] + tab["TT"]).sort_values("TOTAL", ascending=False).drop(columns="TOTAL")

    causas = tab.index.tolist()
    ba_vals = tab["BA"].values
    tt_vals = tab["TT"].values

    pareto_ba = pd.Series(ba_vals).cumsum() / max(ba_vals.sum(), 1) * 100
    pareto_tt = pd.Series(tt_vals).cumsum() / max(tt_vals.sum(), 1) * 100

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=causas, y=ba_vals, name="Total BA",
            marker_color=config.CHART_BA,
            text=ba_vals, texttemplate="%{text:,.0f}", textposition="outside",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=causas, y=tt_vals, name="Total TT",
            marker_color=config.CHART_TT,
            text=tt_vals, texttemplate="%{text:,.0f}", textposition="outside",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=causas, y=pareto_ba.values, name="Pareto BA",
            mode="lines+markers+text",
            line=dict(color=config.CHART_BA, width=2, dash="dash"),
            marker=dict(size=6, color=config.CHART_BA),
            text=pareto_ba.round(0),
            texttemplate="%{text:.0f}%", textposition="top center",
            textfont=dict(size=10, color=config.CHART_BA),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=causas, y=pareto_tt.values, name="Pareto TT",
            mode="lines+markers+text",
            line=dict(color=config.CHART_TT, width=2, dash="dash"),
            marker=dict(size=6, color=config.CHART_TT),
            text=pareto_tt.round(0),
            texttemplate="%{text:.0f}%", textposition="bottom center",
            textfont=dict(size=10, color=config.CHART_TT),
        ),
        secondary_y=True,
    )

    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Total", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="Pareto (%)", secondary_y=True, range=[0, 110], showgrid=False)
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(tickangle=-20)
    return _tema(fig, "", altura=440)


def grafico_media_atribuida_pu(ranking: pd.DataFrame, coluna_grupo: str = "Coordenador") -> go.Figure:
    """
    Gráfico "Média Atribuída x PU" por grupo (Coordenador, Supervisor etc.):
    barras com a Média Atribuída (eixo primário) + linha com o PU (eixo
    secundário), ordenado pela Média Atribuída decrescente. Sem título
    embutido — o título/contexto fica na seção do dashboard.
    """
    if ranking.empty or coluna_grupo not in ranking.columns or "Média Atribuída" not in ranking.columns or "PU" not in ranking.columns:
        return _tema(go.Figure(), "")

    dados = ranking.sort_values("Média Atribuída", ascending=False)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=dados[coluna_grupo], y=dados["Média Atribuída"],
            name="Média Atribuída",
            marker_color="#7B4FDE",
            text=dados["Média Atribuída"].round(2),
            texttemplate="%{text:.2f}", textposition="outside",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=dados[coluna_grupo], y=dados["PU"],
            name="PU", mode="lines+markers+text",
            line=dict(color=config.TLP_ORANGE, width=3),
            marker=dict(size=8, color=config.TLP_ORANGE),
            text=dados["PU"].round(2),
            texttemplate="%{text:.2f}", textposition="top center",
            textfont=dict(size=10, color=config.TLP_ORANGE),
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Média Atribuída", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="PU", secondary_y=True, showgrid=False)
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(tickangle=-20)
    return _tema(fig, "", altura=380)


def grafico_status_pizza(status_counts: dict, titulo: str = "Distribuição por Status") -> go.Figure:
    """Gráfico de rosca com a distribuição de status das atividades."""
    labels = list(status_counts.keys())
    values = list(status_counts.values())

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=config.CHART_COLORWAY, line=dict(color=config.BACKGROUND, width=2)),
                textfont=dict(color="white", size=12),
            )
        ]
    )
    return _tema(fig, titulo, altura=340)


def grafico_comparativo_ba_tt(valor_ba: float, valor_tt: float, titulo: str, formato: str = "") -> go.Figure:
    """Gráfico de barras simples comparando BA vs TT para um indicador."""
    fig = go.Figure(
        data=[
            go.Bar(
                x=["BA", "TT"],
                y=[valor_ba, valor_tt],
                marker_color=[config.CHART_BA, config.CHART_TT],
                text=[f"{valor_ba:{formato}}", f"{valor_tt:{formato}}"] if formato else [valor_ba, valor_tt],
                textposition="outside",
            )
        ]
    )
    return _tema(fig, titulo, altura=280)


def grafico_evolucao_temporal(serie: pd.DataFrame, media: float = None, titulo: str = "") -> go.Figure:
    """
    Linha de evolução (faixa horária ou dia a dia) com marcadores, rótulos
    de valor e uma linha tracejada de referência com a média da série —
    réplica do gráfico "EVOLUÇÃO TEMPORAL" do Power BI.

    Espera um DataFrame com 2 colunas: [rótulo do eixo X, valor numérico].
    """
    if serie.empty:
        return _tema(go.Figure(), titulo)

    col_x, col_y = serie.columns[0], serie.columns[1]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie[col_x],
            y=serie[col_y],
            mode="lines+markers+text",
            line=dict(color=config.TLP_RED, width=3, shape="spline"),
            marker=dict(size=7, color=config.TLP_RED, line=dict(color=config.BACKGROUND, width=1)),
            text=serie[col_y],
            texttemplate="%{text}",
            textposition="top center",
            textfont=dict(size=11, color=config.TEXT),
            fill="tozeroy",
            fillcolor="rgba(232,57,29,0.10)",
            name="Valor",
        )
    )

    if media is not None:
        fig.add_hline(
            y=media,
            line_dash="dash",
            line_color=config.TLP_GOLD,
            annotation_text=f"Média: {media:,.1f}".replace(",", "."),
            annotation_position="top left",
            annotation_font_color=config.TLP_GOLD,
        )

    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-30)
    return _tema(fig, titulo, altura=360)


def grafico_eficacia_pu(ranking: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Gráfico de dispersão Eficácia x PU para identificar melhores performances."""
    if ranking.empty or "Eficácia" not in ranking.columns or "PU" not in ranking.columns:
        return _tema(go.Figure(), "Eficácia x Produtividade (PU)")

    rotulo = ranking.columns[0]
    dados = ranking.head(top_n)

    fig = px.scatter(
        dados,
        x="PU",
        y="Eficácia",
        size="Caixa Total" if "Caixa Total" in dados.columns else None,
        color="Eficácia",
        color_continuous_scale=config.CHART_GRADIENT_SCALE,
        hover_name=rotulo,
        text=rotulo,
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10, color=config.TEXT_MUTED))
    fig.update_layout(coloraxis_showscale=False)
    fig.update_yaxes(tickformat=".0%")
    return _tema(fig, "Eficácia x Produtividade (PU)", altura=420)