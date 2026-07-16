import pandas as pd

from services.indicadores import Indicadores
from services.grupos import metricas_por_grupo, matriz_producao

# Nomes de coluna na matriz_producao (services.grupos) que correspondem
# ao "coluna_valor" de cada indicador tipo "taxa" (os nomes divergem em
# alguns casos, ex.: "Projeção" no registro vs "Proj." na matriz).
_COLUNA_MATRIZ = {"HC Ativo": "HC Ativo", "Eficácia": "Eficácia", "PU": "PU", "Projeção": "Proj."}

# ------------------------------------------------------------------
# FAIXAS HORÁRIAS (réplica do eixo X do gráfico "EVOLUÇÃO TEMPORAL"
# do Power BI: 8:00–20:00 em blocos, + "Fora do expediente")
# ------------------------------------------------------------------
FAIXAS_LABELS = [
    "1. 8:00–9:30", "2. 9:30–10:30", "3. 10:30–11:30", "4. 11:30–12:30",
    "5. 12:30–13:30", "6. 13:30–14:30", "7. 14:30–15:30", "8. 15:30–16:30",
    "9. 16:30–17:30", "10. 17:30–18:30", "11. 18:30–19:30", "12. 19:30–20:00",
]
FORA_EXPEDIENTE = "Fora do expediente"
_BOUNDS = [480, 570, 630, 690, 750, 810, 870, 930, 990, 1050, 1110, 1170, 1200]


def _minutos(hhmm) -> int | None:
    try:
        partes = str(hhmm).split(":")
        return int(partes[0]) * 60 + int(partes[1])
    except (ValueError, AttributeError, IndexError):
        return None


def _faixa(hhmm) -> str:
    minutos = _minutos(hhmm)
    if minutos is None:
        return FORA_EXPEDIENTE
    for i in range(len(_BOUNDS) - 1):
        if _BOUNDS[i] <= minutos < _BOUNDS[i + 1]:
            return FAIXAS_LABELS[i]
    return FORA_EXPEDIENTE


# ------------------------------------------------------------------
# REGISTRO DE INDICADORES DISPONÍVEIS NA SEGMENTAÇÃO
# ------------------------------------------------------------------
# tipo "contagem": indicadores baseados em um filtro de linhas (Status,
#   Contratada, etc.) — suportam faixa horária, cluster e dia a dia.
# tipo "taxa": indicadores calculados (razões/médias) via classe
#   Indicadores — suportam cluster e dia a dia, mas não faixa horária
#   (não fazem sentido "por hora do dia").
INDICADORES = {
    "caixa_total": {
        "label": "Caixa Total", "tipo": "contagem",
        "filtro": lambda df: ~df["Status"].isin(["Suspensa", "Cancelada"]),
        "coluna_valor": "Caixa Total",
    },
    "concluido_ok": {
        "label": "Concluído OK", "tipo": "contagem",
        "filtro": lambda df: df["Status"] == "Concluída",
        "coluna_valor": "Concluído OK",
    },
    "concluido_nok": {
        "label": "Concluído NOK", "tipo": "contagem",
        "filtro": lambda df: df["Status"] == "Não Concluída",
        "coluna_valor": "Concluído NOK",
    },
    "iniciada": {
        "label": "Iniciada", "tipo": "contagem",
        "filtro": lambda df: df["Status"] == "Iniciada",
        "coluna_valor": "Iniciada",
    },
    "cancelada": {
        "label": "Cancelada", "tipo": "contagem",
        "filtro": lambda df: df["Status"] == "Cancelada",
        "coluna_valor": "Cancelada",
    },
    "suspensa": {
        "label": "Suspensa", "tipo": "contagem",
        "filtro": lambda df: df["Status"] == "Suspensa",
        "coluna_valor": "Suspensa",
    },
    "bucket": {
        "label": "Bucket", "tipo": "contagem",
        "filtro": lambda df: (df["Contratada"] == "BUCKET TLP") & (df["Status"] != "Cancelada"),
        "coluna_valor": "Bucket",
    },
    "esteira": {
        "label": "Esteira", "tipo": "contagem",
        "filtro": lambda df: df["Esteira"] == "ESTEIRA",
        "coluna_valor": "Esteira",
    },
    "hc_ativo": {"label": "HC Ativo", "tipo": "taxa", "coluna_valor": "HC Ativo"},
    "eficacia": {"label": "Eficácia", "tipo": "taxa", "coluna_valor": "Eficácia"},
    "pu": {"label": "PU", "tipo": "taxa", "coluna_valor": "PU"},
    "projecao": {"label": "Projeção", "tipo": "taxa", "coluna_valor": "Projeção"},
}


def _col_termino(df: pd.DataFrame):
    return "Término" if "Término" in df.columns else None


