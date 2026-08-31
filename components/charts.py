import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

import config
from services.grupos import serie_diaria_indicadores

FONTE = "Poppins, sans-serif"

# Config padrão passada a TODO st.plotly_chart do site (via opcoes_grafico) —
# deixa a barra de ferramentas do Plotly SEMPRE visível (não só no hover),
# com destaque pro botão de câmera (📷 "Baixar como imagem"), remove o logo
# da Plotly e os botões que não fazem sentido nesses gráficos (seleção por
# laço/retângulo, zoom in/out avulso etc.), mantendo pan/zoom/reset e a
# própria câmera.
_PLOTLY_CONFIG_BASE = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "zoomIn2d", "zoomOut2d",
        "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines",
    ],
}


def opcoes_grafico(nome_arquivo: str = "grafico") -> dict:
    """
    Config a passar em `st.plotly_chart(fig, config=opcoes_grafico("..."))`
    — deixa o botão de câmera (imprimir/baixar como PNG) sempre visível no
    canto superior direito do gráfico, já com um nome de arquivo descritivo
    (em vez do genérico 'newplot.png') e resolução dobrada (scale=2), boa
    o bastante pra colar num relatório/apresentação.
    """
    cfg = dict(_PLOTLY_CONFIG_BASE)
    cfg["toImageButtonOptions"] = {
        "format": "png",
        "filename": nome_arquivo,
        "scale": 2,
    }
    return cfg


def _tema(fig: go.Figure, titulo: str = "", altura: int = 380) -> go.Figure:
    """Aplica o tema visual padrão (dark + paleta TLP) a uma figura Plotly."""
    layout_kwargs = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, color=config.TEXT_MUTED, size=12),
        height=altura,
        margin=dict(l=10, r=10, t=50 if titulo else 20, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=config.TEXT_MUTED)),
        colorway=config.CHART_COLORWAY,
        hoverlabel=dict(bgcolor=config.CARD, font_color=config.TEXT, font_family=FONTE),
    )
    # IMPORTANTE: só inclui a chave 'title' quando há título de fato. Passar
    # title=None explicitamente para o Plotly faz o Plotly.js renderizar o
    # texto literal "undefined" no lugar do título (em vez de simplesmente
    # omiti-lo) — por isso o dict nem chega a ganhar essa chave aqui.
    if titulo:
        layout_kwargs["title"] = dict(text=titulo, font=dict(size=16, color=config.TEXT, family=FONTE))

    fig.update_layout(**layout_kwargs)
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


def grafico_tempo_inicio_janela(df: pd.DataFrame, coluna_valor: str = "_tempo_medio_min", titulo: str = "") -> go.Figure:
    """
    Barras verticais com o tempo médio até o início por Janela de Serviço.
    Ao contrário de `grafico_ranking`, mantém a ordem cronológica das
    janelas (a ordem em que vêm no `df`) em vez de reordenar por valor —
    faz mais sentido comparar o dia visualmente na sequência real.
    """
    if df.empty or coluna_valor not in df.columns or "Janela" not in df.columns:
        return _tema(go.Figure(), titulo)

    fig = px.bar(
        df,
        x="Janela",
        y=coluna_valor,
        text=coluna_valor,
        color=coluna_valor,
        color_continuous_scale=config.CHART_GRADIENT_SCALE,
    )
    fig.update_traces(texttemplate="%{text:,.0f} min", textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False, xaxis_title="", yaxis_title="Minutos")
    return _tema(fig, titulo, altura=380)


