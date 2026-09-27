"""
services/analitica.py
======================
Lógica de negócio da aba "Analítica" — a camada que responde às perguntas
que os indicadores de produção (HC, Caixa, PU, Eficácia...) não respondem
sozinhos:

    • Por que uma OS não fecha? (causas de Não Conclusão / Cancelamento)
    • Onde a operação demora mais? (tempo real de execução em campo)
    • Quem retrabalha? (reincidência de defeito)
    • Quem está performando bem ou mal — Técnico, Supervisor, Coordenador —
      considerando TUDO isso junto (Score de Performance)

Tudo aqui recebe o `df` já filtrado pelos filtros do topo do site (mesmo
padrão de `services/grupos.py` e `services/indicadores.py`), então qualquer
segmentação escolhida pelo usuário (data, cidade, cluster etc.) se propaga
automaticamente pra essas análises.
"""
import pandas as pd

from services.grupos import metricas_por_grupo
from services.chegada import calcular_indicador_chegada, resumo_por_grupo as _resumo_chegada_por_grupo, \
    ranking_ofensores as _ranking_ofensores_chegada

# ------------------------------------------------------------------
# Colunas de causa por status — cada Status usa a coluna mais granular
# que vem SEMPRE preenchida pra aquele status na base tratada:
#   • Não Concluída -> "Causa R1" (100% preenchida quando Status é essa)
#   • Cancelada     -> "PENDENCIA" (mais granular que "CAUSA" p/ cancelamento)
# ------------------------------------------------------------------
COLUNA_CAUSA_POR_STATUS = {
    "Não Concluída": "Causa R1",
    "Cancelada": "PENDENCIA",
}

# ------------------------------------------------------------------
# Classificação heurística da natureza da causa — só pra dar uma leitura
# rápida de "quanto é fora do nosso controle x quanto é da operação".
# Baseada em palavras-chave; qualquer causa que não bater com nenhuma das
# duas listas cai em "Outros/Indefinido". É uma visão aproximada, não uma
# verdade absoluta — pensada como ponto de partida pra discussão, não como
# número fechado.
# ------------------------------------------------------------------
_PALAVRAS_EXTERNA = [
    "CLIENTE", "CASA FECHADA", "CHUVA", "ACESSO PROIBIDO", "ENDERECO",
    "ENDEREÇO", "TUBULACAO INTERNA", "TUBULAÇÃO INTERNA", "ARREPENDIMENTO",
    "CONCORRENCIA", "CONCORRÊNCIA", "DUPLICIDADE NA VENDA",
]
_PALAVRAS_OPERACIONAL = [
    "TECNICA", "TÉCNICA", "A CONTINUAR", "REDE EXTERNA", "REDE INTERNA",
    "SOBRA DE ESTEIRA", "RETENCAO", "RETENÇÃO", "TRATAMENTO DE SOBRAS",
    "CABEAMENTO PREDIAL", "ESPECIALIZADO", "SISTEMAS",
]


def classificar_natureza_causa(causa: str) -> str:
    """Classifica uma causa como 'Externa' (fora do controle da operação),
    'Operacional' (rede/técnica/gestão) ou 'Outros/Indefinido'."""
    if not isinstance(causa, str) or not causa.strip():
        return "Outros/Indefinido"
    texto = causa.upper()
    if any(p in texto for p in _PALAVRAS_EXTERNA):
        return "Externa"
    if any(p in texto for p in _PALAVRAS_OPERACIONAL):
        return "Operacional"
    return "Outros/Indefinido"


# ------------------------------------------------------------------
# PARETO DE CAUSAS
# ------------------------------------------------------------------

def pareto_causas(df: pd.DataFrame, status: str, top_n: int = 12) -> pd.DataFrame:
    """Pareto (Qtd, %, % Acumulado) das causas de um Status específico
    (usa a coluna de causa mapeada em COLUNA_CAUSA_POR_STATUS)."""
    coluna_causa = COLUNA_CAUSA_POR_STATUS.get(status, "CAUSA")
    if df.empty or "Status" not in df.columns or coluna_causa not in df.columns:
        return pd.DataFrame(columns=["Causa", "Qtd", "%", "% Acumulado"])

    sub = df.loc[df["Status"] == status, coluna_causa].dropna()
    if sub.empty:
        return pd.DataFrame(columns=["Causa", "Qtd", "%", "% Acumulado"])

    contagem = sub.value_counts()
    total = contagem.sum()
    tabela = contagem.reset_index()
    tabela.columns = ["Causa", "Qtd"]
    tabela["%"] = (tabela["Qtd"] / total * 100).round(1)
    tabela["% Acumulado"] = tabela["%"].cumsum().round(1)
    tabela["Natureza"] = tabela["Causa"].apply(classificar_natureza_causa)
    return tabela.head(top_n).reset_index(drop=True)


