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
# TEMAS — "laranja" (marca TLP original) e "navy" (variante azul
# marinho escuro). Cada tema é um conjunto completo de cores; trocar
# de tema só troca QUAL dicionário abaixo é aplicado nas constantes
# de cor deste módulo (TLP_ORANGE, BACKGROUND, etc.) — o resto do
# site sempre lê essas constantes normalmente, sem saber que existe
# mais de um tema.
# ------------------------------------------------------------------
TEMAS = {
    "laranja": {
        "TLP_ORANGE": "#FF6A00",
        "TLP_ORANGE_LIGHT": "#FF8A3D",
        "TLP_RED": "#E8391D",
        "TLP_GOLD": "#FFB020",
        "TLP_YELLOW": "#FFC94A",
        "BRAND_GRADIENT": "linear-gradient(135deg, #E8391D 0%, #FF6A00 55%, #FFB020 100%)",
        "BRAND_GRADIENT_STOPS": ["#E8391D", "#FF6A00", "#FFB020"],
        "BACKGROUND": "#F6F7F9",
        "SURFACE": "#FFFFFF",
        "CARD": "#FFFFFF",
        "CARD_BORDER": "#E4E7EC",
        "TEXT": "#1F2430",
        "TEXT_MUTED": "#6B7280",
        "OVERLAY_1": "rgba(255,255,255,0.96)",
        "OVERLAY_2": "rgba(255,255,255,0.92)",
        "OVERLAY_3": "rgba(255,255,255,0.98)",
        "SIDEBAR": "#0B0E14",
        "SIDEBAR_OVERLAY_1": "rgba(11,14,20,0.92)",
        "SIDEBAR_OVERLAY_2": "rgba(11,14,20,0.75)",
        "SIDEBAR_TEXT_MUTED": "#9AA3B2",
        "HEADER_GRADIENT": "linear-gradient(120deg, #E8391D 0%, #FF6A00 55%, #FFB020 100%)",
        "CSS_PATH": "assets/css/style_laranja.css",
    },
    "navy": {
        "TLP_ORANGE": "#2E63C7",
        "TLP_ORANGE_LIGHT": "#5B8DEF",
        "TLP_RED": "#F04438",
        "TLP_GOLD": "#38BDF8",
        "TLP_YELLOW": "#7DD8FA",
        "BRAND_GRADIENT": "linear-gradient(135deg, #0A1930 0%, #123262 50%, #2E63C7 100%)",
        "BRAND_GRADIENT_STOPS": ["#0A1930", "#123262", "#2E63C7"],
        "BACKGROUND": "#F4F6FA",
        "SURFACE": "#FFFFFF",
        "CARD": "#FFFFFF",
        "CARD_BORDER": "#E2E6EF",
        "TEXT": "#1B2436",
        "TEXT_MUTED": "#64748B",
        "OVERLAY_1": "rgba(255,255,255,0.96)",
        "OVERLAY_2": "rgba(255,255,255,0.92)",
        "OVERLAY_3": "rgba(255,255,255,0.98)",
        "SIDEBAR": "#060F22",
        "SIDEBAR_OVERLAY_1": "rgba(6,15,34,0.94)",
        "SIDEBAR_OVERLAY_2": "rgba(6,15,34,0.80)",
        "SIDEBAR_TEXT_MUTED": "#8EA3C7",
        "HEADER_GRADIENT": "linear-gradient(120deg, #0A1930 0%, #123262 55%, #2E63C7 100%)",
        "CSS_PATH": "assets/css/style_navy.css",
    },
}

TEMA_PADRAO = "laranja"
TEMA_LABELS = {"laranja": "🟠 Laranja", "navy": "🔵 Navy"}


def tema_atual() -> str:
    """Nome do tema ativo na sessão atual (padrão: laranja, o de sempre)."""
    return st.session_state.get("tlp_tema", TEMA_PADRAO)


