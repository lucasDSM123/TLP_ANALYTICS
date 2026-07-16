import pandas as pd

from services.indicadores import Indicadores


def metricas_por_grupo(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """
    Calcula os principais indicadores (HC, Caixa, Concluído, Eficácia, PU, Esteira,
    Projeção, Iniciada) para cada valor único de `coluna`, reaproveitando a mesma
    lógica de negócio usada na Dashboard (classe Indicadores) — garante que os
    números batam com os cards da visão geral.
    """
    if df.empty or coluna not in df.columns:
        return pd.DataFrame()

    linhas = []
    for valor in sorted(df[coluna].dropna().unique()):
        sub = df[df[coluna] == valor]
        if sub.empty:
            continue

        ind = Indicadores(sub)
        hc = ind.hc_real()
        caixa = ind.caixa_total()
        concluido = ind.concluido()
        eficacia = ind.eficacia()
        pu = ind.pu()
        media = ind.media_atribuicao()
        esteira = ind.esteira()
        projecao = ind.projecao()
        iniciada = ind.iniciada()

        linhas.append(
            {
                coluna: valor,
                "HC Ativo": hc["HC"],
                "Caixa Total": caixa["TOTAL"],
                "Concluído OK": concluido["OK"],
                "Concluído NOK": concluido["NOK"],
                "Eficácia": eficacia["GERAL"],
                "PU": pu["GERAL"],
                "Média Atribuída": media["GERAL"],
                "Esteira": esteira["TOTAL"],
                "Iniciada": iniciada["TOTAL"],
                "Projeção": projecao["GERAL"],
            }
        )

    return pd.DataFrame(linhas)


def serie_diaria_indicadores(df: pd.DataFrame, coluna_data: str = "Data") -> pd.DataFrame:
    """
    Série dia a dia com Atividades (contagem bruta), Caixa Total, PU,
    Atribuição (Média Atribuição) e Eficácia — recalculando os indicadores
    de negócio (classe Indicadores) para cada dia individualmente, para
    garantir que os números batam com os cards do dashboard.

    Usada pelos gráficos "Produção Diária" (Atividades + PU) e
    "Atribuição x PU" (réplica do gráfico do Excel/Power BI).
    """
    if df.empty or coluna_data not in df.columns:
        return pd.DataFrame()

    serie = df.copy()
    datas = pd.to_datetime(serie[coluna_data], format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie[coluna_data], dayfirst=True, errors="coerce")
    serie["_data"] = datas
    serie = serie.dropna(subset=["_data"])
    if serie.empty:
        return pd.DataFrame()

    linhas = []
    for dia in sorted(serie["_data"].dt.date.unique()):
        sub = serie[serie["_data"].dt.date == dia]
        ind = Indicadores(sub)
        caixa = ind.caixa_total()
        pu = ind.pu()
        media = ind.media_atribuicao()
        eficacia = ind.eficacia()
        linhas.append(
            {
                "Data": dia,
                "Atividades": int(len(sub)),
                "Caixa Total": caixa["TOTAL"],
                "PU": pu["GERAL"],
                "Atribuição": media["GERAL"],
                "Eficácia": eficacia["GERAL"],
            }
        )

    return pd.DataFrame(linhas)


def metricas_por_tecnico(df: pd.DataFrame) -> pd.DataFrame:
    """
    Matriz "Técnico -> seus indicadores": reaproveita `metricas_por_grupo`
    (Caixa Total, Concluído OK/NOK, Eficácia, PU, Esteira, Iniciada,
    Projeção) por Técnico e anexa Coordenador/Supervisor/Cluster e a
    Classificação P (P0..>P3, réplica das medidas QTD_P0..QTD_MAIOR_P3)
    — usada na aba Supervisores quando um supervisor é selecionado, para
    mostrar todos os técnicos dele e seus indicadores numa única tabela.
    """
    # import local para evitar import circular (analise_p não importa grupos)
    from services.analise_p import classificacao_tecnicos

    base = metricas_por_grupo(df, "Técnico")
    if base.empty:
        return base

    colunas_extra = [c for c in ["Coordenador", "Supervisor", "Cluster"] if c in df.columns]
    if colunas_extra:
        extras = (
            df.dropna(subset=["Técnico"])
            .drop_duplicates(subset=["Técnico"])[["Técnico"] + colunas_extra]
        )
        base = base.merge(extras, on="Técnico", how="left")

    classif = classificacao_tecnicos(df)
    if not classif.empty:
        base = base.merge(classif[["Técnico", "Classificação"]], on="Técnico", how="left")
        base = base.rename(columns={"Classificação": "Classificação P"})

    return base


def status_counts(df: pd.DataFrame) -> dict:
    """Retorna a contagem de atividades por Status (para gráfico de rosca)."""
    if df.empty or "Status" not in df.columns:
        return {}
    return df["Status"].value_counts().to_dict()


def matriz_producao(df: pd.DataFrame, lado: str, coluna_grupo: str = "Cluster") -> pd.DataFrame:
    """
    Monta a matriz de produção (igual ao Power BI) para um lado específico
    (BA ou TT), com uma linha por Cluster e uma linha de Total no final.

    Colunas: HC Ativo, Caixa Tot, Esteira, Bucket, Média Atrib., PU, OK, NOK,
    Iniciada, Eficácia, Proj., Proj. PU.

    IMPORTANTE: 'Lado' e 'BA-TT-Real' são colunas diferentes e podem divergir
    linha a linha na base. Caixa/Esteira/Bucket/Iniciada/OK/NOK/Proj. são
    segmentados por 'Lado' (igual aos cards de HC/Caixa/Esteira/Iniciada no
    topo da Dashboard). Já PU, Média Atrib., Eficácia e Proj. PU são
    segmentados por 'BA-TT-Real' — igual aos cards "PU BA"/"PU TT"/
    "Média Atrib." no comparativo BA vs TT. Misturar as duas colunas é o que
    fazia os números da matriz não baterem com os cards.
    """
    if df.empty or "Lado" not in df.columns or "BA-TT-Real" not in df.columns:
        return pd.DataFrame()

    df_lado = df[df["Lado"] == lado]
    if df_lado.empty or coluna_grupo not in df_lado.columns:
        return pd.DataFrame()

    def _linha(sub_lado: pd.DataFrame, sub_batt: pd.DataFrame, nome: str) -> dict:
        ind_lado = Indicadores(sub_lado)
        caixa = ind_lado.caixa_total()
        esteira = ind_lado.esteira()
        bucket = ind_lado.bucket()
        concluido = ind_lado.concluido()
        iniciada = ind_lado.iniciada()
        projecao = ind_lado.projecao()

        # HC ATIVO / PU da MATRIZ: confirmado célula a célula contra o Power
        # BI que usa o filtro 'Lado' (o mesmo já usado por Caixa/OK/NOK) e
        # SÓ o lado correspondente do cálculo (BA_REAL ou TT_REAL, nunca a
        # soma dos dois) — diferente da fórmula dos cards do topo, que
        # segmenta por 'BA-TT-Real' e soma BA_REAL+TT_REAL (hc_real_batt).
        hc_ativo = ind_lado.hc_lado(lado)
        pu = ind_lado.pu_lado(lado)

        if not sub_batt.empty:
            # Média Atrib., Eficácia e Proj. PU continuam segmentadas por
            # 'BA-TT-Real' (formulação antiga) — AINDA NÃO confirmadas
            # célula a célula contra o BI como o PU/HC Ativo acima. Se
            # também estiverem divergindo na matriz, precisamos do mesmo
            # tipo de comparação (prints do BI) pra essas três colunas.
            ind_batt = Indicadores(sub_batt)
            media = ind_batt.media_atribuicao_batt(lado)
            eficacia = ind_batt.eficacia_batt(lado)
            projecao_pu = ind_batt.projecao_pu_batt(lado)
        else:
            media = 0.0
            eficacia = 1.0
            projecao_pu = 0.0

        return {
            "Cluster": nome,
            "HC Ativo": hc_ativo,
            "Caixa Tot": caixa["TOTAL"],
            "Esteira": esteira["TOTAL"],
            "Bucket": bucket["TOTAL"],
            "Média Atrib.": media,
            "PU": pu,
            "OK": concluido["OK"],
            "NOK": concluido["NOK"],
            "Iniciada": iniciada["TOTAL"],
            "Eficácia": eficacia,
            "Proj.": projecao["GERAL"],
            "Proj. PU": projecao_pu,
        }

    linhas = []
    for cluster in sorted(df_lado[coluna_grupo].dropna().unique()):
        sub_lado = df_lado[df_lado[coluna_grupo] == cluster]
        if sub_lado.empty:
            continue
        sub_batt = df[(df["BA-TT-Real"] == lado) & (df[coluna_grupo] == cluster)]
        linhas.append(_linha(sub_lado, sub_batt, cluster))

    if not linhas:
        return pd.DataFrame()

    sub_batt_total = df[df["BA-TT-Real"] == lado]
    linhas.append(_linha(df_lado, sub_batt_total, "Total"))

    return pd.DataFrame(linhas)