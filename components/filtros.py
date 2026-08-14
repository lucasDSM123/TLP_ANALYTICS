import pandas as pd
import streamlit as st


def filtros_topo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza a barra de segmentações no topo do site (Data, Estado,
    Cluster, Cidade) e retorna o DataFrame já filtrado conforme a seleção
    do usuário. Os filtros ficam disponíveis em todas as páginas, pois são
    aplicados antes do roteamento.

    Estado, Cluster e Cidade são multi-seleção (dá pra marcar mais de uma
    opção em cada). Cluster respeita o(s) Estado(s) já escolhido(s), e
    Cidade respeita o(s) Estado(s)/Cluster(s) já escolhidos — do mesmo
    jeito que o Cluster já dependia do Estado antes.
    """
    st.markdown("<div class='tlp-filtros'>", unsafe_allow_html=True)
    col_data, col_estado, col_cluster, col_cidade = st.columns([1.1, 1, 1.1, 1.1])

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

    # ---------------- ESTADO (multi) ----------------
    with col_estado:
        if "Estado" in df.columns:
            opcoes_estado = sorted(df["Estado"].dropna().unique().tolist())
            sel_estado = st.multiselect("Estado", opcoes_estado, placeholder="Todos")
        else:
            sel_estado = []

    # ---------------- CLUSTER (multi, depende do(s) Estado(s)) ----------------
    with col_cluster:
        if "Cluster" in df.columns:
            df_para_cluster = df if not sel_estado else df[df["Estado"].isin(sel_estado)]
            opcoes_cluster = sorted(df_para_cluster["Cluster"].dropna().unique().tolist())
            sel_cluster = st.multiselect("Cluster", opcoes_cluster, placeholder="Todos")
        else:
            sel_cluster = []

    # ---------------- CIDADE (multi, depende do(s) Estado(s)/Cluster(s)) ----------------
    with col_cidade:
        if "Cidade" in df.columns:
            df_para_cidade = df
            if sel_estado:
                df_para_cidade = df_para_cidade[df_para_cidade["Estado"].isin(sel_estado)]
            if sel_cluster:
                df_para_cidade = df_para_cidade[df_para_cidade["Cluster"].isin(sel_cluster)]
            opcoes_cidade = sorted(df_para_cidade["Cidade"].dropna().unique().tolist())
            sel_cidade = st.multiselect("Cidade", opcoes_cidade, placeholder="Todas")
        else:
            sel_cidade = []

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- APLICAÇÃO DOS FILTROS ----------------
    df_filtrado = df.copy()

    if sel_data and "Data" in df_filtrado.columns:
        datas_col = pd.to_datetime(df_filtrado["Data"], errors="coerce", dayfirst=True)
        df_filtrado = df_filtrado[datas_col.dt.strftime("%d/%m/%Y").isin(sel_data)]

    if sel_estado and "Estado" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Estado"].isin(sel_estado)]

    if sel_cluster and "Cluster" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Cluster"].isin(sel_cluster)]

    if sel_cidade and "Cidade" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Cidade"].isin(sel_cidade)]

    return df_filtrado