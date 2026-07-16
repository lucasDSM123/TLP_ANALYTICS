import io

import pandas as pd
import streamlit as st

from components.header import secao_titulo
from services.loader import opcoes_filtro, aplicar_filtro

COLUNAS_PADRAO = [
    "Ordem de Serviço", "Técnico", "Cidade", "Estado", "Supervisor", "Coordenador",
    "Tipo de Atividade", "Status", "Lado", "Perfil Técnico", "Contratada", "Data",
]


def render(df, indicadores):
    secao_titulo("Relatórios", "Explore e exporte os dados filtrados")

    col1, col2, col3 = st.columns(3)
    with col1:
        coord_sel = st.selectbox("Coordenador", opcoes_filtro(df, "Coordenador"), key="rel_coord")
    with col2:
        status_sel = st.selectbox("Status", opcoes_filtro(df, "Status"), key="rel_status")
    with col3:
        lado_sel = st.selectbox("Lado", opcoes_filtro(df, "Lado"), key="rel_lado")

    df_filtrado = df.copy()
    df_filtrado = aplicar_filtro(df_filtrado, "Coordenador", coord_sel)
    df_filtrado = aplicar_filtro(df_filtrado, "Status", status_sel)
    df_filtrado = aplicar_filtro(df_filtrado, "Lado", lado_sel)

    colunas_disponiveis = [c for c in COLUNAS_PADRAO if c in df_filtrado.columns]
    colunas_sel = st.multiselect(
        "Colunas a exibir",
        options=list(df_filtrado.columns),
        default=colunas_disponiveis,
    )

    if not colunas_sel:
        colunas_sel = colunas_disponiveis

    st.divider()

    # ====== FILTRO POR VALOR DAS COLUNAS SELECIONADAS ======
    secao_titulo("Filtrar por coluna", "Escolha uma ou mais colunas exibidas e selecione os valores que deseja manter")

    colunas_filtro = st.multiselect(
        "Colunas para aplicar filtro de valores",
        options=colunas_sel,
        key="rel_colunas_filtro",
    )

    for coluna in colunas_filtro:
        valores_disponiveis = sorted(
            v for v in df_filtrado[coluna].dropna().unique().tolist()
        )
        valores_sel = st.multiselect(
            f"Valores de \"{coluna}\"",
            options=valores_disponiveis,
            key=f"rel_valor_{coluna}",
        )
        if valores_sel:
            df_filtrado = df_filtrado[df_filtrado[coluna].isin(valores_sel)]

    st.divider()

    st.markdown(f"**{len(df_filtrado):,}** registros encontrados".replace(",", "."))

    st.dataframe(df_filtrado[colunas_sel], width='stretch', hide_index=True, height=460)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtrado[colunas_sel].to_excel(writer, index=False, sheet_name="Relatório")

    st.download_button(
        "⬇️ Baixar Excel filtrado",
        data=buffer.getvalue(),
        file_name="tlp_relatorio_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
