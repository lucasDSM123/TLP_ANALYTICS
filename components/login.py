import streamlit as st

import config
from services.auth import verificar_login
from utils.assets import imagem_como_data_uri


def tela_login():
    """
    Renderiza a tela de login. Se o login for válido, guarda o usuário
    em st.session_state e força um rerun para liberar o app.
    Deve ser chamada no topo do app.py, ANTES de qualquer conteúdo do dashboard.
    """
    logo_uri = imagem_como_data_uri(config.LOGO_PATH)
    login_bg_uri = imagem_como_data_uri(config.LOGIN_BACKGROUND_IMAGE_PATH)

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-color: #FFFFFF !important;
            background-image:
                linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.82) 100%),
                url("{login_bg_uri}") !important;
            background-repeat: no-repeat !important;
            background-position: center center !important;
            background-size: cover !important;
        }}
        [data-testid="stSidebar"] {{
            display: none;
        }}
        .tlp-login-wrapper {{
            display: flex;
            justify-content: center;
            margin-top: 10vh;
        }}
        .tlp-login-card {{
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(8px);
            border: 1px solid {config.CARD_BORDER};
            border-radius: 16px;
            padding: 32px 36px;
            width: 100%;
            max-width: 380px;
            text-align: center;
            box-shadow: 0 12px 40px rgba(20,20,30,0.12);
        }}
        .tlp-login-logo {{
            display: block;
            max-width: 180px;
            width: 60%;
            height: auto;
            margin: 0 auto 16px auto;
        }}
        .tlp-login-title {{
            color: {config.TEXT};
            font-size: 20px;
            font-weight: 700;
            margin: 0 0 4px 0;
        }}
        .tlp-login-sub {{
            color: {config.TEXT_MUTED};
            font-size: 13px;
            margin-bottom: 24px;
        }}
        [data-testid="stTextInput"] label {{
            color: {config.TEXT_MUTED} !important;
        }}
        </style>
        <div class="tlp-login-wrapper">
            <div class="tlp-login-card">
                <img src="{logo_uri}" class="tlp-login-logo">
                <div class="tlp-login-title">{config.APP_NAME}</div>
                <div class="tlp-login-sub">Faça login para continuar</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Formulário centralizado, logo abaixo do "cartão" visual acima
    _, col_meio, _ = st.columns([1, 1.2, 1])
    with col_meio:
        with st.form("form_login", clear_on_submit=False):
            login = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            if not login or not senha:
                st.warning("Preencha usuário e senha.")
            else:
                usuario = verificar_login(login, senha)
                if usuario:
                    st.session_state["usuario_logado"] = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")


def logout():
    """Limpa a sessão do usuário logado."""
    if "usuario_logado" in st.session_state:
        del st.session_state["usuario_logado"]
    st.rerun()


def usuario_autenticado() -> bool:
    """Verifica se há um usuário válido na sessão atual."""
    return "usuario_logado" in st.session_state