def resumo_natureza_causa(df: pd.DataFrame, status: str) -> pd.DataFrame:
    """Quanto do total de um Status é Externa x Operacional x Outros —
    visão resumida pra cards/gráfico de pizza."""
    coluna_causa = COLUNA_CAUSA_POR_STATUS.get(status, "CAUSA")
    if df.empty or coluna_causa not in df.columns:
        return pd.DataFrame(columns=["Natureza", "Qtd", "%"])

    sub = df.loc[df["Status"] == status, coluna_causa].dropna()
    if sub.empty:
        return pd.DataFrame(columns=["Natureza", "Qtd", "%"])

    natureza = sub.apply(classificar_natureza_causa)
    contagem = natureza.value_counts()
    total = contagem.sum()
    tabela = contagem.reset_index()
    tabela.columns = ["Natureza", "Qtd"]
    tabela["%"] = (tabela["Qtd"] / total * 100).round(1)
    return tabela


def causa_principal_por_grupo(df: pd.DataFrame, status: str, coluna_grupo: str,
                               top_n_causas: int = 6) -> pd.DataFrame:
    """Para cada valor de `coluna_grupo` (Coordenador, Supervisor, Cidade...),
    mostra quantas OS teve em cada uma das top-N causas mais frequentes do
    Status escolhido, mais o total e qual é a causa nº1 daquele grupo —
    ajuda a enxergar se a causa é 'geral da operação' ou concentrada nalgum
    time específico."""
    coluna_causa = COLUNA_CAUSA_POR_STATUS.get(status, "CAUSA")
    if df.empty or coluna_causa not in df.columns or coluna_grupo not in df.columns:
        return pd.DataFrame()

    sub = df.loc[df["Status"] == status].dropna(subset=[coluna_causa, coluna_grupo])
    if sub.empty:
        return pd.DataFrame()

    top_causas = sub[coluna_causa].value_counts().head(top_n_causas).index.tolist()
    sub_top = sub[sub[coluna_causa].isin(top_causas)]

    pivot = pd.crosstab(sub_top[coluna_grupo], sub_top[coluna_causa])
    for c in top_causas:
        if c not in pivot.columns:
            pivot[c] = 0
    pivot = pivot[top_causas]

    pivot["Total"] = pivot.sum(axis=1)
    pivot["Causa Principal"] = pivot[top_causas].idxmax(axis=1)
    pivot = pivot.sort_values("Total", ascending=False).reset_index()
    return pivot


