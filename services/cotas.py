import glob
import os
import re
import unicodedata

import pandas as pd
import streamlit as st

from services.database import ler_dados_do_neon

# Padrão de nome gerado pelo cota.py: Cota_Cidades_DD-MM-AAAA.xlsx (ou o
# arquivo fixo Cota_Cidades.xlsx). Usado como fallback caso o Neon ainda
# não tenha a tabela populada (ex.: antes do primeiro `upload_dados_cotas.py`).
COTAS_DATA_GLOB = "data/Cota_Cidades*.xlsx"
COTAS_TABELA_NEON = "cotas_cidades"
COTAS_MINUTOS_TABELA_NEON = "cotas_cidades_minutos"


def _limpar_base_cotas(df: pd.DataFrame, coluna_chave: str) -> pd.DataFrame:
    if df.empty:
        return df

    # A chave sintética criada no upload (chave_cota / chave_cota_minutos)
    # é só para o upsert no Neon — não faz parte dos dados exibidos no site.
    df = df.drop(columns=[coluna_chave], errors="ignore")

    # Remove os prefixos "Cluster - " / "Bucket - " vindos da árvore do
    # Oracle, pra exibir só o nome limpo (Blumenau, Balneario Camboriu...).
    df["Cluster"] = df["Cluster"].astype(str).str.replace("Cluster - ", "", regex=False)
    df["Cidade"] = df["Cidade"].astype(str).str.replace("Bucket - ", "", regex=False)

    for col in ("Cota", "Real", "GAP"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


@st.cache_data(show_spinner=False, ttl=600)
def carregar_base_cotas() -> pd.DataFrame:
    """
    Carrega a base de Cotas (Cluster, Cidade, Data, Segmento, Tipo de
    Serviço, Atividade, Horário, Cota, Real, GAP).

    Tenta primeiro a tabela `cotas_cidades` no Neon (alimentada pelo
    `upload_dados_cotas.py`, mesmo padrão de upload_dados.py +
    services/database.py usado pela base de produção). Se o Neon falhar ou
    a tabela ainda estiver vazia/inexistente, cai para o Excel mais recente
    em `data/` (aba "Cotas") como backup.
    """
    try:
        df = ler_dados_do_neon(COTAS_TABELA_NEON)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        arquivos = sorted(glob.glob(COTAS_DATA_GLOB), key=os.path.getmtime, reverse=True)
        if not arquivos:
            return pd.DataFrame()
        try:
            df = pd.read_excel(arquivos[0], sheet_name="Cotas")
        except Exception:
            return pd.DataFrame()

    return _limpar_base_cotas(df, coluna_chave="chave_cota")


@st.cache_data(show_spinner=False, ttl=600)
def carregar_base_cotas_minutos() -> pd.DataFrame:
    """
    Carrega a base de Cotas EM MINUTOS (mesma capacidade da base por
    Atividade, só que medida em minutos abertos/usados em vez de em número
    de atividades) — mesmo formato (Cluster, Cidade, Data, Atividade,
    Horário, Cota, Real, GAP), pra reaproveitar todas as mesmas funções de
    agregação e as mesmas tabelas de exibição já usadas no modo "Atividades".

    Tenta primeiro a tabela `cotas_cidades_minutos` no Neon (alimentada pelo
    `upload_dados_cotas_minutos.py`, a partir da aba "Todas_Cidades" do
    Excel). Se o Neon falhar ou a tabela ainda estiver vazia/inexistente,
    cai para o Excel mais recente em `data/` (aba "Todas_Cidades") como
    backup, normalizando a árvore Time Slot > Atividade da mesma forma que
    o script de upload faz.
    """
    try:
        df = ler_dados_do_neon(COTAS_MINUTOS_TABELA_NEON)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        arquivos = sorted(glob.glob(COTAS_DATA_GLOB), key=os.path.getmtime, reverse=True)
        if not arquivos:
            return pd.DataFrame()
        try:
            df_bruto = pd.read_excel(arquivos[0], sheet_name="Todas_Cidades")
            df_bruto = df_bruto.rename(columns=lambda c: c.strip())
            col_descricao = "Time slots/Categorias da capacidade"
            df_bruto[col_descricao] = df_bruto[col_descricao].astype(str).str.strip()
            eh_slot = df_bruto[col_descricao].str.match(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}$")
            df_bruto["Horário"] = df_bruto[col_descricao].where(eh_slot).ffill()
            df_bruto["Atividade"] = df_bruto[col_descricao].where(~eh_slot)
            df = df_bruto[~eh_slot].copy()
            df = df.rename(columns={"Usado(a)": "Real"})
            df["Cota"] = pd.to_numeric(df["Cota"], errors="coerce")
            df["Real"] = pd.to_numeric(df["Real"], errors="coerce")
            df = df.dropna(subset=["Cota"])
            df["Real"] = df["Real"].fillna(0)
            df["GAP"] = df["Real"] - df["Cota"]
            df = df[["Cluster", "Cidade", "Data", "Horário", "Atividade", "Cota", "Real", "GAP"]]
        except Exception:
            return pd.DataFrame()

    return _limpar_base_cotas(df, coluna_chave="chave_cota_minutos")


def dias_disponiveis(df: pd.DataFrame) -> list:
    """Lista as datas (strings 'AAAA/MM/DD') presentes na base, em ordem crescente."""
    if df.empty or "Data" not in df.columns:
        return []
    return sorted(df["Data"].dropna().unique().tolist())


def formatar_data_br(data_str: str) -> str:
    """Converte 'AAAA/MM/DD' (formato da base de Cotas) para 'DD/MM/AAAA'."""
    convertida = pd.to_datetime(data_str, errors="coerce", format="%Y/%m/%d")
    if pd.isna(convertida):
        # fallback pra qualquer outro formato que apareça na base
        convertida = pd.to_datetime(data_str, errors="coerce", dayfirst=False)
    return convertida.strftime("%d/%m/%Y") if not pd.isna(convertida) else str(data_str)


def _normalizar_texto(texto) -> str:
    """Maiúsculas, sem acento e sem espaços nas pontas — pra comparar nomes
    de Cluster/Cidade entre bases diferentes (a grafia exata pode variar,
    ex.: 'Florianópolis' vs 'FLORIANOPOLIS', ou nomes "sujos" vindos do
    Oracle como 'Joinville - Cetp')."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper()


def filtrar_cotas_por_segmentacao_global(df_cotas: pd.DataFrame, df_producao: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica na base de Cotas a mesma segmentação de Estado/Cluster/Cidade
    escolhida na barra de filtros do topo do site (já aplicada em
    `df_producao`, que é o `df` recebido em `render(df, indicadores)`).

    A base de Cotas não tem coluna "Estado" e o nome de Cidade pode vir
    "sujo" (ex.: "Joinville - Cetp", "Rio Do Sul - Fibrasil"), então o
    cruzamento é feito por nome normalizado: Cluster por igualdade exata
    (os nomes de Cluster são limpos e batem 1:1 nas duas bases) e Cidade
    por correspondência parcial (contém/está contido) — o suficiente pra
    reconhecer "Rio Do Sul - Fibrasil" como a cidade "Rio Do Sul", etc.

    A Data NÃO entra aqui — a aba de Cotas tem seletor de dia próprio
    (D0..D6), independente da segmentação de Data do topo do site.
    """
    if df_cotas.empty or df_producao is None or df_producao.empty:
        return df_cotas
    if "Cluster" not in df_producao.columns or "Cluster" not in df_cotas.columns:
        return df_cotas

    clusters_prod = {_normalizar_texto(c) for c in df_producao["Cluster"].dropna().unique()}
    if clusters_prod:
        df_cotas = df_cotas[df_cotas["Cluster"].apply(lambda c: _normalizar_texto(c) in clusters_prod)]

    if "Cidade" in df_producao.columns and "Cidade" in df_cotas.columns and not df_cotas.empty:
        cidades_prod = [_normalizar_texto(c) for c in df_producao["Cidade"].dropna().unique()]
        cidades_prod = [c for c in cidades_prod if c]
        if cidades_prod:

            def _cidade_bate(cidade_cota):
                nome = _normalizar_texto(cidade_cota)
                return any(nome and (nome in c or c in nome) for c in cidades_prod)

            df_cotas = df_cotas[df_cotas["Cidade"].apply(_cidade_bate)]

    return df_cotas


def _pct_agendada(cota: float, real: float) -> float:
    return 0.0 if cota == 0 else real / cota


def resumo_cards(df_dia: pd.DataFrame) -> dict:
    """Totais gerais do dia: Cotas Abertas, Atribuídas, Delta e %Agendada."""
    if df_dia.empty:
        return {"Cota": 0, "Real": 0, "GAP": 0, "%Agendada": 0.0}

    cota = int(df_dia["Cota"].sum())
    real = int(df_dia["Real"].sum())
    gap = int(df_dia["GAP"].sum())
    return {"Cota": cota, "Real": real, "GAP": gap, "%Agendada": _pct_agendada(cota, real)}


def resumo_turno(df_dia: pd.DataFrame) -> tuple:
    """
    Réplica da tabela "Distribuição por Turno": uma linha por Atividade,
    colunas = Horário, com a Cota, o Real (Ativ.) e o GAP lado a lado —
    a Cota fica visível pra explicar de onde vem o Gap. Retorna
    (pivot_cota, pivot_real, pivot_gap) já na ordem dos horários como
    aparecem na base (não em ordem alfabética).
    """
    if df_dia.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    horarios_ordem = list(dict.fromkeys(df_dia["Horário"].tolist()))

    agrupado = df_dia.groupby(["Atividade", "Horário"], as_index=False).agg(
        Cota=("Cota", "sum"), Real=("Real", "sum"), GAP=("GAP", "sum")
    )

    pivot_cota = agrupado.pivot(index="Atividade", columns="Horário", values="Cota").fillna(0).astype(int)
    pivot_real = agrupado.pivot(index="Atividade", columns="Horário", values="Real").fillna(0).astype(int)
    pivot_gap = agrupado.pivot(index="Atividade", columns="Horário", values="GAP").fillna(0).astype(int)

    colunas_validas = [h for h in horarios_ordem if h in pivot_real.columns]
    pivot_cota = pivot_cota.reindex(columns=colunas_validas)
    pivot_real = pivot_real.reindex(columns=colunas_validas)
    pivot_gap = pivot_gap.reindex(columns=colunas_validas)

    return pivot_cota, pivot_real, pivot_gap


def resumo_horario_cidade(df_dia: pd.DataFrame) -> pd.DataFrame:
    """
    Detalhe por Time Slot dentro de cada Cidade (nível mais fino da árvore
    Cluster > Cidade > Horário): Cota, Real e Delta por horário, na ordem
    em que os horários aparecem na base.
    """
    if df_dia.empty:
        return pd.DataFrame()

    horarios_ordem = list(dict.fromkeys(df_dia["Horário"].tolist()))

    agrupado = df_dia.groupby(["Cluster", "Cidade", "Horário"], as_index=False).agg(
        Cota=("Cota", "sum"), Real=("Real", "sum"), GAP=("GAP", "sum")
    )
    agrupado = agrupado.rename(columns={"GAP": "Delta"})
    agrupado["%Agendada"] = agrupado.apply(lambda r: _pct_agendada(r["Cota"], r["Real"]), axis=1)
    agrupado["_ordem"] = agrupado["Horário"].map({h: i for i, h in enumerate(horarios_ordem)})
    agrupado = agrupado.sort_values("_ordem").drop(columns="_ordem")

    return agrupado


def resumo_cluster_cidade(df_dia: pd.DataFrame) -> tuple:
    """
    Réplica da tabela "COTAS" (árvore Cluster > Cidade): Cotas Abertas
    (soma Cota), Cotas Atribuídas (soma Real), Delta (soma GAP) e
    %Agendada (Real/Cota) — uma versão agregada por Cluster e outra por
    Cidade (pra alimentar o expander de cada cluster).
    """
    if df_dia.empty:
        return pd.DataFrame(), pd.DataFrame()

    def _agg(sub):
        cota = int(sub["Cota"].sum())
        real = int(sub["Real"].sum())
        gap = int(sub["GAP"].sum())
        return pd.Series(
            {"Cotas Abertas": cota, "Cotas Atribuídas": real, "Delta": gap, "%Agendada": _pct_agendada(cota, real)}
        )

    por_cidade = df_dia.groupby(["Cluster", "Cidade"]).apply(_agg, include_groups=False).reset_index()
    por_cluster = df_dia.groupby("Cluster").apply(_agg, include_groups=False).reset_index()

    # groupby.apply retorna as colunas inteiras como float (mistura com
    # %Agendada na mesma Series) — devolve pro tipo inteiro pra exibição.
    for tabela in (por_cidade, por_cluster):
        for col in ("Cotas Abertas", "Cotas Atribuídas", "Delta"):
            tabela[col] = tabela[col].astype(int)

    return por_cluster.sort_values("Cluster"), por_cidade


def matriz_agendada_slot(df_dia: pd.DataFrame, nivel: str = "Cluster") -> pd.DataFrame:
    """
    Réplica da tabela "%AGENDADA_SLOT": % Real/Cota por Horário, agrupado
    por Cluster (ou por Cidade, se nivel="Cidade").
    """
    if df_dia.empty or nivel not in df_dia.columns:
        return pd.DataFrame()

    horarios_ordem = list(dict.fromkeys(df_dia["Horário"].tolist()))

    agrupado = df_dia.groupby([nivel, "Horário"], as_index=False).agg(Real=("Real", "sum"), Cota=("Cota", "sum"))
    agrupado["%Agendada"] = agrupado.apply(lambda r: _pct_agendada(r["Cota"], r["Real"]), axis=1)

    matriz = agrupado.pivot(index=nivel, columns="Horário", values="%Agendada").fillna(0.0)
    matriz = matriz.reindex(columns=[h for h in horarios_ordem if h in matriz.columns])

    return matriz
