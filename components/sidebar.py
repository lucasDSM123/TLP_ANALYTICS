import streamlit as st
from streamlit_option_menu import option_menu

import config
from utils.assets import imagem_como_data_uri
from components.login import logout


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

        pagina = option_menu(
            menu_title=None,
            options=config.PAGES,
            icons=config.PAGE_ICONS,
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": config.TLP_GOLD, "font-size": "16px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "3px 8px",
                    "border-radius": "8px",
                    "color": config.TEXT_MUTED,
                    "--hover-color": config.SURFACE,
                },
                "nav-link-selected": {
                    "background": config.BRAND_GRADIENT,
                    "color": "white",
                    "font-weight": "600",
                },
            },
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

        st.caption("© 2026 TLP · Operações Técnicas")

    return pagina
