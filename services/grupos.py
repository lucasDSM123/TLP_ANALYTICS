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
        eficacia_caixa = ind.eficacia_caixa()
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
                "Eficácia": eficacia_caixa,
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


def _parse_datas(df: pd.DataFrame, coluna_data: str = "Data") -> pd.DataFrame:
    """Anexa a coluna auxiliar '_data' (datetime) a partir da coluna de texto 'Data' (dd/mm/aa)."""
    serie = df.copy()
    datas = pd.to_datetime(serie[coluna_data], format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie[coluna_data], dayfirst=True, errors="coerce")
    serie["_data"] = datas
    return serie.dropna(subset=["_data"])


def _linha_indicadores_dia(sub: pd.DataFrame) -> dict:
    """Calcula Concluída (OK), Improdutiva (NOK), Técnicos (HC Ativo), Atribuição, PU e Eficácia
    para um recorte (dia/estado) já filtrado, reaproveitando a classe Indicadores — igual ao
    PAINEL de fechamento mensal usado no Excel/Power BI (Eficácia %, Concluída, Improdutiva,
    Técnicos, Atribuição, PU vs Meta).

    Inclui também 'Caixa Total' (não exibida nas tabelas) — usada apenas como base para
    recalcular corretamente a linha de Total/Total Mês (ver `_linha_resumo_soma`)."""
    ind = Indicadores(sub)
    hc = ind.hc_real()
    concluido = ind.concluido()
    eficacia = ind.eficacia()
    pu = ind.pu()
    media = ind.media_atribuicao()
    caixa = ind.caixa_total()
    return {
        "Concluída": concluido["OK"],
        "Improdutiva": concluido["NOK"],
        "Técnicos": hc["HC"],
        "Caixa Total": caixa["TOTAL"],
        "Atribuição": media["GERAL"],
        "PU": pu["GERAL"],
        "Eficácia": eficacia["GERAL"],
    }


def _linha_resumo_soma(nome_linha: str, coluna_nome: str, sub_diario: pd.DataFrame) -> dict:
    """
    Constrói a linha de total (Total Mês / Total por Estado / Total Geral)
    SOMANDO os valores diários já calculados — NUNCA recalculando PU/Atribuição
    direto sobre o período inteiro (isso contaria Técnicos como únicos do mês
    inteiro, um número bem menor que a soma dos técnicos de cada dia).

    Regra (conforme o PAINEL do Excel/Power BI):
    - Técnicos (Total)   = soma dos Técnicos de cada dia
    - Concluída (Total)  = soma da Concluída de cada dia
    - Improdutiva (Total)= soma da Improdutiva de cada dia
    - PU (Total)         = Total Concluída / Total Técnicos
    - Atribuição (Total) = Total Caixa Total / Total Técnicos
    - Eficácia (Total)   = Total Concluída / (Total Concluída + Total Improdutiva)
    """
    concluida = int(sub_diario["Concluída"].sum())
    improdutiva = int(sub_diario["Improdutiva"].sum())
    tecnicos = int(sub_diario["Técnicos"].sum())
    caixa_total = float(sub_diario["Caixa Total"].sum())

    pu_total = 0.0 if tecnicos == 0 else round(concluida / tecnicos, 2)
    atribuicao_total = 0.0 if tecnicos == 0 else round(caixa_total / tecnicos, 2)
    base_eficacia = concluida + improdutiva
    eficacia_total = 1.0 if base_eficacia == 0 else concluida / base_eficacia

    return {
        coluna_nome: nome_linha,
        "Concluída": concluida,
        "Improdutiva": improdutiva,
        "Técnicos": tecnicos,
        "Atribuição": atribuicao_total,
        "PU": pu_total,
        "Eficácia": eficacia_total,
    }


def resumo_mes_total(df: pd.DataFrame, coluna_data: str = "Data") -> dict:
    """
    Totais acumulados do mês (todo o período filtrado), SEM quebrar por
    Estado/Cluster — mesma regra de `resumo_mes_por_grupo`/`_linha_resumo_soma`
    (soma os Técnicos, a Concluída e a Caixa Total de CADA DIA e só então
    divide, em vez de recalcular PU/Atribuição direto sobre o período
    inteiro). Usada pelos cards de resumo geral no topo da página Acumulado
    Mês, para que o PU/Atribuição mostrados ali batam com o Total das
    tabelas mais abaixo.

    Retorna um dict só com a linha de total (chaves: Concluída, Improdutiva,
    Técnicos, Atribuição, PU, Eficácia), ou None se não houver dados.
    """
    if df.empty or coluna_data not in df.columns:
        return None

    serie = _parse_datas(df, coluna_data)
    if serie.empty:
        return None

    linhas = []
    for dia in sorted(serie["_data"].dt.date.unique()):
        sub_dia = serie[serie["_data"].dt.date == dia]
        linha = {"Data": dia}
        linha.update(_linha_indicadores_dia(sub_dia))
        linhas.append(linha)

    diario = pd.DataFrame(linhas)
    if diario.empty:
        return None

    return _linha_resumo_soma("Total", "Data", diario)


