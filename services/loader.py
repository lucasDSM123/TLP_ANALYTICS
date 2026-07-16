import pandas as pd
import streamlit as st
from services.database import ler_dados_do_neon
import config


@st.cache_data(show_spinner=False, ttl=600)
def carregar_base() -> pd.DataFrame:
    """
    Carrega a base tratada direto do Neon (Postgres) e mantém em cache por 10 min.
    Para forçar atualização antes do TTL expirar, chame st.cache_data.clear().
    """
    return ler_dados_do_neon(config.DATABASE_TABLE)


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