def serie_faixa_horaria(df: pd.DataFrame, filtro) -> pd.DataFrame:
    """Conta as linhas filtradas, distribuídas nas faixas horárias do expediente."""
    col_termino = _col_termino(df)
    ordem = FAIXAS_LABELS + [FORA_EXPEDIENTE]

    if df.empty or col_termino is None:
        return pd.DataFrame()

    sub = df[filtro(df)].copy()
    if sub.empty:
        return pd.DataFrame({"Faixa": ordem, "Quantidade": [0] * len(ordem)})

    sub["Faixa"] = sub[col_termino].apply(_faixa)
    contagem = sub["Faixa"].value_counts()
    return pd.DataFrame({"Faixa": ordem, "Quantidade": [int(contagem.get(f, 0)) for f in ordem]})


def valores_por_cluster(df: pd.DataFrame, chave: str, coluna_grupo: str = "Cluster") -> pd.DataFrame:
    """Quebra o indicador selecionado por Cluster (ou outra dimensão)."""
    meta = INDICADORES[chave]

    if df.empty or coluna_grupo not in df.columns:
        return pd.DataFrame()

    if meta["tipo"] == "contagem":
        sub = df[meta["filtro"](df)]
        if sub.empty:
            return pd.DataFrame()
        contagem = sub.groupby(coluna_grupo).size().reset_index(name=meta["coluna_valor"])
        return contagem.sort_values(meta["coluna_valor"], ascending=False)

    base = metricas_por_grupo(df, coluna_grupo)
    if base.empty or meta["coluna_valor"] not in base.columns:
        return pd.DataFrame()
    return base[[coluna_grupo, meta["coluna_valor"]]].sort_values(meta["coluna_valor"], ascending=False)


def valores_por_cluster_lado(df: pd.DataFrame, chave: str, lado: str, coluna_grupo: str = "Cluster") -> pd.DataFrame:
    """
    Quebra o indicador por Cluster, segmentado por 'Lado' (BA ou TT) —
    réplica das duas tabelas "PRODUÇÃO BA" / "PRODUÇÃO TT" do Power BI.

    Indicadores "contagem" filtram direto por Lado + o filtro do
    indicador. Indicadores "taxa" reaproveitam matriz_producao(), que já
    replica célula a célula as fórmulas do BI (HC Ativo, PU, Eficácia,
    Projeção) segmentadas por Lado.
    """
    meta = INDICADORES[chave]

    if df.empty or "Lado" not in df.columns or coluna_grupo not in df.columns:
        return pd.DataFrame()

    if meta["tipo"] == "contagem":
        sub_lado = df[df["Lado"] == lado]
        if sub_lado.empty:
            return pd.DataFrame()
        sub = sub_lado[meta["filtro"](sub_lado)]
        if sub.empty:
            return pd.DataFrame()
        contagem = sub.groupby(coluna_grupo).size().reset_index(name=meta["coluna_valor"])
        return contagem.sort_values(meta["coluna_valor"], ascending=False)

    matriz = matriz_producao(df, lado=lado, coluna_grupo=coluna_grupo)
    if matriz.empty:
        return pd.DataFrame()
    matriz = matriz[matriz[coluna_grupo] != "Total"]

    col_matriz = _COLUNA_MATRIZ.get(meta["coluna_valor"], meta["coluna_valor"])
    if col_matriz not in matriz.columns:
        return pd.DataFrame()

    resultado = matriz[[coluna_grupo, col_matriz]].rename(columns={col_matriz: meta["coluna_valor"]})
    return resultado.sort_values(meta["coluna_valor"], ascending=False)


def _valor_taxa(ind: Indicadores, chave: str):
    if chave == "hc_ativo":
        return ind.hc_real()["HC"]
    if chave == "eficacia":
        return round(ind.eficacia()["GERAL"] * 100, 1)
    if chave == "pu":
        return round(ind.pu()["GERAL"], 2)
    if chave == "projecao":
        return ind.projecao()["GERAL"]
    return 0


def serie_diaria(df: pd.DataFrame, chave: str, coluna_data: str = "Data") -> pd.DataFrame:
    """Série histórica dia a dia do indicador selecionado (comparação entre datas)."""
    if df.empty or coluna_data not in df.columns:
        return pd.DataFrame()

    meta = INDICADORES[chave]
    serie = df.copy()
    datas = pd.to_datetime(serie[coluna_data], format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie[coluna_data], dayfirst=True, errors="coerce")
    serie["_data"] = datas
    serie = serie.dropna(subset=["_data"])

    dias = sorted(serie["_data"].dt.date.unique())
    if len(dias) < 2:
        return pd.DataFrame()

    linhas = []
    for dia in dias:
        sub = serie[serie["_data"].dt.date == dia]
        if meta["tipo"] == "contagem":
            valor = int(meta["filtro"](sub).sum())
        else:
            valor = _valor_taxa(Indicadores(sub), chave)
        linhas.append({"Data": dia.strftime("%d/%m"), "Quantidade": valor})

    return pd.DataFrame(linhas)
