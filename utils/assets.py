"""
Utilitários para carregar assets estáticos (imagens) e injetá-los via CSS.
O Streamlit não serve arquivos locais por URL por padrão, então convertemos
para base64 e embutimos como data URI no CSS.
"""
from pathlib import Path
import base64

import streamlit as st


@st.cache_data(show_spinner=False)
def imagem_para_base64(caminho: str) -> str:
    """Lê um arquivo de imagem do disco e retorna a string base64 (cacheada)."""
    dados = Path(caminho).read_bytes()
    return base64.b64encode(dados).decode()


def imagem_como_data_uri(caminho: str) -> str:
    """Retorna a imagem como data:image/...;base64,... pronta para uso em CSS/HTML."""
    ext = Path(caminho).suffix.replace(".", "") or "png"
    if ext == "svg":
        mime = "image/svg+xml"
    else:
        mime = f"image/{ext}"
    return f"data:{mime};base64,{imagem_para_base64(caminho)}"
