"""
Congelamento AUTOMÁTICO do mês anterior, na virada do mês.

Como funciona
-------------
O upload (upload_dados.py) faz upsert e APAGA do Neon o que não vem no arquivo.
Então, no primeiro upload de um mês novo, o mês anterior ainda está no Neon
até o instante do envio. `congelar_virada()` roda ANTES desse envio:

  1. Olha as datas distintas que já estão no Neon e as do arquivo novo.
  2. Para cada mês no Neon MENOR que o mês mais recente do arquivo novo (e ainda
     não congelado), junta as linhas desse mês que estão no Neon com as que
     vieram no arquivo novo (o arquivo novo vence em caso de repetição pelo
     numero_atividade — cobre o "dia D-1" que chega no dia seguinte).
  3. Calcula o fechamento DIA A DIA de Estado, Cluster e Supervisor com a mesma
     regra do site (services.grupos) e grava na tabela `fechamento_congelado`.

Os totais mensais são a soma dos dias (mesma regra do site), então não precisam
ser gravados à parte.

Prioridade na leitura (ver services/historico_mensal.py): o que estiver
cadastrado À MÃO em historico_mensal.py / services/historico_diario/*.json
(números oficiais do painel) vence; esta tabela é o plano automático.

Segurança: nada aqui deve derrubar o upload — quem chama envolve em try/except.
Meses com poucos dias de dados (< MIN_DIAS) NÃO são congelados, para não
cristalizar um mês incompleto.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import bindparam, text

from services.grupos import serie_diaria_por_grupo

TABELA_CONGELADO = "fechamento_congelado"
DIMENSOES = ("Estado", "Cluster", "Supervisor")
MIN_DIAS = 20

_METRICAS = ("concluida", "improdutiva", "tecnicos", "caixa_total", "atribuicao", "pu", "eficacia")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _engine():
    from services.database import obter_engine
    return obter_engine()


def _datas(serie: pd.Series) -> pd.Series:
    """Coluna Data (texto dd/mm/aa ou datetime) -> datetime."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    datas = pd.to_datetime(serie, format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return datas


def _normalizar_data_texto(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza a coluna Data como texto dd/mm/aa (formato do Neon)."""
    df = df.copy()
    df["Data"] = _datas(df["Data"]).dt.strftime("%d/%m/%y")
    return df.dropna(subset=["Data"])


def criar_tabela(engine=None) -> None:
    engine = engine or _engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_CONGELADO} (
                ano          INTEGER      NOT NULL,
                mes          INTEGER      NOT NULL,
                nivel        VARCHAR(20)  NOT NULL,
                grupo        VARCHAR(200) NOT NULL,
                dia          INTEGER      NOT NULL,
                concluida    INTEGER,
                improdutiva  INTEGER,
                tecnicos     INTEGER,
                caixa_total  DOUBLE PRECISION,
                atribuicao   DOUBLE PRECISION,
                pu           DOUBLE PRECISION,
                eficacia     DOUBLE PRECISION,
                congelado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ano, mes, nivel, grupo, dia)
            )
        """))


def meses_congelados(engine=None) -> set[tuple[int, int]]:
    engine = engine or _engine()
    with engine.connect() as conn:
        linhas = conn.execute(text(f"SELECT DISTINCT ano, mes FROM {TABELA_CONGELADO}")).fetchall()
    return {(int(a), int(m)) for a, m in linhas}


