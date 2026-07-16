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


def card(title: str, value, color: str = "#FF6A00", subtitle: str = "", icon: str = None):
    """
    Renderiza um card KPI com título, valor, cor de destaque e subtítulo opcional.

    Args:
        title: Título do card
        value: Valor a ser exibido
        color: Cor hexadecimal da borda esquerda / ícone (padrão: laranja TLP)
        subtitle: Texto adicional abaixo do valor
        icon: Emoji do badge do card. Se não informado, é escolhido
            automaticamente com base no título.
    """
    # Sempre renderiza o parágrafo do subtítulo (mesmo vazio) para que todos
    # os cards tenham exatamente a mesma estrutura/altura, com ou sem subtítulo.
    subtitle_html = f'<p class="kpi-subtitle">{subtitle if subtitle else "&nbsp;"}</p>'
    icone = icon if icon else _icone_automatico(title)

    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: {color}; --kpi-color: {color};">
            <div class="kpi-title-row">
                <span class="kpi-icon">{icone}</span>
                <p class="kpi-title">{title}</p>
            </div>
            <h2 class="kpi-value">{value}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