def renderizar_grafico_scroll(fig: go.Figure, n_categorias: int, largura_por_categoria: int = 110,
                               largura_minima: int = 700, altura: int = 380, nome_arquivo: str = "grafico") -> None:
    """
    Renderiza uma figura Plotly (barras) dentro de um cartão com rolagem
    HORIZONTAL própria — pensado pra gráficos com muitas categorias no
    eixo X (ex.: uma barra por Janela de Serviço), onde `width="stretch"`
    espremeria os rótulos até ficarem ilegíveis.

    A figura ganha uma largura mínima fixa (proporcional a `n_categorias`)
    e só o cartão ao redor rola por dentro quando ultrapassa a largura
    disponível — a página em si não estica. Em telas largas o suficiente
    pra caber tudo, não aparece rolagem nenhuma.
    """
    largura_px = max(largura_minima, n_categorias * largura_por_categoria)
    fig.update_layout(width=largura_px, height=altura, margin=dict(l=10, r=10, t=fig.layout.margin.t or 50, b=10))

    cfg = dict(_PLOTLY_CONFIG_BASE)
    cfg["toImageButtonOptions"] = {"format": "png", "filename": nome_arquivo, "scale": 2}

    html_grafico = fig.to_html(include_plotlyjs="cdn", full_html=False, config=cfg)
    html_final = (
        "<div style='overflow-x:auto; overflow-y:hidden; "
        f"background:{config.CARD}; border-radius:10px;'>"
        f"<div style='width:{largura_px}px;'>{html_grafico}</div>"
        "</div>"
    )
    components.html(html_final, height=altura + 40, scrolling=False)


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
            fill="tozeroy", fillcolor="rgba(46,99,199,0.15)",
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


def grafico_evolucao_pu(serie: pd.DataFrame) -> go.Figure:
    """
    Evolução do PU ao longo do dia, ponto a ponto por horário de extração
    (a cada ~30 min), com a linha de Meta PU como referência.

    Espera um DataFrame no formato de `carregar_historico_intradia`
    (colunas Hora, PU), já ordenado cronologicamente.
    """
    titulo = "Evolução PU"
    if serie.empty or "Hora" not in serie.columns:
        return _tema(go.Figure(), titulo)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie["Hora"], y=serie["PU"],
            name="PU", mode="lines+markers+text",
            line=dict(color=config.TLP_ORANGE, width=3, shape="spline", smoothing=0.7),
            marker=dict(size=6, color=config.TLP_ORANGE),
            text=serie["PU"].round(2),
            texttemplate="<b>%{text}</b>", textposition="top center",
            textfont=dict(size=13, color=config.TLP_ORANGE),
        )
    )
    fig.add_hline(
        y=config.META_PU_ALVO, line_dash="dash", line_color=config.TLP_ORANGE, opacity=0.4,
        annotation_text=f"Meta PU: {config.META_PU_ALVO:.1f}",
        annotation_position="bottom right", annotation_font_color=config.TLP_ORANGE,
    )

    pu_max = max(serie["PU"].max(), config.META_PU_ALVO)
    fig.update_yaxes(title_text="PU", showgrid=True, gridcolor=config.CARD_BORDER, range=[0, pu_max * 1.35])
    fig.update_xaxes(title_text="Horário da extração")
    fig.update_layout(showlegend=False)
    return _tema(fig, titulo, altura=300)


def grafico_evolucao_eficacia(serie: pd.DataFrame) -> go.Figure:
    """
    Evolução da Eficácia ao longo do dia, ponto a ponto por horário de
    extração (a cada ~30 min).

    Espera um DataFrame no formato de `carregar_historico_intradia`
    (colunas Hora, Eficácia), já ordenado cronologicamente.
    """
    titulo = "Evolução Eficácia"
    if serie.empty or "Hora" not in serie.columns:
        return _tema(go.Figure(), titulo)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie["Hora"], y=serie["Eficácia"],
            name="Eficácia", mode="lines+markers+text",
            line=dict(color="#7B8CDE", width=3, dash="dot", shape="spline", smoothing=0.7),
            marker=dict(size=6, color="#7B8CDE"),
            text=(serie["Eficácia"] * 100).round(0).astype(int).astype(str) + "%",
            texttemplate="<b>%{text}</b>", textposition="top center",
            textfont=dict(size=13, color="#7B8CDE"),
        )
    )

    eff_min, eff_max = serie["Eficácia"].min(), serie["Eficácia"].max()
    fig.update_yaxes(
        title_text="Eficácia", showgrid=True, gridcolor=config.CARD_BORDER, tickformat=".0%",
        range=[max(0.0, eff_min - 0.1), min(1.0, eff_max) + 0.1],
    )
    fig.update_xaxes(title_text="Horário da extração")
    fig.update_layout(showlegend=False)
    return _tema(fig, titulo, altura=300)