# ---------------------------------------------------------------------------
# Congelar (chamado pelo upload, ANTES de enviar o arquivo novo)
# ---------------------------------------------------------------------------
def congelar_virada(df_novo: pd.DataFrame, engine=None, tabela_base: str = None,
                    min_dias: int = MIN_DIAS, log=print) -> list[tuple[int, int]]:
    """Congela os meses que estão no Neon e são anteriores ao mês mais recente
    do arquivo novo. Retorna a lista de (ano, mês) congelados nesta chamada."""
    import config
    from services import historico_mensal  # import tardio: evita ciclo

    engine = engine or _engine()
    tabela_base = tabela_base or config.DATABASE_TABLE

    # Mês mais recente do arquivo novo
    datas_novo = _datas(df_novo["Data"]).dropna()
    if datas_novo.empty:
        return []
    ref = datas_novo.max()
    mes_novo = (ref.year, ref.month)

    # Datas distintas já no Neon (consulta leve — não lê a tabela inteira)
    with engine.connect() as conn:
        distintas = pd.read_sql(text(f'SELECT DISTINCT "Data" FROM "{tabela_base}"'), conn)
    if distintas.empty:
        return []
    distintas["_dt"] = _datas(distintas["Data"])
    distintas = distintas.dropna(subset=["_dt"])
    distintas["_mes"] = list(zip(distintas["_dt"].dt.year, distintas["_dt"].dt.month))

    candidatos = sorted({m for m in distintas["_mes"] if m < mes_novo})
    if not candidatos:
        return []

    criar_tabela(engine)
    ja = meses_congelados(engine)
    congelados = []

    for ano, mes in candidatos:
        if (ano, mes) in ja:
            continue
        if (ano, mes) in historico_mensal._HISTORICO:
            log(f"   ↪ {mes:02d}/{ano}: já cadastrado à mão em historico_mensal.py — nada a fazer.")
            continue

        datas_txt = distintas.loc[distintas["_mes"] == (ano, mes), "Data"].tolist()
        with engine.connect() as conn:
            q = text(f'SELECT * FROM "{tabela_base}" WHERE "Data" IN :datas').bindparams(
                bindparam("datas", expanding=True))
            neon_mes = pd.read_sql(q, conn, params={"datas": datas_txt})

        novo = _normalizar_data_texto(df_novo)
        novo_dt = _datas(novo["Data"])
        novo_mes = novo[(novo_dt.dt.year == ano) & (novo_dt.dt.month == mes)]

        base = pd.concat([_normalizar_data_texto(neon_mes), novo_mes], ignore_index=True)
        if "numero_atividade" in base.columns:
            base = base.drop_duplicates(subset=["numero_atividade"], keep="last")

        dias = _datas(base["Data"]).dt.day.nunique()
        if dias < min_dias:
            log(f"   ⚠️ {mes:02d}/{ano}: só {dias} dia(s) de dados (mínimo {min_dias}) — NÃO congelado.")
            continue

        linhas = _calcular_linhas(base, ano, mes)
        _gravar(engine, ano, mes, linhas)
        congelados.append((ano, mes))
        log(f"   ❄️ {mes:02d}/{ano} congelado: {len(base)} linhas, {dias} dias, {len(linhas)} registros.")

    return congelados


def _calcular_linhas(base_mes: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    partes = []
    for nivel in DIMENSOES:
        if nivel not in base_mes.columns:
            continue
        diario = serie_diaria_por_grupo(base_mes, nivel)
        if diario.empty:
            continue
        partes.append(pd.DataFrame({
            "ano": ano, "mes": mes, "nivel": nivel,
            "grupo": diario[nivel].astype(str),
            "dia": diario["Data"].apply(lambda d: d.day).astype(int),
            "concluida": diario["Concluída"].astype(int),
            "improdutiva": diario["Improdutiva"].astype(int),
            "tecnicos": diario["Técnicos"].astype(int),
            "caixa_total": diario["Caixa Total"].astype(float).round(2),
            "atribuicao": diario["Atribuição"].astype(float).round(4),
            "pu": diario["PU"].astype(float).round(4),
            "eficacia": diario["Eficácia"].astype(float).round(6),
        }))
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _gravar(engine, ano: int, mes: int, linhas: pd.DataFrame) -> None:
    if linhas.empty:
        return
    with engine.begin() as conn:  # tudo ou nada
        conn.execute(text(f"DELETE FROM {TABELA_CONGELADO} WHERE ano = :a AND mes = :m"),
                     {"a": ano, "m": mes})
        linhas.to_sql(TABELA_CONGELADO, conn, if_exists="append", index=False,
                      method="multi", chunksize=500)


# ---------------------------------------------------------------------------
# Ler (usado por services/historico_mensal.py)
# ---------------------------------------------------------------------------
def ler_congelado(ano: int, mes: int, engine=None) -> dict | None:
    """{nivel: {grupo: DataFrame indexado por dia}} do mês congelado, ou None
    se não houver (ou se a tabela/banco não estiver disponível)."""
    try:
        engine = engine or _engine()
        cols = ", ".join(("nivel", "grupo", "dia") + _METRICAS)
        with engine.connect() as conn:
            df = pd.read_sql(
                text(f"SELECT {cols} FROM {TABELA_CONGELADO} WHERE ano = :a AND mes = :m"),
                conn, params={"a": ano, "m": mes})
    except Exception:
        return None
    if df.empty:
        return None
    renomear = {"concluida": "Concluída", "improdutiva": "Improdutiva", "tecnicos": "Técnicos",
                "caixa_total": "Caixa Total", "atribuicao": "Atribuição", "pu": "PU",
                "eficacia": "Eficácia"}
    saida: dict = {}
    for (nivel, grupo), sub in df.groupby(["nivel", "grupo"]):
        saida.setdefault(nivel, {})[grupo] = (
            sub.drop(columns=["nivel", "grupo"]).set_index("dia").sort_index().rename(columns=renomear)
        )
    return saida
