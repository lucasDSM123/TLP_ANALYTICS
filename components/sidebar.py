import streamlit as st
from streamlit_option_menu import option_menu

import config
from utils.assets import imagem_como_data_uri
from components.login import logout

# Chave usada no session_state para lembrar qual aba estava ativa. Guardar
# isso separado do widget é o que garante que a aba correta continua
# selecionada mesmo se o componente do menu precisar remontar (ex.: quando
# o tema muda e os valores de cor passados em `styles` mudam junto).
CHAVE_PAGINA_ATUAL = "tlp_pagina_atual"


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

        # Recupera a última página selecionada (se existir) pra calcular o
        # índice inicial do menu. Sem isso, qualquer remount do componente
        # (ex.: troca de tema, que muda as cores do `styles` abaixo) volta
        # sempre pro índice 0 (Dashboard), ignorando onde o usuário estava.
        pagina_salva = st.session_state.get(CHAVE_PAGINA_ATUAL, config.PAGES[0])
        indice_atual = config.PAGES.index(pagina_salva) if pagina_salva in config.PAGES else 0

        pagina = option_menu(
            menu_title=None,
            options=config.PAGES,
            icons=config.PAGE_ICONS,
            default_index=indice_atual,
            key="tlp_menu_principal",  # identidade fixa: evita que o componente seja tratado como "novo" a cada rerun
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

        # Persiste a escolha atual pra próxima renderização (ver acima).
        st.session_state[CHAVE_PAGINA_ATUAL] = pagina

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