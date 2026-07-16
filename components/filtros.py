import pandas as pd
import streamlit as st


def filtros_topo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza a barra de segmentações no topo do site (Data, Estado,
    Contratada, Cluster) e retorna o DataFrame já filtrado conforme a
    seleção do usuário. Os filtros ficam disponíveis em todas as páginas,
    pois são aplicados antes do roteamento.
    """
    st.markdown("<div class='tlp-filtros'>", unsafe_allow_html=True)
    col_data, col_estado, col_contratada, col_cluster = st.columns([1.2, 1, 1.6, 1.2])

    # ---------------- DATA (multi) ----------------
    with col_data:
        if "Data" in df.columns:
            datas_validas = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True).dropna()
            if not datas_validas.empty:
                opcoes_data = [d.strftime("%d/%m/%Y") for d in sorted(datas_validas.dt.date.unique(), reverse=True)]
                sel_data = st.multiselect("Data", opcoes_data, placeholder="Todas")
            else:
                sel_data = []
        else:
            sel_data = []

    # ---------------- ESTADO ----------------
    with col_estado:
        if "Estado" in df.columns:
            opcoes_estado = sorted(df["Estado"].dropna().unique().tolist())
            sel_estado = st.selectbox("Estado", ["Todos"] + opcoes_estado)
        else:
            sel_estado = "Todos"

    # ---------------- CONTRATADA (multi) ----------------
    with col_contratada:
        if "Contratada" in df.columns:
            opcoes_contratada = sorted(df["Contratada"].dropna().unique().tolist())
            sel_contratada = st.multiselect("Contratada", opcoes_contratada, placeholder="Todas")
        else:
            sel_contratada = []

    # ---------------- CLUSTER (depende do Estado selecionado) ----------------
    with col_cluster:
        if "Cluster" in df.columns:
            df_para_cluster = df if sel_estado == "Todos" else df[df["Estado"] == sel_estado]
            opcoes_cluster = sorted(df_para_cluster["Cluster"].dropna().unique().tolist())
            sel_cluster = st.selectbox("Cluster", ["Todos"] + opcoes_cluster)
        else:
            sel_cluster = "Todos"

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- APLICAÇÃO DOS FILTROS ----------------
    df_filtrado = df.copy()

    if sel_data and "Data" in df_filtrado.columns:
        datas_col = pd.to_datetime(df_filtrado["Data"], errors="coerce", dayfirst=True)
        df_filtrado = df_filtrado[datas_col.dt.strftime("%d/%m/%Y").isin(sel_data)]

    if sel_estado != "Todos" and "Estado" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Estado"] == sel_estado]

    if sel_contratada and "Contratada" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Contratada"].isin(sel_contratada)]

    if sel_cluster != "Todos" and "Cluster" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Cluster"] == sel_cluster]

    return df_filtrado