import pandas as pd

# ------------------------------------------------------------------
# ANÁLISE P — réplica das medidas DAX QTD_P0 / QTD_P1 / QTD_P2 / QTD_P3 /
# QTD_MAIOR_P3.
#
# Para cada Técnico com ao menos uma atividade não "Cancelada" (a
# população definida pelo filtro CALCULATE(..., Status <> "Cancelada")
# da medida original), conta quantas atividades ele tem com
# Status == "Concluída" e classifica:
#   0 concluídas   -> P0
#   1 concluída    -> P1
#   2 concluídas   -> P2
#   3 concluídas   -> P3
#   >3 concluídas  -> >P3
# ------------------------------------------------------------------

FAIXAS_P = ["P0", "P1", "P2", "P3", ">P3"]


def _classificar(qtd: int) -> str:
    if qtd <= 0:
        return "P0"
    if qtd == 1:
        return "P1"
    if qtd == 2:
        return "P2"
    if qtd == 3:
        return "P3"
    return ">P3"


def concluidas_por_tecnico(df: pd.DataFrame, coluna_tecnico: str = "Técnico") -> pd.Series:
    """Qtd de atividades 'Concluída' por técnico (população = técnicos com
    ao menos 1 atividade não Cancelada, igual à medida DAX original)."""
    if df.empty or coluna_tecnico not in df.columns or "Status" not in df.columns:
        return pd.Series(dtype=int)

    populacao = df.loc[df["Status"] != "Cancelada", coluna_tecnico].dropna().unique()
    concluidas = df.loc[df["Status"] == "Concluída"].groupby(coluna_tecnico).size()

    return pd.Series({t: int(concluidas.get(t, 0)) for t in populacao})


def classificacao_tecnicos(df: pd.DataFrame, coluna_tecnico: str = "Técnico") -> pd.DataFrame:
    """
    Tabela Técnico -> Concluídas -> Classificação (P0..>P3), com
    Coordenador/Supervisor/Cluster/Lado anexados (primeiro valor
    encontrado para o técnico) — base para a segmentação hierárquica
    Coordenador > Supervisor > Técnico.
    """
    concl = concluidas_por_tecnico(df, coluna_tecnico)
    if concl.empty:
        return pd.DataFrame()

    colunas_extra = [c for c in ["Coordenador", "Supervisor", "Cluster", "Lado"] if c in df.columns]
    mapa = (
        df.dropna(subset=[coluna_tecnico])
        .drop_duplicates(subset=[coluna_tecnico])
        .set_index(coluna_tecnico)[colunas_extra]
    )

    tabela = pd.DataFrame({coluna_tecnico: concl.index, "Concluídas": concl.values}).set_index(coluna_tecnico)
    tabela = tabela.join(mapa, how="left")
    tabela["Classificação"] = tabela["Concluídas"].apply(_classificar)
    return tabela.reset_index()


def matriz_analise_p(df: pd.DataFrame, coluna_grupo: str = "Supervisor") -> pd.DataFrame:
    """
    Matriz P0..>P3 agrupada por `coluna_grupo` (Supervisor, Coordenador ou
    Cluster) com uma linha de TOTAL — réplica da tabela "PRODUTIVIDADE POR
    SUPERVISOR - TÉCNICO" do Power BI.
    """
    tabela = classificacao_tecnicos(df)
    if tabela.empty or coluna_grupo not in tabela.columns:
        return pd.DataFrame()

    tabela = tabela.dropna(subset=[coluna_grupo])
    if tabela.empty:
        return pd.DataFrame()

    pivot = tabela.pivot_table(
        index=coluna_grupo, columns="Classificação", values="Técnico", aggfunc="count", fill_value=0
    )
    for faixa in FAIXAS_P:
        if faixa not in pivot.columns:
            pivot[faixa] = 0
    pivot = pivot[FAIXAS_P].sort_index()

    total = pivot.sum(numeric_only=True)
    total.name = "TOTAL"
    pivot = pd.concat([pivot, total.to_frame().T])
    pivot.index.name = coluna_grupo

    return pivot.reset_index()


# ------------------------------------------------------------------
# ANÁLISE P DETALHADA POR CLUSTER — P0..P5 / P≥6, com contagem e
# percentual por cluster (réplica da tabela "Contagem por Cluster" /
# "Percentual por Cluster" do site de referência).
# ------------------------------------------------------------------

FAIXAS_P_DETALHADO = ["P0", "P1", "P2", "P3", "P4", "P5", "P≥6"]


def _classificar_detalhado(qtd: int) -> str:
    if qtd <= 0:
        return "P0"
    if qtd >= 6:
        return "P≥6"
    return f"P{qtd}"


def classificacao_tecnicos_detalhada(df: pd.DataFrame, coluna_tecnico: str = "Técnico") -> pd.DataFrame:
    """Mesma ideia de `classificacao_tecnicos`, mas com faixas P0..P5/P≥6."""
    concl = concluidas_por_tecnico(df, coluna_tecnico)
    if concl.empty:
        return pd.DataFrame()

    colunas_extra = [c for c in ["Coordenador", "Supervisor", "Cluster", "Lado"] if c in df.columns]
    mapa = (
        df.dropna(subset=[coluna_tecnico])
        .drop_duplicates(subset=[coluna_tecnico])
        .set_index(coluna_tecnico)[colunas_extra]
    )

    tabela = pd.DataFrame({coluna_tecnico: concl.index, "Concluídas": concl.values}).set_index(coluna_tecnico)
    tabela = tabela.join(mapa, how="left")
    tabela["Classificação"] = tabela["Concluídas"].apply(_classificar_detalhado)
    return tabela.reset_index()


def matriz_analise_p_cluster(df: pd.DataFrame, coluna_grupo: str = "Cluster", coluna_tecnico: str = "Técnico"):
    """
    Retorna duas tabelas (contagem, percentual) com as faixas P0..P5/P≥6
    agrupadas por `coluna_grupo`, mais uma linha "Total Geral". O
    percentual é calculado em relação ao total de técnicos de cada linha
    (cluster), igual ao site de referência (Power BI).
    """
    tabela = classificacao_tecnicos_detalhada(df, coluna_tecnico)
    if tabela.empty or coluna_grupo not in tabela.columns:
        return pd.DataFrame(), pd.DataFrame()

    tabela = tabela.dropna(subset=[coluna_grupo])
    if tabela.empty:
        return pd.DataFrame(), pd.DataFrame()

    pivot = tabela.pivot_table(
        index=coluna_grupo, columns="Classificação", values=coluna_tecnico, aggfunc="count", fill_value=0
    )
    for faixa in FAIXAS_P_DETALHADO:
        if faixa not in pivot.columns:
            pivot[faixa] = 0
    pivot = pivot[FAIXAS_P_DETALHADO].sort_index()
    pivot["TOTAL"] = pivot[FAIXAS_P_DETALHADO].sum(axis=1)

    total_geral = pivot.sum(numeric_only=True)
    total_geral.name = "Total Geral"
    contagem = pd.concat([pivot, total_geral.to_frame().T])
    contagem.index.name = coluna_grupo
    contagem = contagem.astype(int)

    percentual = contagem[FAIXAS_P_DETALHADO].div(contagem["TOTAL"].replace(0, pd.NA), axis=0) * 100
    percentual = percentual.fillna(0).round(1)
    percentual.index.name = coluna_grupo

    return contagem.reset_index(), percentual.reset_index()