def grafico_fechamento_mensal(serie_grupo: pd.DataFrame, indicador: str = "PU", coluna_grupo: str = "Estado") -> go.Figure:
    """
    Evolução diária de um indicador (PU ou Eficácia) ao longo do mês,
    com uma linha por grupo (Estado ou Cluster) — réplica do comportamento
    do PAINEL de fechamento do Excel/Power BI, mas desenhada com Plotly no
    padrão visual do site.

    Espera um DataFrame no formato de `serie_diaria_por_grupo` (colunas
    <coluna_grupo>, Data, ..., indicador). Quando `coluna_grupo` é "Estado",
    usa as cores fixas SC/RS da marca; para outras dimensões (ex.: Cluster,
    que pode ter muitos valores), cicla pela paleta sequencial do site.
    """
    titulo = f"Evolução Diária — {indicador}"
    if serie_grupo.empty or indicador not in serie_grupo.columns or coluna_grupo not in serie_grupo.columns:
        return _tema(go.Figure(), titulo)

    cores_estado = {"SC": config.CHART_BA, "RS": config.TLP_ORANGE}
    grupos = sorted(serie_grupo[coluna_grupo].dropna().unique())
    fig = go.Figure()

    for i, grupo in enumerate(grupos):
        sub = serie_grupo[serie_grupo[coluna_grupo] == grupo].sort_values("Data")
        if coluna_grupo == "Estado":
            cor = cores_estado.get(grupo, config.TLP_GOLD)
        else:
            cor = config.CHART_COLORWAY[i % len(config.CHART_COLORWAY)]
        fig.add_trace(
            go.Scatter(
                x=sub["Data"], y=sub[indicador],
                name=str(grupo), mode="lines+markers",
                line=dict(color=cor, width=3, shape="spline"),
                marker=dict(size=5, color=cor),
            )
        )

    if indicador == "PU":
        fig.add_hline(
            y=config.META_PU_ALVO, line_dash="dash", line_color=config.TEXT_MUTED,
            annotation_text=f"Meta PU: {config.META_PU_ALVO:.1f}",
            annotation_position="top left", annotation_font_color=config.TEXT_MUTED,
        )
        fig.update_yaxes(title_text="PU")
    elif indicador == "Eficácia":
        fig.add_hline(
            y=config.META_EFICACIA_ALVO, line_dash="dash", line_color=config.TEXT_MUTED,
            annotation_text=f"Meta Eficácia: {config.META_EFICACIA_ALVO:.0%}",
            annotation_position="top left", annotation_font_color=config.TEXT_MUTED,
        )
        fig.update_yaxes(title_text="Eficácia", tickformat=".0%")

    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(tickangle=-30)
    return _tema(fig, titulo, altura=360)


_MESES_ABREV = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}


def _rotulos_dia(datas) -> list:
    """Formata uma coluna de datas como rótulos categóricos 'dd/mmm' (ex.: '01/jul'),
    evitando que o Plotly trate o eixo X como um eixo de tempo contínuo (o que
    comprime/distorce os dias quando há poucos pontos ou datas espaçadas)."""
    rotulos = []
    for d in datas:
        try:
            rotulos.append(f"{d.day:02d}/{_MESES_ABREV.get(d.month, d.month)}")
        except AttributeError:
            rotulos.append(str(d))
    return rotulos


