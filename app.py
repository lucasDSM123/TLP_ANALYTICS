import streamlit as st
import pandas as pd

import config
from components.sidebar import sidebar
from components.header import header, secao_titulo
from components.filtros import filtros_topo
from components.login import tela_login, usuario_autenticado, logout
from services.loader import carregar_base
from services.indicadores import Indicadores
from utils.assets import imagem_como_data_uri

from views import dashboard, gestores, relatorios, configuracoes

# ================================================
# CONFIGURAÇÃO INICIAL
# ================================================

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================
# CSS + TEMA (imagem de fundo TLP embutida em base64)
# ================================================

with open(config.CSS_PATH, encoding="utf-8") as f:
    css = f.read()

# Tokens de cor da paleta única TLP (config.py).
css = css.replace("__TLP_BG__", config.BACKGROUND)
css = css.replace("__TLP_SURFACE__", config.SURFACE)
css = css.replace("__TLP_CARD__", config.CARD)
css = css.replace("__TLP_CARD_BORDER__", config.CARD_BORDER)
css = css.replace("__TLP_SIDEBAR__", config.SIDEBAR)
css = css.replace("__TLP_TEXT__", config.TEXT)
css = css.replace("__TLP_TEXT_MUTED__", config.TEXT_MUTED)
css = css.replace("__TLP_SIDEBAR_OVERLAY_1__", config.SIDEBAR_OVERLAY_1)
css = css.replace("__TLP_SIDEBAR_OVERLAY_2__", config.SIDEBAR_OVERLAY_2)
css = css.replace("__TLP_SIDEBAR_TEXT_MUTED__", config.SIDEBAR_TEXT_MUTED)
css = css.replace("__TLP_HEADER_GRADIENT__", config.HEADER_GRADIENT)

background_uri = imagem_como_data_uri(config.BACKGROUND_IMAGE_PATH)
css = css.replace("__BACKGROUND_IMAGE__", background_uri)

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ================================================
# GATE DE LOGIN — nada abaixo renderiza sem autenticação
# ================================================

if not usuario_autenticado():
    tela_login()
    st.stop()

# ================================================
# CARREGAR DADOS
# ================================================

df_base = carregar_base()

# Trata casos em que a base não pôde ser carregada ou retornou vazia/com erro
if df_base is None or not hasattr(df_base, "columns") or df_base.empty:
    st.error("⚠️ Não foi possível carregar os dados do banco de dados Neon ou a tabela está vazia.")
    st.info("Por favor, verifique a conexão com o banco de dados e as configurações de acesso.")
    st.stop()

# Data/hora da extração da base: a coluna de extração só vem
# preenchida nas linhas do dia mais recente carregado, então pegamos
# o valor máximo não nulo para saber quando a base foi extraída.
data_extracao = None
col_extracao = next((c for c in df_base.columns if c.lower() in ["data extração", "data_extracao"]), None)

if col_extracao:
    serie_extracao = df_base[col_extracao].dropna()
    if not serie_extracao.empty:
        data_extracao = serie_extracao.max()

# ================================================
# SIDEBAR
# ================================================

pagina = sidebar()
header(subtitulo=pagina, data_extracao=data_extracao)
st.divider()

# ================================================
# SEGMENTAÇÕES (topo do site)
# ================================================

df = filtros_topo(df_base)
st.divider()

# ================================================
# INDICADOR EM FOCO
# ================================================

indicadores = Indicadores(df)

# ================================================
# ROTEAMENTO DE PÁGINAS
# ================================================

PAGINAS = {
    "Dashboard": dashboard,
    "Gestores": gestores,
    "Relatórios": relatorios,
    "Configurações": configuracoes,
}

modulo = PAGINAS.get(pagina, dashboard)
modulo.render(df, indicadores)