def serie_diaria_por_grupo(df: pd.DataFrame, coluna_grupo: str = "Estado", coluna_data: str = "Data") -> pd.DataFrame:
    """
    Réplica do PAINEL de fechamento mensal (Excel/Power BI): para cada valor
    de `coluna_grupo` (Estado, Cluster etc.) e cada dia do período filtrado,
    calcula Concluída, Improdutiva, Técnicos (HC Ativo), Atribuição, PU e
    Eficácia — recalculando a classe Indicadores em cada recorte para
    garantir que os números batam com os cards do site.

    Retorna colunas: <coluna_grupo>, Data, Concluída, Improdutiva, Técnicos,
    Caixa Total, Atribuição, PU, Eficácia.
    """
    if df.empty or coluna_data not in df.columns or coluna_grupo not in df.columns:
        return pd.DataFrame()

    serie = _parse_datas(df, coluna_data)
    if serie.empty:
        return pd.DataFrame()

    linhas = []
    for grupo in sorted(serie[coluna_grupo].dropna().unique()):
        sub_grupo = serie[serie[coluna_grupo] == grupo]
        for dia in sorted(sub_grupo["_data"].dt.date.unique()):
            sub_dia = sub_grupo[sub_grupo["_data"].dt.date == dia]
            linha = {coluna_grupo: grupo, "Data": dia}
            linha.update(_linha_indicadores_dia(sub_dia))
            linhas.append(linha)

    return pd.DataFrame(linhas)


def resumo_mes_por_grupo(df: pd.DataFrame, coluna_grupo: str = "Estado") -> pd.DataFrame:
    """
    Totais acumulados do mês (todo o período filtrado) por `coluna_grupo`
    (Estado, Cluster etc.), mais uma linha 'Total' com o consolidado geral.

    IMPORTANTE: PU e Atribuição do Total NÃO são recalculados direto sobre o
    período inteiro (isso contaria Técnicos como únicos do mês inteiro — um
    número bem menor que o real). Em vez disso, somamos os Técnicos, a
    Concluída e a Caixa Total de CADA DIA (via serie_diaria_por_grupo) e só
    então dividimos — exatamente como o PAINEL do Excel/Power BI:

        PU (Total) = soma(Concluída de cada dia) / soma(Técnicos de cada dia)
        Atribuição (Total) = soma(Caixa Total de cada dia) / soma(Técnicos de cada dia)
    """
    if df.empty or coluna_grupo not in df.columns:
        return pd.DataFrame()

    diario = serie_diaria_por_grupo(df, coluna_grupo)
    if diario.empty:
        return pd.DataFrame()

    linhas = []
    for grupo in sorted(diario[coluna_grupo].dropna().unique()):
        sub = diario[diario[coluna_grupo] == grupo]
        if sub.empty:
            continue
        linhas.append(_linha_resumo_soma(grupo, coluna_grupo, sub))

    if not linhas:
        return pd.DataFrame()

    linhas.append(_linha_resumo_soma("Total", coluna_grupo, diario))

    return pd.DataFrame(linhas)


def serie_diaria_por_estado(df: pd.DataFrame, coluna_data: str = "Data") -> pd.DataFrame:
    """Atalho de `serie_diaria_por_grupo` agrupando por Estado (SC/RS)."""
    return serie_diaria_por_grupo(df, "Estado", coluna_data)


def resumo_mes_por_estado(df: pd.DataFrame) -> pd.DataFrame:
    """Atalho de `resumo_mes_por_grupo` agrupando por Estado (SC/RS)."""
    return resumo_mes_por_grupo(df, "Estado")


def serie_diaria_por_cluster(df: pd.DataFrame, coluna_data: str = "Data") -> pd.DataFrame:
    """Atalho de `serie_diaria_por_grupo` agrupando por Cluster."""
    return serie_diaria_por_grupo(df, "Cluster", coluna_data)


