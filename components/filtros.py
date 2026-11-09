from contextlib import nullcontext

import pandas as pd
import streamlit as st


def filtros_topo(df: pd.DataFrame, ocultar: tuple = (), mostrar_gestao: bool = False) -> pd.DataFrame:
    """
    Renderiza a barra de segmentações no topo do site (Data, Estado,
    Cluster, Cidade, Coordenador, Tipo) e retorna o DataFrame já filtrado conforme a seleção
    do usuário. Os filtros ficam disponíveis em todas as páginas, pois são
    aplicados antes do roteamento.

    Estado, Cluster, Cidade e Coordenador são multi-seleção (dá pra marcar
    mais de uma opção em cada). Cluster respeita o(s) Estado(s) já
    escolhido(s), Cidade respeita o(s) Estado(s)/Cluster(s) já escolhidos, e
    Coordenador respeita o(s) Estado(s)/Cluster(s)/Cidade(s) já escolhidos —
    cada filtro à direita vai restringindo as opções com base nos filtros já
    marcados à esquerda.

    `ocultar`: nomes de filtros a esconder nesta página (hoje só \"Cidade\" e
    \"Coordenador\" são suportados). Um filtro oculto fica sem seleção, ou seja,
    não restringe nada.

    `mostrar_gestao`: quando True, mostra uma 2ª linha com as segmentações
    Supervisor e Técnico (hoje só na aba Dashboard). Supervisor respeita
    Estado/Cluster/Cidade/Coordenador já marcados e Técnico respeita também
    o(s) Supervisor(es) marcado(s).
    """
    st.markdown("<div class='tlp-filtros'>", unsafe_allow_html=True)
    mostrar_cidade = "Cidade" not in ocultar
    mostrar_coord = "Coordenador" not in ocultar
    mostrar_tipo = "Tipo" not in ocultar and "Tipo" in df.columns
    if mostrar_cidade or mostrar_coord:
        larguras = [1, 1, 1, 1, 1.1] + ([1] if mostrar_tipo else [])
        colunas_topo = st.columns(larguras)
        col_data, col_estado, col_cluster, col_cidade, col_coordenador = colunas_topo[:5]
        col_tipo = colunas_topo[5] if mostrar_tipo else None
    else:
        larguras = [1, 1, 1] + ([1] if mostrar_tipo else [])
        colunas_topo = st.columns(larguras)
        col_data, col_estado, col_cluster = colunas_topo[:3]
        col_cidade = col_coordenador = None
        col_tipo = colunas_topo[3] if mostrar_tipo else None

    # ---------------- TOGGLE PU VIVO (global, vale para todas as páginas) ----------------
    # Fica em session_state para que qualquer card/tabela, em qualquer view,
    # saiba se deve mostrar a comparação "PU Vivo" (fórmula do Backoffice
    # Regional Sul / Vivo) ao lado do PU do nosso site, sem precisar
    # repassar esse parâmetro manualmente por todas as funções.
    st.session_state["mostrar_pu_vivo"] = st.checkbox(
        "🔁 Ver PU VIVO",
        value=st.session_state.get("mostrar_pu_vivo", False),
        help=(
            "Mostra ao lado do PU do nosso site o PU calculado no padrão do "
            "Backoffice Regional Sul (site da Vivo): soma do peso de cada "
            "atividade concluída (coluna 'Peso') ÷ técnicos que concluíram "
            "pelo menos 1 atividade no dia."
        ),
    )

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
    with (col_cidade if mostrar_cidade else nullcontext()):
        if mostrar_cidade and "Cidade" in df.columns:
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
    with (col_coordenador if mostrar_coord else nullcontext()):
        if mostrar_coord and "Coordenador" in df.columns:
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

    # ---- TIPO DE SERVIÇO (multi; coluna "Tipo" da base: DEF, INST, DS, ME, SERV...) ----
    # Não depende dos outros filtros: dá pra ver, por ex., só Instalação (INST)
    # em qualquer página. OS sem Tipo preenchido só aparecem com o filtro vazio.
    with (col_tipo if mostrar_tipo else nullcontext()):
        if mostrar_tipo:
            opcoes_tipo = sorted(df["Tipo"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())
            sel_tipo = st.multiselect("Tipo", opcoes_tipo, placeholder="Todos")
        else:
            sel_tipo = []

    # ------- SUPERVISOR e TÉCNICO (multi, só no Dashboard; cascata a partir dos filtros acima) -------
    sel_supervisor, sel_tecnico = [], []
    if mostrar_gestao and ("Supervisor" in df.columns or "Técnico" in df.columns):
        col_sup, col_tec, _, _, _ = st.columns([1, 1, 1, 1, 1.1])
        df_para_gestao = df
        if sel_estado and "Estado" in df_para_gestao.columns:
            df_para_gestao = df_para_gestao[df_para_gestao["Estado"].isin(sel_estado)]
        if sel_cluster and "Cluster" in df_para_gestao.columns:
            df_para_gestao = df_para_gestao[df_para_gestao["Cluster"].isin(sel_cluster)]
        if sel_cidade and "Cidade" in df_para_gestao.columns:
            df_para_gestao = df_para_gestao[df_para_gestao["Cidade"].isin(sel_cidade)]
        if sel_coordenador and "Coordenador" in df_para_gestao.columns:
            df_para_gestao = df_para_gestao[df_para_gestao["Coordenador"].isin(sel_coordenador)]

        with col_sup:
            if "Supervisor" in df_para_gestao.columns:
                opcoes_sup = sorted(df_para_gestao["Supervisor"].dropna().unique().tolist())
                sel_supervisor = st.multiselect("Supervisor", opcoes_sup, placeholder="Todos", key="filtro_supervisor")
        if sel_supervisor:
            df_para_gestao = df_para_gestao[df_para_gestao["Supervisor"].isin(sel_supervisor)]
        with col_tec:
            if "Técnico" in df_para_gestao.columns:
                opcoes_tec = sorted(df_para_gestao["Técnico"].dropna().unique().tolist())
                # descarta seleção antiga que saiu das opções (ex.: trocou o Supervisor)
                if "filtro_tecnico" in st.session_state:
                    st.session_state["filtro_tecnico"] = [t for t in st.session_state["filtro_tecnico"] if t in opcoes_tec]
                sel_tecnico = st.multiselect("Técnico", opcoes_tec, placeholder="Todos", key="filtro_tecnico")

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
    st.session_state["filtro_sel_tipo"] = sel_tipo
    st.session_state["filtro_sel_supervisor"] = sel_supervisor
    st.session_state["filtro_sel_tecnico"] = sel_tecnico

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

    if sel_supervisor and "Supervisor" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Supervisor"].isin(sel_supervisor)]

    if sel_tecnico and "Técnico" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Técnico"].isin(sel_tecnico)]

    if sel_tipo and "Tipo" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Tipo"].astype(str).str.strip().isin(sel_tipo)]

    return df_filtrado