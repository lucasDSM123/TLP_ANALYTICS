import streamlit as st

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
# SIDEBAR
# ================================================

# ================================================
# CARREGAR DADOS
# ================================================

df_base = carregar_base()

# Data/hora da extração da base: a coluna "Data Extração" só vem
# preenchida nas linhas do dia mais recente carregado (o restante do
# histórico fica com esse campo vazio), então pegamos o valor máximo
# não nulo para saber quando a base foi extraída pela última vez.
data_extracao = None
if "Data Extração" in df_base.columns:
    serie_extracao = df_base["Data Extração"].dropna()
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
# O seletor deixou de ser global: agora cada página decide se o usa e
# onde ele aparece. Dashboard e Relatórios renderizam o seletor
# internamente (Dashboard mais abaixo, afetando só os indicadores
# daquela página; Relatórios no topo da própria página). Coordenadores,
# Supervisores não tem mais esse filtro.

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