def matriz_heatmap_causa(df: pd.DataFrame, status: str, coluna_grupo: str,
                          top_n_causas: int = 8, top_n_grupos: int = 12) -> pd.DataFrame:
    """Matriz Grupo x Causa (contagem) pronta pra plotar como heatmap —
    já recortada nos top grupos/causas pra não virar ilegível."""
    coluna_causa = COLUNA_CAUSA_POR_STATUS.get(status, "CAUSA")
    if df.empty or coluna_causa not in df.columns or coluna_grupo not in df.columns:
        return pd.DataFrame()

    sub = df.loc[df["Status"] == status].dropna(subset=[coluna_causa, coluna_grupo])
    if sub.empty:
        return pd.DataFrame()

    top_causas = sub[coluna_causa].value_counts().head(top_n_causas).index.tolist()
    top_grupos = sub[coluna_grupo].value_counts().head(top_n_grupos).index.tolist()
    sub = sub[sub[coluna_causa].isin(top_causas) & sub[coluna_grupo].isin(top_grupos)]
    if sub.empty:
        return pd.DataFrame()

    pivot = pd.crosstab(sub[coluna_grupo], sub[coluna_causa])
    pivot = pivot.reindex(index=top_grupos, columns=top_causas, fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    return pivot


# ------------------------------------------------------------------
# TEMPO DE EXECUÇÃO (duração real em campo: Término - Início)
# ------------------------------------------------------------------

def _minutos_desde_meia_noite(hora_str) -> float:
    try:
        partes = str(hora_str).split(":")
        h, m = int(partes[0]), int(partes[1])
        return h * 60 + m
    except (ValueError, IndexError, TypeError):
        return float("nan")


def formatar_minutos(minutos) -> str:
    """Formata minutos como 'Xh Ymin' (ou só 'Ymin' se < 1h)."""
    if minutos is None or pd.isna(minutos):
        return "—"
    minutos = round(float(minutos))
    h, m = divmod(minutos, 60)
    return f"{h}h {m:02d}min" if h else f"{m}min"


def base_com_duracao(df: pd.DataFrame, limite_horas: int = 12) -> pd.DataFrame:
    """Retorna só as OS Concluídas com Início/Término válidos, com a coluna
    auxiliar '_duracao_min' (Término - Início, em minutos). Descarta OS com
    duração negativa não recuperável ou acima de `limite_horas` (provável
    erro de digitação de horário, não atendimento real)."""
    se_ausentes = [c for c in ("Status", "Início", "Término") if c not in df.columns]
    if df.empty or se_ausentes:
        return pd.DataFrame()

    sub = df[df["Status"] == "Concluída"].copy()
    if sub.empty:
        return sub

    ini = sub["Início"].apply(_minutos_desde_meia_noite)
    fim = sub["Término"].apply(_minutos_desde_meia_noite)
    dur = fim - ini
    dur = dur.where(dur >= 0, dur + 24 * 60)  # atendimento que virou a meia-noite

    sub["_duracao_min"] = dur
    sub = sub[sub["_duracao_min"].notna() & (sub["_duracao_min"] <= limite_horas * 60)]
    return sub


def resumo_duracao_geral(df: pd.DataFrame) -> dict:
    """Duração média/mediana geral (todas as OS concluídas do recorte)."""
    sub = base_com_duracao(df)
    if sub.empty:
        return {"media_min": None, "mediana_min": None, "total": 0}
    return {
        "media_min": sub["_duracao_min"].mean(),
        "mediana_min": sub["_duracao_min"].median(),
        "total": int(sub.shape[0]),
    }


def duracao_por_grupo(df: pd.DataFrame, coluna_grupo: str, min_amostras: int = 3) -> pd.DataFrame:
    """Duração média/mediana de execução por grupo (Tipo de Atividade,
    Cidade, Cluster, Supervisor, Coordenador...), descartando grupos com
    poucas amostras (estatística pouco confiável)."""
    sub = base_com_duracao(df)
    if sub.empty or coluna_grupo not in sub.columns:
        return pd.DataFrame()

    g = sub.groupby(coluna_grupo)["_duracao_min"].agg(["mean", "median", "count"])
    g = g[g["count"] >= min_amostras].reset_index()
    g.columns = [coluna_grupo, "Duração Média (min)", "Duração Mediana (min)", "Qtd Amostras"]
    g["Duração Média (min)"] = g["Duração Média (min)"].round(1)
    g["Duração Mediana (min)"] = g["Duração Mediana (min)"].round(1)
    return g.sort_values("Duração Média (min)", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------
# REINCIDÊNCIA / RETRABALHO
# ------------------------------------------------------------------

def reincidencia_por_grupo(df: pd.DataFrame, coluna_grupo: str) -> pd.DataFrame:
    """% de OS com 'Defeito Repetido' > 0 por grupo — indício de retrabalho
    (o mesmo defeito voltando a acontecer no mesmo cliente/endereço)."""
    if df.empty or "Defeito Repetido" not in df.columns or coluna_grupo not in df.columns:
        return pd.DataFrame()

    sub = df.dropna(subset=[coluna_grupo]).copy()
    if sub.empty:
        return pd.DataFrame()

    sub["_reincidente"] = sub["Defeito Repetido"].fillna(0) > 0
    g = sub.groupby(coluna_grupo).agg(
        Total_OS=("_reincidente", "count"),
        Qtd_Reincidencias=("_reincidente", "sum"),
    ).reset_index()
    g["Taxa Reincidência"] = (g["Qtd_Reincidencias"] / g["Total_OS"] * 100).round(1)
    return g.rename(columns={"Total_OS": "Total OS", "Qtd_Reincidencias": "Qtd Reincidências"}) \
        .sort_values("Taxa Reincidência", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------
# PU "MÉDIO POR TÉCNICO-DIA" — correção do PU oficial do site pra uso
# nesta aba.
#
# O PU oficial (services/indicadores.py -> pu()) é OK / HC, onde o HC é
# calculado com uma fórmula pensada pra POOLS de vários técnicos (MSK/BA/TT
# com arredondamento). Quando aplicado num recorte de 1 único técnico (como
# faz metricas_por_grupo/metricas_por_tecnico), o HC quase sempre vira 1 —
# então o "PU" acaba sendo, na prática, só a CONTAGEM de OS concluídas no
# período (uma soma disfarçada), não uma taxa. Em recortes de vários dias
# isso fica bem visível (PU de 11,50 / 16,00 / 18,50...).
#
# Aqui calculamos uma média por "técnico-dia": para cada dia, quantos
# técnicos distintos atuaram naquele grupo, soma-se isso no período, e
# divide-se o total de OS Concluída do grupo por essa soma. Funciona pra
# Técnico (vira OK / dias trabalhados), Supervisor e Coordenador (vira
# OK / soma diária de técnicos ativos no time) com a mesma lógica.
# ------------------------------------------------------------------

def pu_medio_diario(df: pd.DataFrame, coluna_grupo: str) -> pd.DataFrame:
    campos_necessarios = {"Data", "Técnico", "Status", coluna_grupo}
    if df.empty or not campos_necessarios.issubset(df.columns):
        return pd.DataFrame()

    sub = df.dropna(subset=[coluna_grupo, "Data"])
    if sub.empty:
        return pd.DataFrame()

    tecnico_dia = (
        sub.groupby([coluna_grupo, "Data"])["Técnico"].nunique()
        .groupby(coluna_grupo).sum()
    )
    ok = sub.loc[sub["Status"] == "Concluída"].groupby(coluna_grupo).size()

    tabela = tecnico_dia.rename("Técnico-Dia").reset_index()
    tabela["Concluído OK"] = tabela[coluna_grupo].map(ok).fillna(0)
    tabela["PU Médio/Dia"] = (
        tabela["Concluído OK"] / tabela["Técnico-Dia"].replace(0, pd.NA)
    ).fillna(0).round(2)
    return tabela


# ------------------------------------------------------------------
# PONTUALIDADE / CHEGADA NA JANELA
# ------------------------------------------------------------------

def pontualidade_por_grupo(df: pd.DataFrame, coluna_grupo: str) -> pd.DataFrame:
    """% de OS iniciadas dentro da Janela agendada, por grupo — reaproveita
    a régua oficial da aba Chegada (services/chegada.py), então o número
    bate com o que aparece lá."""
    if df.empty or coluna_grupo not in df.columns:
        return pd.DataFrame()
    df_chegada = calcular_indicador_chegada(df)
    return _resumo_chegada_por_grupo(df_chegada, coluna_grupo)


def ranking_ofensores_pontualidade(df: pd.DataFrame, coluna_grupo: str, top_n: int = 10) -> pd.DataFrame:
    """Ranking de quem mais chegou 'Depois' da tolerância da Janela — mesma
    lógica/nome usado na aba Chegada."""
    if df.empty or coluna_grupo not in df.columns:
        return pd.DataFrame()
    df_chegada = calcular_indicador_chegada(df)
    return _ranking_ofensores_chegada(df_chegada, coluna_grupo, top_n=top_n)


# ------------------------------------------------------------------
# SCORE DE PERFORMANCE (ranking Técnico / Supervisor / Coordenador)
# ------------------------------------------------------------------

PESOS_SCORE = {
    "eficacia": 0.30,
    "pu": 0.20,
    "nao_concluida": 0.15,
    "pontualidade": 0.20,
    "reincidencia": 0.08,
    "duracao": 0.07,
}


def _normalizar(serie: pd.Series, inverso: bool = False) -> pd.Series:
    """Normaliza uma série pra 0-100 (min-max) dentro do próprio recorte.
    Quando não há variação (todo mundo igual, ou só 1 elemento), devolve um
    valor neutro (70) em vez de 0/100 artificiais."""
    serie = serie.astype(float)
    valido = serie.dropna()
    if valido.empty or valido.max() == valido.min():
        return pd.Series(70.0, index=serie.index)
    norm = (serie - valido.min()) / (valido.max() - valido.min()) * 100
    return (100 - norm) if inverso else norm


def score_performance(df: pd.DataFrame, coluna_grupo: str = "Técnico",
                       meta_pu: float = 3.0, caixa_minima: int = 5) -> pd.DataFrame:
    """
    Score de Performance (0-100) por Técnico / Supervisor / Coordenador,
    combinando os indicadores já usados no resto do site com os achados
    desta aba:

        30% Eficácia             (OK / (OK+NOK))
        20% PU médio/dia vs meta (ver pu_medio_diario — corrige a distorção
            do PU oficial, que em recorte de 1 técnico e vários dias vira
            praticamente uma soma em vez de uma taxa)
        15% % Não Concluída       (quanto menor, melhor)
        20% Pontualidade          (% de OS iniciadas dentro da Janela —
            chegar atrasado compromete a agenda do dia inteiro, por isso o
            peso alto; ver services/chegada.py)
         8% Taxa de Reincidência  (quanto menor, melhor)
         7% Duração média de execução (quanto menor, melhor — comparação
            sempre relativa ao próprio recorte, não penaliza quem tem OS
            mais rápidas por natureza do serviço)

    Grupos com menos de `caixa_minima` OS na Caixa Total ficam de fora —
    amostra pequena demais pra virar ranking (evita "melhor/pior técnico"
    com 1 ou 2 OS no período).

    Classificação final: Destaque (score >= 65) / Atenção (45-65) /
    Ofensor (< 45) — limites arbitrários, pensados só como referência
    visual rápida.
    """
    base = metricas_por_grupo(df, coluna_grupo)
    if base.empty:
        return pd.DataFrame()

    base = base[base["Caixa Total"] >= caixa_minima].copy()
    if base.empty:
        return pd.DataFrame()

    # PU médio por técnico-dia (substitui o PU oficial nesta tabela — ver
    # docstring de pu_medio_diario)
    pu_dia = pu_medio_diario(df, coluna_grupo)
    if not pu_dia.empty:
        base = base.drop(columns=["PU"], errors="ignore").merge(
            pu_dia[[coluna_grupo, "PU Médio/Dia"]], on=coluna_grupo, how="left"
        ).rename(columns={"PU Médio/Dia": "PU"})
    base["PU"] = base["PU"].fillna(0)

    # % Não Concluída sobre a Caixa Total do grupo
    if "Status" in df.columns:
        nao_concl = df.loc[df["Status"] == "Não Concluída"].groupby(coluna_grupo).size()
    else:
        nao_concl = pd.Series(dtype=int)
    base["Qtd Não Concluída"] = base[coluna_grupo].map(nao_concl).fillna(0)
    base["% Não Concluída"] = (
        base["Qtd Não Concluída"] / base["Caixa Total"].replace(0, pd.NA) * 100
    ).fillna(0).round(1)

    # Pontualidade (chegada dentro da Janela)
    pont = pontualidade_por_grupo(df, coluna_grupo)
    if not pont.empty:
        base = base.merge(pont[[coluna_grupo, "% Dentro"]], on=coluna_grupo, how="left")
    else:
        base["% Dentro"] = pd.NA
    mediana_pontualidade = base["% Dentro"].median()
    base["Pontualidade"] = base["% Dentro"].fillna(
        mediana_pontualidade if pd.notna(mediana_pontualidade) else 0
    ).round(1)
    base = base.drop(columns=["% Dentro"])

    # Reincidência
    reinc = reincidencia_por_grupo(df, coluna_grupo)
    if not reinc.empty:
        base = base.merge(reinc[[coluna_grupo, "Taxa Reincidência"]], on=coluna_grupo, how="left")
    else:
        base["Taxa Reincidência"] = pd.NA
    base["Taxa Reincidência"] = base["Taxa Reincidência"].fillna(0)

    # Duração média de execução
    dur = duracao_por_grupo(df, coluna_grupo, min_amostras=1)
    if not dur.empty:
        base = base.merge(dur[[coluna_grupo, "Duração Média (min)"]], on=coluna_grupo, how="left")
    else:
        base["Duração Média (min)"] = pd.NA

    mediana_duracao = base["Duração Média (min)"].median()
    duracao_preenchida = base["Duração Média (min)"].fillna(mediana_duracao)

    n_eficacia = base["Eficácia"].astype(float) * 100
    n_pu = (base["PU"].astype(float).clip(upper=meta_pu) / meta_pu * 100).clip(upper=100)
    n_nao_concl = _normalizar(base["% Não Concluída"], inverso=True)
    n_pontualidade = base["Pontualidade"].astype(float)
    n_reinc = _normalizar(base["Taxa Reincidência"], inverso=True)
    n_duracao = _normalizar(duracao_preenchida, inverso=True)

    base["Score"] = (
        n_eficacia * PESOS_SCORE["eficacia"]
        + n_pu * PESOS_SCORE["pu"]
        + n_nao_concl * PESOS_SCORE["nao_concluida"]
        + n_pontualidade * PESOS_SCORE["pontualidade"]
        + n_reinc * PESOS_SCORE["reincidencia"]
        + n_duracao * PESOS_SCORE["duracao"]
    ).round(1)

    base["Classificação"] = pd.cut(
        base["Score"], bins=[-1, 45, 65, 101], labels=["Ofensor", "Atenção", "Destaque"]
    ).astype(str)

    return base.sort_values("Score", ascending=False).reset_index(drop=True)
