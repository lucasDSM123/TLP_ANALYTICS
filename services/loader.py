import numpy as np
import pandas as pd
import streamlit as st
from services.database import ler_dados_do_neon
import config


def hhmm_para_minutos(serie: pd.Series) -> pd.Series:
    """Converte texto "HH:MM" (ou "HH:MM:SS") em minutos (float). Vazio/inválido vira NaN."""
    if pd.api.types.is_timedelta64_dtype(serie):
        return serie.dt.total_seconds() / 60
    partes = serie.astype("string").str.strip().str.extract(r"^(\d{1,3}):(\d{2})(?::(\d{2}))?$")
    h = pd.to_numeric(partes[0], errors="coerce")
    m = pd.to_numeric(partes[1], errors="coerce")
    seg = pd.to_numeric(partes[2], errors="coerce").fillna(0)
    minutos = (h * 60 + m + seg / 60).to_numpy(dtype="float64", na_value=np.nan)
    return pd.Series(minutos, index=serie.index)


@st.cache_data(show_spinner=False, ttl=600)
def carregar_base() -> pd.DataFrame:
    """
    Carrega a base tratada direto do Neon (Postgres) e mantém em cache por 10 min.
    Para forçar atualização antes do TTL expirar, chame st.cache_data.clear().

    Anexa `config.COL_DESLOC_MIN` (minutos, float) a partir da coluna de texto
    "Tempo de Deslocamento" (HH:MM), para as matrizes calcularem a média.
    """
    df = ler_dados_do_neon(config.DATABASE_TABLE)
    if config.COL_DESLOC_TEXTO in df.columns:
        minutos = hhmm_para_minutos(df[config.COL_DESLOC_TEXTO])
        if config.DESLOC_IGNORAR_ZERO:
            minutos = minutos.where(minutos > 0)
        df[config.COL_DESLOC_MIN] = minutos
    return df


def opcoes_filtro(df: pd.DataFrame, coluna: str) -> list:
    """Retorna a lista de opções únicas (ordenadas) de uma coluna, com 'Todos' no início."""
    if coluna not in df.columns:
        return ["Todos"]
    valores = sorted(df[coluna].dropna().unique().tolist())
    return ["Todos"] + valores


def aplicar_filtro(df: pd.DataFrame, coluna: str, valor) -> pd.DataFrame:
    """Filtra o dataframe por uma coluna/valor, ignorando quando valor é 'Todos' ou None."""
    if valor is None or valor == "Todos" or coluna not in df.columns:
        return df
    return df[df[coluna] == valor]