def resumo_mes_por_cluster(df: pd.DataFrame) -> pd.DataFrame:
    """Atalho de `resumo_mes_por_grupo` agrupando por Cluster."""
    return resumo_mes_por_grupo(df, "Cluster")


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

        # EFICÁCIA da matriz = OK / Caixa Total, sempre no mesmo contexto
        # (segmentado por 'Lado') já usado por Caixa Tot/OK/NOK acima na
        # mesma linha — Média Atrib. e Proj. PU continuam segmentadas por
        # 'BA-TT-Real' (sub_batt), que é outra coluna.
        eficacia = ind_lado.eficacia_caixa()

        if not sub_batt.empty:
            ind_batt = Indicadores(sub_batt)
            media = ind_batt.media_atribuicao_batt(lado)
            projecao_pu = ind_batt.projecao_pu_batt(lado)
        else:
            media = 0.0
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


def matriz_producao_cluster_cidade(
    df: pd.DataFrame, lado: str, coluna_grupo: str = "Cluster", coluna_subgrupo: str = "Cidade"
) -> list[dict]:
    """
    Mesma matriz de produção de `matriz_producao` (colunas e regras de
    cálculo idênticas — segmentação por 'Lado' e 'BA-TT-Real'), mas
    destrinchada em dois níveis: Cluster -> Cidade, no formato usado pela
    tabela expansível (mesmo padrão de `services.coordenador_tabela`).

    Retorna uma lista de grupos:
    [{"cluster": str, "cidades": [linha, ...], "subtotal": linha}, ...]
    onde cada "linha" tem as mesmas chaves de `matriz_producao`
    (HC Ativo, Caixa Tot, Esteira, Bucket, Média Atrib., PU, OK, NOK,
    Iniciada, Eficácia, Proj., Proj. PU), com "Cluster" trocado por "Nome"
    (nome da cidade, ou do próprio cluster no subtotal).
    """
    if df.empty or "Lado" not in df.columns or "BA-TT-Real" not in df.columns:
        return []

    df_lado = df[df["Lado"] == lado]
    if df_lado.empty or coluna_grupo not in df_lado.columns or coluna_subgrupo not in df_lado.columns:
        return []

    def _linha(sub_lado: pd.DataFrame, sub_batt: pd.DataFrame, nome: str) -> dict:
        ind_lado = Indicadores(sub_lado)
        caixa = ind_lado.caixa_total()
        esteira = ind_lado.esteira()
        bucket = ind_lado.bucket()
        concluido = ind_lado.concluido()
        iniciada = ind_lado.iniciada()
        projecao = ind_lado.projecao()

        hc_ativo = ind_lado.hc_lado(lado)
        pu = ind_lado.pu_lado(lado)

        # EFICÁCIA da matriz = OK / Caixa Total, no mesmo contexto (Lado)
        # já usado por Caixa Tot/OK/NOK acima na mesma linha.
        eficacia = ind_lado.eficacia_caixa()

        if not sub_batt.empty:
            ind_batt = Indicadores(sub_batt)
            media = ind_batt.media_atribuicao_batt(lado)
            projecao_pu = ind_batt.projecao_pu_batt(lado)
        else:
            media = 0.0
            projecao_pu = 0.0

        return {
            "Nome": nome,
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

    grupos = []
    for cluster in sorted(df_lado[coluna_grupo].dropna().unique()):
        sub_cluster_lado = df_lado[df_lado[coluna_grupo] == cluster]
        if sub_cluster_lado.empty:
            continue

        cidades = []
        for cidade in sorted(sub_cluster_lado[coluna_subgrupo].dropna().unique()):
            sub_lado = sub_cluster_lado[sub_cluster_lado[coluna_subgrupo] == cidade]
            if sub_lado.empty:
                continue
            sub_batt = df[
                (df["BA-TT-Real"] == lado) & (df[coluna_grupo] == cluster) & (df[coluna_subgrupo] == cidade)
            ]
            cidades.append(_linha(sub_lado, sub_batt, cidade))

        if not cidades:
            continue

        sub_batt_cluster = df[(df["BA-TT-Real"] == lado) & (df[coluna_grupo] == cluster)]
        subtotal = _linha(sub_cluster_lado, sub_batt_cluster, cluster)

        grupos.append({"cluster": cluster, "cidades": cidades, "subtotal": subtotal})

    return grupos