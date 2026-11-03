import streamlit as st

import config
from utils.assets import imagem_como_data_uri
from components.login import logout

# Chave usada no session_state para lembrar qual aba estava ativa. Guardar
# isso separado do widget é o que garante que a aba correta continua
# selecionada mesmo se o menu precisar remontar (ex.: quando o tema muda e
# as cores do CSS abaixo mudam junto).
CHAVE_PAGINA_ATUAL = "tlp_pagina_atual"

# O menu é um st.radio NATIVO do Streamlit estilizado por CSS (antes era o
# componente de terceiros `streamlit-option-menu`, que deixou de carregar no
# servidor com as versões novas do Streamlit). Nativo = sem arquivo externo
# pra baixar, então não quebra com atualização de versão. Ícones em emoji,
# na mesma ordem de config.PAGES.
ICONES_PAGINAS = {
    "Dashboard": "📊",
    "Acumulado Mês": "🗓️",
    "Alongados": "⏳",
    "Cotas": "📋",
    "Atribuição": "👤",
    "Chegada": "🕒",
    "Backlog Reparo": "🛠️",
    "Gestores": "👥",
    "Analítica": "📈",
    "Relatórios": "📑",
    "Configurações": "⚙️",
}


def _css_menu() -> str:
    """CSS que transforma o st.radio da sidebar em um menu de navegação:
    esconde a bolinha, deixa cada opção como um 'botão' e destaca a página
    ativa com o degradê da marca (cores seguem o tema atual)."""
    return f"""
    <style>
    section[data-testid="stSidebar"] [data-testid="stRadio"] > label {{ display: none; }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {{
        gap: 0; padding: 0;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {{
        margin: 3px 8px; padding: 8px 12px; border-radius: 8px; width: auto;
        cursor: pointer; background: transparent;
    }}
    /* esconde a bolinha do radio */
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {{
        display: none;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label p {{
        font-size: 14px; color: {config.SIDEBAR_TEXT_MUTED}; margin: 0;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {{
        background: rgba(255,255,255,0.08);
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {{
        background: {config.BRAND_GRADIENT};
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p {{
        color: white; font-weight: 600;
    }}
    </style>
    """


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
        # índice inicial do menu. Sem isso, qualquer remount do menu (ex.:
        # troca de tema) voltaria sempre pro índice 0 (Dashboard).
        pagina_salva = st.session_state.get(CHAVE_PAGINA_ATUAL, config.PAGES[0])
        indice_atual = config.PAGES.index(pagina_salva) if pagina_salva in config.PAGES else 0

        st.markdown(_css_menu(), unsafe_allow_html=True)
        pagina = st.radio(
            "Navegação",
            options=config.PAGES,
            index=indice_atual,
            key="tlp_menu_principal",  # identidade fixa entre reruns
            format_func=lambda p: f"{ICONES_PAGINAS.get(p, '•')}  {p}",
            label_visibility="collapsed",
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