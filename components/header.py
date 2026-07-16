import streamlit as st
from datetime import datetime

import config


def header(subtitulo: str = "Dashboard Operacional", data_extracao=None):
    """Cabeçalho superior com título da página, status online, data/hora,
    sino de notificações e avatar do usuário (genérico, sem foto real).
    Se `data_extracao` for informado, mostra também a data/hora em que a
    base de dados foi extraída pela última vez."""

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    extracao_html = ""
    if data_extracao is not None:
        try:
            extracao_fmt = data_extracao.strftime("%d/%m/%Y %H:%M")
        except AttributeError:
            extracao_fmt = str(data_extracao)
        extracao_html = (
            '<div class="tlp-extracao-badge">'
            '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path>'
            '</svg>'
            f'Base extraída em {extracao_fmt}'
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
        f'{extracao_html}'
        '</div>'
        '<div style="display:flex; align-items:center; gap:22px;">'
        '<div style="text-align:right;">'
        '<div style="font-weight:600; color:#FFFFFF;">'
        '<span class="tlp-status-dot"></span>ONLINE'
        '</div>'
        f'<div style="color:rgba(255,255,255,0.85); font-size: 13px;">{agora}</div>'
        '</div>'
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
