import streamlit as st

import config
from utils.assets import imagem_como_data_uri
from components.login import logout

# Chave usada no session_state para lembrar qual aba estava ativa. Guardar
# isso separado do widget é o que garante que a aba correta continua
# selecionada mesmo se o menu precisar remontar (ex.: quando o tema muda e
# as cores do CSS abaixo mudam junto).
CHAVE_PAGINA_ATUAL = "tlp_pagina_atual"

# O menu é feito com botões NATIVOS do Streamlit (st.button) estilizados por
# CSS. Antes era o componente de terceiros `streamlit-option-menu` (parou de
# carregar no servidor) e depois um st.radio, mas o HTML interno do radio muda
# entre versões do Streamlit (localhost e Cloud ficavam diferentes). Botão tem
# HTML estável em qualquer versão e não depende de arquivo externo. Ícones em
# emoji, na mesma ordem de config.PAGES.
ICONES_PAGINAS = {
    "Produção Online": "📊",
    "Acumulado Mês": "🗓️",
    "Alongados": "⏳",
    "Cotas": "📋",
    "Atribuição": "👤",
    "Chegada": "🕒",
    "Backlog Reparo": "🛠️",
    "Analítica": "📈",
    "Relatórios": "📑",
    "Configurações": "⚙️",
}


def _css_menu() -> str:
    """CSS do menu: os botões de página viram itens de navegação (largura
    toda, texto à esquerda, fundo transparente) e o da página ativa recebe o
    degradê da marca. Escopo `.st-key-tlp_menu` (container com key) pra não
    mexer nos botões 'Sair' e 'Mudar para...'."""
    m = ".st-key-tlp_menu"
    return f"""
    <style>
    {m} {{ gap: 4px !important; }}
    {m} .stButton > button {{
        width: 100% !important; justify-content: flex-start !important;
        text-align: left !important; padding: 8px 12px !important;
        background: transparent !important; border: none !important;
        box-shadow: none !important; filter: none !important;
        border-radius: 8px !important; min-height: 0 !important;
    }}
    /* o conteúdo do botão (ícone + texto) vem centralizado por padrão:
       força tudo a começar na esquerda e o texto a ocupar a largura toda */
    {m} .stButton > button > div {{ width: 100% !important; }}
    {m} .stButton > button div,
    {m} .stButton > button span {{
        justify-content: flex-start !important; text-align: left !important;
    }}
    {m} .stButton > button p {{
        text-align: left !important; margin: 0 !important; font-size: 14px !important;
        font-weight: 400 !important; color: {config.SIDEBAR_TEXT_MUTED} !important;
    }}
    {m} .stButton > button:hover {{ background: rgba(255,255,255,0.08) !important; }}
    /* página ativa (botão type="primary") */
    {m} .stButton > button[kind="primary"],
    {m} .stButton > button[data-testid="stBaseButton-primary"] {{
        background: {config.BRAND_GRADIENT} !important;
    }}
    {m} .stButton > button[kind="primary"] p,
    {m} .stButton > button[data-testid="stBaseButton-primary"] p {{
        color: #FFFFFF !important; font-weight: 600 !important;
    }}
    </style>
    """


def _ir_para(pagina: str) -> None:
    """on_click dos botões do menu: guarda a página escolhida."""
    st.session_state[CHAVE_PAGINA_ATUAL] = pagina


def sidebar() -> str:
    """Renderiza a sidebar com logo TLP e menu de navegação. Retorna a página selecionada."""

    with st.sidebar:

        logo_uri = imagem_como_data_uri(config.LOGO_PATH)
        st.markdown(
            f"""
            <div class="tlp-sidebar-logo">
                <img src="{logo_uri}" style="width: 130px;">
            </div>
            <div class="tlp-sidebar-caption">Analytics</div>
            """,
            unsafe_allow_html=True,
        )

        # Página ativa: a última escolhida (guardada no session_state, então
        # sobrevive a troca de tema etc.); na primeira vez, o Dashboard.
        pagina = st.session_state.get(CHAVE_PAGINA_ATUAL, config.PAGES[0])
        if pagina not in config.PAGES:
            pagina = config.PAGES[0]
        st.session_state[CHAVE_PAGINA_ATUAL] = pagina

        st.markdown(_css_menu(), unsafe_allow_html=True)
        with st.container(key="tlp_menu"):
            for p in config.PAGES:
                st.button(
                    f"{ICONES_PAGINAS.get(p, '•')}  {p}",
                    key=f"menu_{p}",
                    type="primary" if p == pagina else "secondary",
                    use_container_width=True,
                    on_click=_ir_para,
                    args=(p,),
                )

        st.markdown("<hr>", unsafe_allow_html=True)

        usuario = st.session_state.get("usuario_logado")
        if usuario:
            nome = usuario["nome"]
            iniciais = "".join(p[0] for p in nome.split()[:2]).upper()
            st.markdown(
                f"""
                <div class="tlp-sidebar-user">
                    <div class="tlp-avatar">{iniciais}</div>
                    <div class="tlp-sidebar-user-name">{nome}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Sair", use_container_width=True):
                logout()

        st.markdown("<hr>", unsafe_allow_html=True)

        tema = config.tema_atual()
        proximo = "navy" if tema == "laranja" else "laranja"
        if st.button(
            f"Mudar para {config.TEMA_LABELS[proximo]}",
            use_container_width=True,
            key="botao_alternar_tema",
        ):
            config.alternar_tema()

        st.caption("© 2026 TLP · Operações Técnicas")

    return pagina