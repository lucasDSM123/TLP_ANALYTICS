import pandas as pd
import streamlit as st


def filtros_topo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza a barra de segmentações no topo do site (Data, Estado,
    Cluster, Cidade) e retorna o DataFrame já filtrado conforme a seleção
    do usuário. Os filtros ficam disponíveis em todas as páginas, pois são
    aplicados antes do roteamento.

    Estado, Cluster, Cidade e Coordenador são multi-seleção (dá pra marcar
    mais de uma opção em cada). Cluster respeita o(s) Estado(s) já
    escolhido(s), Cidade respeita o(s) Estado(s)/Cluster(s) já escolhidos, e
    Coordenador respeita o(s) Estado(s)/Cluster(s)/Cidade(s) já escolhidos —
    cada filtro à direita vai restringindo as opções com base nos filtros já
    marcados à esquerda.
    """
    st.markdown("<div class='tlp-filtros'>", unsafe_allow_html=True)
    col_data, col_estado, col_cluster, col_cidade, col_coordenador = st.columns([1, 1, 1, 1, 1.1])

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

    # ------- COORDENADOR (multi, depende do(s) Estado(s)/Cluster(s)/Cidade(s)) -------
    with col_coordenador:
        if "Coordenador" in df.columns:
            df_para_coordenador = df
            if sel_estado:
                df_para_coordenador = df_para_coordenador[df_para_coordenador["Estado"].isin(sel_estado)]
            if sel_cluster:
                df_para_coordenador = df_para_coordenador[df_para_coordenador["Cluster"].isin(sel_cluster)]
            if sel_cidade:
                df_para_coordenador = df_para_coordenador[df_para_coordenador["Cidade"].isin(sel_cidade)]
            opcoes_coordenador = sorted(df_para_coordenador["Coordenador"].dropna().unique().tolist())
            sel_coordenador = st.multiselect("Coordenador", opcoes_coordenador, placeholder="Todos")
        else:
            sel_coordenador = []

    st.markdown("</div>", unsafe_allow_html=True)

    # Guarda a seleção "crua" (antes de aplicar) em session_state para que
    # outras partes do site (ex.: legenda automática do botão "Copiar
    # imagem") saibam quais Estado(s)/Data(s) estão marcados no momento,
    # sem precisar re-derivar isso a partir do DataFrame já filtrado.
    st.session_state["filtro_sel_estado"] = sel_estado
    st.session_state["filtro_sel_data"] = sel_data
    st.session_state["filtro_sel_cluster"] = sel_cluster
    st.session_state["filtro_sel_cidade"] = sel_cidade
    st.session_state["filtro_sel_coordenador"] = sel_coordenador

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

    if sel_coordenador and "Coordenador" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Coordenador"].isin(sel_coordenador)]

    return df_filtrado