def grafico_eficacia_diaria(serie_dia: pd.DataFrame) -> go.Figure:
    """
    "Eficácia Diária" — réplica exata do gráfico do Excel/Power BI: barras
    de Concluída e Improdutiva lado a lado por dia, com uma linha tracejada
    de Eficácia % (eixo secundário) e um rótulo em cada ponto da linha.

    Espera um DataFrame no formato diário de uma única série (Data,
    Concluída, Improdutiva, Eficácia) — ex.: a série de um Estado/Cluster
    já filtrada e ordenada por Data (sem a linha 'Total Mês').
    """
    if serie_dia.empty or "Data" not in serie_dia.columns:
        return _tema(go.Figure())

    serie = serie_dia.sort_values("Data")
    rotulos = _rotulos_dia(serie["Data"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=rotulos, y=serie["Concluída"], name="Concluída",
            marker_color="#15803D",
            text=serie["Concluída"], texttemplate="<b>%{text:,.0f}</b>", textposition="outside",
            textfont=dict(size=12, color="#0F5C2A"),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=rotulos, y=serie["Improdutiva"], name="Improdutiva",
            marker_color=config.TLP_RED,
            text=serie["Improdutiva"], texttemplate="<b>%{text:,.0f}</b>", textposition="outside",
            textfont=dict(size=12, color="#B32A14"),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=rotulos, y=serie["Eficácia"], name="Eficácia %",
            mode="lines+markers+text",
            line=dict(color=config.TEXT_MUTED, width=2, dash="dot"),
            marker=dict(size=6, color=config.TEXT_MUTED),
            text=[f"{v:.0%}" for v in serie["Eficácia"]],
            texttemplate="<b>%{text}</b>", textposition="top center",
            textfont=dict(size=11, color=config.TEXT),
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Atividades", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="Eficácia %", secondary_y=True, showgrid=False, tickformat=".0%")
    fig.update_layout(barmode="group", showlegend=False)
    return _tema(fig, altura=360)


def grafico_produtividade_diaria(serie_dia: pd.DataFrame) -> go.Figure:
    """
    "Produtividade Diária" — réplica exata do gráfico do Excel/Power BI:
    barras de Técnicos por dia, com uma linha tracejada de PU (eixo
    secundário) e um rótulo em cada ponto/barra.

    Espera um DataFrame no formato diário de uma única série (Data,
    Técnicos, PU) — ex.: a série de um Estado/Cluster já filtrada e
    ordenada por Data (sem a linha 'Total Mês').
    """
    if serie_dia.empty or "Data" not in serie_dia.columns:
        return _tema(go.Figure())

    serie = serie_dia.sort_values("Data")
    rotulos = _rotulos_dia(serie["Data"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=rotulos, y=serie["Técnicos"], name="Técnicos",
            marker_color=config.TEXT,
            text=serie["Técnicos"], texttemplate="<b>%{text:,.0f}</b>", textposition="outside",
            textfont=dict(size=12, color=config.TEXT),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=rotulos, y=serie["PU"], name="PU",
            mode="lines+markers+text",
            line=dict(color=config.TLP_ORANGE, width=2, dash="dot"),
            marker=dict(size=6, color=config.TLP_ORANGE),
            text=serie["PU"].round(2),
            texttemplate="<b>%{text}</b>", textposition="top center",
            textfont=dict(size=11, color="#CC5500"),
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Técnicos", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="PU", secondary_y=True, showgrid=False)
    fig.update_layout(showlegend=False)
    return _tema(fig, altura=360)


def cabecalho_grafico_combo(titulo: str, itens: list) -> str:
    """
    Monta um cabeçalho HTML com o título do gráfico e a legenda customizada
    (quadradinho para barra, tracinho pontilhado para linha) logo em
    seguida, tudo centralizado no topo — usado para os gráficos combo
    (Eficácia Diária / Produtividade Diária).

    Renderizado via st.markdown ANTES do st.plotly_chart, com o gráfico já
    sem título/legenda internos (showlegend=False). Isso evita depender do
    posicionamento (x/y) da legenda nativa do Plotly, que ficava sujeito a
    colidir com o eixo secundário/conteúdo do gráfico dependendo do
    navegador — com HTML puro o alinhamento é sempre exato.

    `itens`: lista de tuplas (rótulo, cor, tipo), tipo = "barra" ou "linha".
    """
    badges = []
    for label, cor, tipo in itens:
        if tipo == "linha":
            swatch = (
                f"<span style='display:inline-block; width:14px; height:0; "
                f"border-top:2px dotted {cor}; margin-right:5px; vertical-align:middle;'></span>"
            )
        else:
            swatch = (
                f"<span style='display:inline-block; width:10px; height:10px; "
                f"background:{cor}; border-radius:2px; margin-right:5px; vertical-align:middle;'></span>"
            )
        badges.append(
            f"<span style='margin-left:14px; font-size:12.5px; color:{config.TEXT_MUTED}; white-space:nowrap;'>"
            f"{swatch}{label}</span>"
        )

    return (
        f"<div style='display:flex; justify-content:center; align-items:center; "
        f"flex-wrap:wrap; gap:2px; margin-bottom:6px;'>"
        f"<h4 style='color:{config.TEXT}; margin:0; font-size:16px; font-weight:700; white-space:nowrap;'>{titulo}</h4>"
        f"<div style='display:flex; align-items:center; flex-wrap:wrap;'>{''.join(badges)}</div>"
        f"</div>"
    )


def _cor_gradiente_marca(n: int) -> list:
    """Gera N cores em degradê a partir dos stops de marca do tema ativo
    (config.BRAND_GRADIENT_STOPS — navy escuro→azul vibrante no tema navy,
    vermelho→laranja→dourado no tema laranja). Índice 0 recebe o stop mais
    escuro; usado para colorir barras de ranking/Pareto (maior valor =
    tom mais forte) sempre respeitando o tema em uso, sem precisar de
    nenhuma cor fixa."""
    stops = getattr(config, "BRAND_GRADIENT_STOPS", [config.TLP_RED, config.TLP_ORANGE, config.TLP_GOLD])
    if n <= 1:
        return [stops[-1]]

    def _hex_para_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _rgb_para_hex(rgb):
        return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, round(c))) for c in rgb])

    pontos = [_hex_para_rgb(s) for s in stops]
    segmentos = len(pontos) - 1
    cores = []
    for i in range(n):
        pos = (i / (n - 1)) * segmentos
        seg = min(int(pos), segmentos - 1)
        frac = pos - seg
        c0, c1 = pontos[seg], pontos[seg + 1]
        rgb = tuple(c0[k] + (c1[k] - c0[k]) * frac for k in range(3))
        cores.append(_rgb_para_hex(rgb))
    return cores


