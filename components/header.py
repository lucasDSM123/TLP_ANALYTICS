import streamlit as st
from datetime import datetime

import config


def header(subtitulo: str = "Dashboard Operacional", data_extracao=None):
    """Cabeçalho superior com título da página, data/hora de extração da
    base, sino de notificações e avatar do usuário (genérico, sem foto
    real). Se `data_extracao` for informado, mostra a data/hora em que a
    base de dados foi extraída pela última vez no canto superior direito
    (onde antes ficava o status "ONLINE", removido por ser informação
    sem utilidade real pro usuário)."""

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if data_extracao is not None:
        try:
            extracao_fmt = data_extracao.strftime("%d/%m/%Y %H:%M")
        except AttributeError:
            extracao_fmt = str(data_extracao)
    else:
        extracao_fmt = None

    # Badge de data/hora de extração — antes ficava solto no canto
    # esquerdo (abaixo do título); agora mora no canto superior direito,
    # no lugar do antigo status "ONLINE" + relógio ao vivo.
    extracao_html = (
        '<div style="text-align:right;">'
        '<div style="display:inline-flex; align-items:center; gap:6px; font-weight:600; color:#FFFFFF;">'
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'style="width:15px; height:15px; stroke:#FFFFFF; flex-shrink:0;">'
        '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path>'
        '</svg>'
        f'{"Base extraída em" if extracao_fmt else "Atualizado em"}'
        '</div>'
        f'<div style="color:rgba(255,255,255,0.85); font-size:13px;">{extracao_fmt or agora}</div>'
        '</div>'
    )

    # HTML montado como uma única linha (sem indentação) para evitar que o
    # parser de Markdown do Streamlit interprete blocos indentados como
    # "código" e exiba as tags literalmente em vez de renderizá-las.
    html = (
        '<div class="tlp-header">'
        '<div style="display:flex; justify-content:space-between; align-items:center;">'
        '<div>'
        f'<h2 style="margin:0;">{config.APP_ICON} {config.APP_NAME}</h2>'
        f'<span style="opacity:0.85;">{subtitulo}</span>'
        '</div>'
        '<div style="display:flex; align-items:center; gap:22px;">'
        f'{extracao_html}'
        '<div class="tlp-header-actions">'
        '<div class="tlp-header-bell">'
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0"></path>'
        '</svg>'
        '<span class="tlp-badge-dot"></span>'
        '</div>'
        '<div class="tlp-header-avatar" title="Usuário logado">'
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>'
        '<circle cx="12" cy="7" r="4"></circle>'
        '</svg>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)

    # Botão de alternância de tema (laranja original / navy) — fica logo
    # abaixo do banner do header, alinhado à direita, discreto.
    tema = config.tema_atual()
    proximo_label = config.TEMA_LABELS["navy"] if tema == "laranja" else config.TEMA_LABELS["laranja"]
    _, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button(f"Trocar p/ {proximo_label}", key="tlp_toggle_tema", use_container_width=True):
            config.alternar_tema()


def secao_titulo(titulo: str, subtitulo: str = ""):
    """Título de seção com barra lateral colorida (padrão de marca TLP)."""
    st.markdown(
        f"""
        <div class="tlp-section-title">
            <div class="bar"></div>
            <h3>{titulo}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if subtitulo:
        st.markdown(f"<p class='tlp-section-sub'>{subtitulo}</p>", unsafe_allow_html=True)