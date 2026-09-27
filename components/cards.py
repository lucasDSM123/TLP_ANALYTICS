import streamlit as st

# Mapeia palavras-chave do título para um ícone (emoji) — cobre os
# indicadores já existentes no dashboard sem precisar alterar todos os
# pontos onde card() é chamado.
_ICONS = [
    (("hc",), "🧑\u200d💼"),
    (("caixa",), "📥"),
    (("concluído ok", "concluido ok"), "✅"),
    (("não concluí", "nao conclui", "nok"), "❌"),
    (("eficácia", "eficacia"), "🎯"),
    (("projeção pu", "projecao pu"), "📈"),
    (("projeção", "projecao"), "🔮"),
    (("média", "media"), "📊"),
    (("bucket",), "🪣"),
    (("esteira",), "🧵"),
    (("iniciada",), "🚀"),
    (("pu",), "🔁"),
]


def _icone_automatico(title: str) -> str:
    titulo_lower = (title or "").lower()
    for chaves, emoji in _ICONS:
        if any(chave in titulo_lower for chave in chaves):
            return emoji
    return "📌"


def _fundo_icone_rgba(cor_hex: str, alpha: float = 0.16) -> str:
    """
    Converte uma cor hex (#RRGGBB) numa rgba() com opacidade `alpha` —
    substitui o antigo `color-mix(in srgb, cor 16%, transparent)` do CSS.

    Calculado aqui em Python (em vez de color-mix() no CSS) porque
    color-mix() não é suportada pelo html2canvas (usado no botão "Copiar
    imagem" das áreas do site), o que fazia o print falhar justamente nos
    cards. rgba() tem o mesmo resultado visual e funciona em qualquer
    navegador/biblioteca.
    """
    cor_hex = (cor_hex or "").lstrip("#")
    if len(cor_hex) != 6:
        return f"rgba(46, 99, 199, {alpha})"
    try:
        r, g, b = int(cor_hex[0:2], 16), int(cor_hex[2:4], 16), int(cor_hex[4:6], 16)
    except ValueError:
        return f"rgba(46, 99, 199, {alpha})"
    return f"rgba({r}, {g}, {b}, {alpha})"


def card(title: str, value, color: str = "#2E63C7", subtitle: str = "", icon: str = None,
         pu_site: float = None, pu_vivo_valor: float = None):
    """
    Renderiza um card KPI com título, valor, cor de destaque e subtítulo opcional.

    Args:
        title: Título do card
        value: Valor a ser exibido
        color: Cor hexadecimal da borda esquerda / ícone (padrão: laranja TLP)
        subtitle: Texto adicional abaixo do valor
        icon: Emoji do badge do card. Se não informado, é escolhido
            automaticamente com base no título.
        pu_site: valor de PU do nosso site (opcional). Quando informado
            junto com pu_vivo_valor E o toggle "Ver PU VIVO" estiver
            marcado, uma segunda linha comparativa é exibida abaixo do
            subtítulo — ex.: "PU Vivo: 1.68 (▲ 6%)".
        pu_vivo_valor: valor de PU no padrão do Backoffice Regional Sul
            (ver services/indicadores.py -> pu_vivo*()).
    """
    # Sempre renderiza o parágrafo do subtítulo (mesmo vazio) para que todos
    # os cards tenham exatamente a mesma estrutura/altura, com ou sem subtítulo.
    subtitle_html = f'<p class="kpi-subtitle">{subtitle if subtitle else "&nbsp;"}</p>'
    icone = icon if icon else _icone_automatico(title)
    fundo_icone = _fundo_icone_rgba(color)

    pu_vivo_html = ""
    if pu_site is not None and pu_vivo_valor is not None:
        from components.pu_vivo import pu_vivo_ativo, texto_comparativo_pu, cor_comparativo_pu
        if pu_vivo_ativo():
            texto = texto_comparativo_pu(pu_site, pu_vivo_valor)
            if texto:
                cor_pv = cor_comparativo_pu(pu_site, pu_vivo_valor)
                pu_vivo_html = f'<p class="kpi-subtitle" style="color:{cor_pv}; font-weight:700;">{texto}</p>'

    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: {color}; --kpi-color: {color}; --kpi-icon-bg: {fundo_icone};">
            <div class="kpi-title-row">
                <span class="kpi-icon">{icone}</span>
                <p class="kpi-title">{title}</p>
            </div>
            <h2 class="kpi-value">{value}</h2>
            {subtitle_html}
            {pu_vivo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
