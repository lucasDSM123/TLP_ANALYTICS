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

    colunas_extra = [c for c in ["Coordenador", "Supervisor", "Cluster", "Cidade", "Lado"] if c in df.columns]
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

    colunas_extra = [c for c in ["Coordenador", "Supervisor", "Cluster", "Cidade", "Lado"] if c in df.columns]
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


def matriz_analise_p_cluster_cidade(
    df: pd.DataFrame, coluna_grupo: str = "Cluster", coluna_subgrupo: str = "Cidade", coluna_tecnico: str = "Técnico"
) -> list[dict]:
    """
    Mesma Análise P detalhada (P0..P5/P≥6) de `matriz_analise_p_cluster`,
    mas destrinchada em dois níveis: Cluster -> Cidade, no formato usado
    pela tabela expansível (mesmo padrão de `services.coordenador_tabela`
    e `services.grupos.matriz_producao_cluster_cidade`).

    Retorna uma lista de grupos:
    [{"cluster": str, "cidades": [linha, ...], "subtotal": linha}, ...]
    onde cada "linha" é um dict com "Nome" + uma chave por faixa
    (P0..P5/P≥6) já como contagem (int) e uma chave "TOTAL" com a soma —
    o percentual de cada faixa é calculado na hora de renderizar (valor /
    TOTAL da própria linha).
    """
    tabela = classificacao_tecnicos_detalhada(df, coluna_tecnico)
    if tabela.empty or coluna_grupo not in tabela.columns or coluna_subgrupo not in tabela.columns:
        return []

    tabela = tabela.dropna(subset=[coluna_grupo, coluna_subgrupo])
    if tabela.empty:
        return []

    def _linha(sub: pd.DataFrame, nome: str) -> dict:
        contagens = sub["Classificação"].value_counts()
        linha = {"Nome": nome}
        for faixa in FAIXAS_P_DETALHADO:
            linha[faixa] = int(contagens.get(faixa, 0))
        linha["TOTAL"] = int(sum(linha[f] for f in FAIXAS_P_DETALHADO))
        return linha

    grupos = []
    for cluster in sorted(tabela[coluna_grupo].dropna().unique()):
        sub_cluster = tabela[tabela[coluna_grupo] == cluster]
        if sub_cluster.empty:
            continue

        cidades = []
        for cidade in sorted(sub_cluster[coluna_subgrupo].dropna().unique()):
            sub_cidade = sub_cluster[sub_cluster[coluna_subgrupo] == cidade]
            if sub_cidade.empty:
                continue
            cidades.append(_linha(sub_cidade, cidade))

        if not cidades:
            continue

        subtotal = _linha(sub_cluster, cluster)
        grupos.append({"cluster": cluster, "cidades": cidades, "subtotal": subtotal})

    return grupos


def matriz_analise_p_coordenador_supervisor_tecnico(
    df: pd.DataFrame, coluna_nivel1: str = "Coordenador", coluna_nivel2: str = "Supervisor",
    coluna_tecnico: str = "Técnico",
) -> list[dict]:
    """
    Mesma Análise P detalhada (P0..P5/P≥6) de `matriz_analise_p_cluster`,
    mas destrinchada em TRÊS níveis: Coordenador -> Supervisor -> Técnico
    (o Técnico é o nível folha — cada um aparece com "1" na sua própria
    faixa e "0" nas demais, já que cada técnico tem só uma classificação).

    Retorna uma lista de grupos:
    [{"nome": coordenador, "subtotal": linha, "supervisores": [
        {"nome": supervisor, "subtotal": linha, "tecnicos": [linha, ...]},
        ...
    ]}, ...]
    onde cada "linha" é um dict com "Nome" + uma chave por faixa
    (P0..P5/P≥6, já como contagem) e uma chave "TOTAL" com a soma.
    """
    tabela = classificacao_tecnicos_detalhada(df, coluna_tecnico)
    if tabela.empty or coluna_nivel1 not in tabela.columns or coluna_nivel2 not in tabela.columns:
        return []

    tabela = tabela.dropna(subset=[coluna_nivel1, coluna_nivel2])
    if tabela.empty:
        return []

    def _linha(sub: pd.DataFrame, nome: str) -> dict:
        contagens = sub["Classificação"].value_counts()
        linha = {"Nome": nome}
        for faixa in FAIXAS_P_DETALHADO:
            linha[faixa] = int(contagens.get(faixa, 0))
        linha["TOTAL"] = int(sum(linha[f] for f in FAIXAS_P_DETALHADO))
        return linha

    grupos = []
    for coord in sorted(tabela[coluna_nivel1].dropna().unique()):
        sub_coord = tabela[tabela[coluna_nivel1] == coord]
        if sub_coord.empty:
            continue

        supervisores = []
        for sup in sorted(sub_coord[coluna_nivel2].dropna().unique()):
            sub_sup = sub_coord[sub_coord[coluna_nivel2] == sup]
            if sub_sup.empty:
                continue

            tecnicos = []
            for _, row in sub_sup.sort_values(coluna_tecnico).iterrows():
                linha_tec = {"Nome": row[coluna_tecnico]}
                for faixa in FAIXAS_P_DETALHADO:
                    linha_tec[faixa] = 1 if row["Classificação"] == faixa else 0
                linha_tec["TOTAL"] = 1
                tecnicos.append(linha_tec)

            subtotal_sup = _linha(sub_sup, sup)
            supervisores.append({"nome": sup, "subtotal": subtotal_sup, "tecnicos": tecnicos})

        if not supervisores:
            continue

        subtotal_coord = _linha(sub_coord, coord)
        grupos.append({"nome": coord, "subtotal": subtotal_coord, "supervisores": supervisores})

    return grupos