def grafico_pareto_causa(df: pd.DataFrame, lado: str = "BA") -> go.Figure:
    """
    Gráfico de Pareto das pendências (Status = 'Não Concluída') de UM lado
    (BA ou TT) agrupadas por Motivo da Pendência — barras em degradê
    seguindo a cor da marca do tema ativo (navy ou laranja) e linha
    tracejada do percentual acumulado (Pareto). Pensado pra ficar logo
    abaixo da matriz de produção do mesmo lado, dentro da mesma área de
    "Copiar imagem".
    """
    coluna_motivo = "Motivo da Pendência" if "Motivo da Pendência" in df.columns else "CAUSA"
    dados = df[(df["Status"] == "Não Concluída") & (df["Lado"] == lado)]
    contagem = dados.groupby(coluna_motivo).size().sort_values(ascending=False)

    if contagem.empty:
        return _tema(go.Figure(), "")

    causas = contagem.index.tolist()
    valores = contagem.values
    pareto = pd.Series(valores).cumsum() / max(valores.sum(), 1) * 100
    cores_barras = _cor_gradiente_marca(len(causas))

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=causas, y=valores, name=f"Total {lado}",
            marker_color=cores_barras,
            text=valores, texttemplate="%{text:,.0f}", textposition="outside",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=causas, y=pareto.values, name="Pareto acumulado",
            mode="lines+markers+text",
            line=dict(color=config.TLP_RED, width=2, dash="dash"),
            marker=dict(size=6, color=config.TLP_RED),
            text=pareto.round(0),
            texttemplate="%{text:.0f}%", textposition="top center",
            textfont=dict(size=10, color=config.TLP_RED),
        ),
        secondary_y=True,
    )

    fig.update_layout(barmode="group", showlegend=False)
    fig.update_yaxes(title_text="Total", secondary_y=False, showgrid=True, gridcolor=config.CARD_BORDER)
    fig.update_yaxes(title_text="Pareto (%)", secondary_y=True, range=[0, 110], showgrid=False)
    fig.update_xaxes(tickangle=-20)
    return _tema(fig, "", altura=380)


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
            fillcolor="rgba(240,68,56,0.10)",
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