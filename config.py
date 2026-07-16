# config.py
"""
Configurações globais e paleta de marca do TLP Analytics.
Cores extraídas da identidade visual TLP (logo T-L-P laranja/vermelho/dourado).
"""
import os
from dotenv import load_dotenv
import streamlit as st

# Carrega as variáveis de ambiente do .env para o sistema
load_dotenv()

APP_NAME = "TLP Analytics"
APP_ICON = "📊"

# ------------------------------------------------------------------
# PALETA DE MARCA TLP
# (fixa: aparece igual nos dois temas — é a identidade visual)
# ------------------------------------------------------------------
TLP_ORANGE = "#FF6A00"      # laranja principal (T e P)
TLP_ORANGE_LIGHT = "#FF8A3D"
TLP_RED = "#E8391D"         # vermelho de destaque (detalhes do T e P)
TLP_GOLD = "#FFB020"        # dourado (L)
TLP_YELLOW = "#FFC94A"

# Estados
SUCCESS = "#22C55E"
WARNING = TLP_GOLD
DANGER = TLP_RED
INFO = "#3B82F6"

# Gradiente de marca (usado em headers/destaques)
BRAND_GRADIENT = f"linear-gradient(135deg, {TLP_RED} 0%, {TLP_ORANGE} 55%, {TLP_GOLD} 100%)"

# ------------------------------------------------------------------
# TEMA ÚNICO — mesma marca TLP, um layout só (sidebar escura + área
# de conteúdo clara com o banner de destaque em degradê laranja/dourado).
# ------------------------------------------------------------------
BACKGROUND = "#F6F7F9"
SURFACE = "#FFFFFF"
CARD = "#FFFFFF"
CARD_BORDER = "#E4E7EC"
TEXT = "#1F2430"
TEXT_MUTED = "#6B7280"
OVERLAY_1 = "rgba(255,255,255,0.96)"
OVERLAY_2 = "rgba(255,255,255,0.92)"
OVERLAY_3 = "rgba(255,255,255,0.98)"

# Sidebar: escura, com a imagem de marca por trás (mesmo fundo do app,
# só que com um overlay escuro para manter o contraste com o laranja).
SIDEBAR = "#0B0E14"
SIDEBAR_OVERLAY_1 = "rgba(11,14,20,0.92)"
SIDEBAR_OVERLAY_2 = "rgba(11,14,20,0.75)"
SIDEBAR_TEXT_MUTED = "#9AA3B2"

# Banner do topo (header) em degradê vivo da marca TLP.
HEADER_GRADIENT = "linear-gradient(120deg, #E8391D 0%, #FF6A00 55%, #FFB020 100%)"

# Paleta sequencial para gráficos (BA / TT / MSK / Geral)
CHART_BA = "#00C9A7"
CHART_TT = TLP_ORANGE
CHART_MSK = "#7B8CDE"
CHART_GERAL = TLP_GOLD

CHART_COLORWAY = [TLP_ORANGE, TLP_GOLD, "#00E5C7", TLP_RED, "#8C7BFF", "#FF5C8A", "#3BCBFF"]

# Escala contínua "futurista" usada em rankings/dispersões (vermelho -> laranja -> dourado -> ciano)
CHART_GRADIENT_SCALE = [TLP_RED, TLP_ORANGE, TLP_GOLD, "#3BCBFF"]

# ------------------------------------------------------------------
# CAMINHOS E BANCO DE DADOS
# ------------------------------------------------------------------
LOGO_PATH = "assets/images/logo.png"
BACKGROUND_IMAGE_PATH = "assets/images/background.png"
LOGIN_BACKGROUND_IMAGE_PATH = "assets/images/login_bg.jpg"
CSS_PATH = "assets/css/style.css"

# Caminho local (usado para atualizar o banco ou como backup secundário)
DATA_PATH = r"data/PRODUCAO_TLP_TRATADA.xlsx"

# Configurações do Banco de Dados Online (Neon PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_TABLE = "producao_tlp_tratada"  # Nome da tabela que criaremos no Neon

# ------------------------------------------------------------------
# TABELA "PRODUÇÃO POR COORDENADOR"
# ------------------------------------------------------------------
SIGLAS_CLUSTER = {
    frozenset({"BLUMENAU"}): "BNU",
    frozenset({"FLORIANOPOLIS", "LAGES", "CHAPECÓ"}): "FNS / LGS / CCO",
    frozenset({"JOINVILLE"}): "JVE",
}

META_PU_ALVO = 3
META_EFICACIA_ALVO = 0.70

# ------------------------------------------------------------------
# NAVEGAÇÃO
# ------------------------------------------------------------------
PAGES = ["Dashboard", "Gestores", "Relatórios", "Configurações"]
PAGE_ICONS = ["speedometer2", "people", "bar-chart-line", "gear"]