def alternar_tema() -> None:
    """Troca pro outro tema disponível e força o rerender da página."""
    atual = tema_atual()
    proximo = "navy" if atual == "laranja" else "laranja"
    st.session_state["tlp_tema"] = proximo
    st.rerun()


def aplicar_tema_da_sessao() -> None:
    """
    Sobrescreve as constantes de cor deste módulo (TLP_ORANGE, BACKGROUND,
    CSS_PATH etc.) com os valores do tema ativo na sessão. Chamado no
    início do app.py, antes de qualquer CSS ou componente ser montado —
    daí em diante todo `config.TLP_ORANGE`, `config.CARD` etc. usado
    pelo resto do site (components/, services/, views/) já reflete o
    tema escolhido, sem precisar tocar em mais nenhum arquivo.
    """
    tema = TEMAS.get(tema_atual(), TEMAS[TEMA_PADRAO])
    globals().update(tema)
    _recalcular_derivados()


# Estados (não variam por tema)
SUCCESS = "#22C55E"
INFO = "#3B82F6"

# Valores de cor iniciais (tema padrão) — sobrescritos em runtime por
# aplicar_tema_da_sessao(). Mantidos aqui também para scripts que
# importam config sem passar pelo app.py (ex.: criar_primeiro_usuario.py).
globals().update(TEMAS[TEMA_PADRAO])
WARNING = TLP_GOLD
DANGER = TLP_RED

# Paleta sequencial para gráficos (BA / TT / MSK / Geral) — computada a
# partir das cores do tema ativo; refeita dentro de aplicar_tema_da_sessao()
# não é necessária porque estas listas são recriadas a cada import/uso
# indireto via função abaixo.
CHART_BA = "#00C9A7"
CHART_MSK = "#7B8CDE"


def _recalcular_derivados() -> None:
    """Recalcula WARNING/DANGER e as paletas de gráfico a partir das
    cores de marca atuais — chamado logo após aplicar_tema_da_sessao()."""
    g = globals()
    g["WARNING"] = g["TLP_GOLD"]
    g["DANGER"] = g["TLP_RED"]
    g["CHART_TT"] = g["TLP_ORANGE"]
    g["CHART_GERAL"] = g["TLP_GOLD"]
    g["CHART_COLORWAY"] = [g["TLP_ORANGE"], g["TLP_GOLD"], "#00E5C7", g["TLP_RED"], "#8C7BFF", "#FF5C8A", "#3BCBFF"]
    g["CHART_GRADIENT_SCALE"] = [g["TLP_RED"], g["TLP_ORANGE"], g["TLP_GOLD"], "#3BCBFF"]


CHART_TT = TLP_ORANGE
CHART_GERAL = TLP_GOLD
CHART_COLORWAY = [TLP_ORANGE, TLP_GOLD, "#00E5C7", TLP_RED, "#8C7BFF", "#FF5C8A", "#3BCBFF"]
CHART_GRADIENT_SCALE = [TLP_RED, TLP_ORANGE, TLP_GOLD, "#3BCBFF"]

# ------------------------------------------------------------------
# CAMINHOS E BANCO DE DADOS
# ------------------------------------------------------------------
LOGO_PATH = "assets/images/logo.png"
BACKGROUND_IMAGE_PATH = "assets/images/background.png"
LOGIN_BACKGROUND_IMAGE_PATH = "assets/images/login_bg.jpg"
# CSS_PATH não é fixo: vem do dicionário TEMAS (cada tema aponta pro
# seu próprio arquivo CSS) e já está definido em globals() pelas linhas
# acima (globals().update(TEMAS[TEMA_PADRAO])).

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
META_ATRIBUICAO_ALVO = 4.0

# ------------------------------------------------------------------
# NAVEGAÇÃO
# ------------------------------------------------------------------
PAGES = ["Dashboard", "Acumulado Mês", "Cotas", "Chegada", "Gestores", "Relatórios", "Configurações"]
PAGE_ICONS = ["speedometer2", "calendar2-check", "clipboard-data", "clock-history", "people", "bar-chart-line", "gear"]