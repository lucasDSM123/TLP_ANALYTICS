import streamlit as st

from components.header import secao_titulo


def render(df, indicadores):
    secao_titulo("Configurações", "Informações e manutenção da base de dados")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Total de registros", f"{len(df):,}".replace(",", "."), disabled=True)
        st.text_input("Total de colunas", len(df.columns), disabled=True)
    with col2:
        st.text_input("Coordenadores", df["Coordenador"].nunique() if "Coordenador" in df.columns else "-", disabled=True)
        st.text_input("Cidades", df["Cidade"].nunique() if "Cidade" in df.columns else "-", disabled=True)

    st.divider()

    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

    with st.expander("Colunas disponíveis na base"):
        st.write(list(df.columns))
