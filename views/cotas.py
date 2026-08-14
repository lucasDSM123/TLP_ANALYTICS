import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.print_button import area_com_print
from components.tabelas_cotas import tabela_detalhe_cidade, tabela_distribuicao_turno, tabela_matriz_agendada
from services.cotas import (
    carregar_base_cotas,
    carregar_base_cotas_minutos,
    dias_disponiveis,
    filtrar_cotas_por_segmentacao_global,
    formatar_data_br,
    matriz_agendada_slot,
    resumo_cards,
    resumo_cluster_cidade,
    resumo_horario_cidade,
    resumo_turno,
)


def render(df, indicadores):
    secao_titulo("Cotas", "Cota x Real por turno, cluster e cidade — janela de 7 dias (hoje + 6)")

    # ------------------------------------------------------------
    # Modo: Atividades (número de atividades) ou Minutos (capacidade em
    # minutos abertos/usados) — mesmo dado, duas unidades de medida. As
    # duas bases têm exatamente o mesmo formato (Cluster, Cidade, Data,
    # Atividade, Horário, Cota, Real, GAP), então todo o resto da página
    # (cards, distribuição por turno, árvore Cluster > Cidade, matriz
    # %Agendada) funciona sem mudar nada — só troca a fonte dos dados.
    # ------------------------------------------------------------
    modo = st.radio("Modo", ["Atividades", "Minutos"], horizontal=True, key="cotas_modo")

    if modo == "Minutos":
        df_cotas = carregar_base_cotas_minutos()
        aba_esperada, nome_arquivo_erro = "Todas_Cidades", "`Todas_Cidades`"
    else:
        df_cotas = carregar_base_cotas()
        aba_esperada, nome_arquivo_erro = "Cotas", "`Cotas`"

    if df_cotas.empty:
        st.warning(
            f"Nenhuma base de Cotas encontrada em `data/` (arquivo `Cota_Cidades*.xlsx`, aba {nome_arquivo_erro}). "
            "Rode o `cota.py` e coloque o Excel gerado nessa pasta."
        )
        return

    # ------------------------------------------------------------
    # Respeita a segmentação global do topo do site (Estado, Cluster,
    # Cidade — a Data fica de fora, pois o seletor de Dia abaixo já cobre
    # isso). A base de Cotas não tem essas mesmas colunas prontas, então o
    # cruzamento é por nome normalizado — ver services/cotas.py.
    # ------------------------------------------------------------
    total_antes_segmentacao = len(df_cotas)
    df_cotas = filtrar_cotas_por_segmentacao_global(df_cotas, df)

    if df_cotas.empty:
        if total_antes_segmentacao:
            st.info(
                "Nenhuma cota encontrada para a segmentação de Estado/Cluster/Cidade selecionada no topo do site. "
                "Ajuste os filtros ali em cima para ver os dados de Cotas."
            )
        return

    # ------------------------------------------------------------
    # Filtro de dia (D0, D1, D2... — igual ao seletor do site de referência)
    # ------------------------------------------------------------
    dias = dias_disponiveis(df_cotas)
    rotulos_dias = {d: f"D{i}" for i, d in enumerate(dias)}
    dia_sel = st.radio(
        "Dia",
        dias,
        format_func=lambda d: f"{rotulos_dias.get(d, d)} — {formatar_data_br(d)}",
        horizontal=True,
        key="cotas_dia",
    )

    df_dia = df_cotas[df_cotas["Data"] == dia_sel]

    # Rótulos mudam de unidade conforme o modo (nº de atividades x minutos),
    # o resto do fluxo (cálculo, tabelas, cores) é idêntico nos dois modos.
    eh_minutos = modo == "Minutos"
    unidade = "min" if eh_minutos else ""
    rotulo_aberta = "Minutos Abertos" if eh_minutos else "Cotas Abertas"
    rotulo_atribuida = "Minutos Usados" if eh_minutos else "Cotas Atribuídas"
    rotulo_delta = "Delta (min)" if eh_minutos else "Delta (GAP)"
    sufixo_chave = "_min" if eh_minutos else ""

    # ------------------------------------------------------------
    # Cards resumo do dia (mesmo componente card() usado nas outras abas)
    # ------------------------------------------------------------
    cards = resumo_cards(df_dia)
    with area_com_print(f"cotas_cards_{dia_sel}{sufixo_chave}", nome_arquivo=f"resumo_cotas_{dia_sel}{sufixo_chave}"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            valor = f"{cards['Cota']:,}".replace(",", ".") + (f" {unidade}" if unidade else "")
            card(rotulo_aberta, valor, config.TLP_ORANGE, icon="🗂️")
        with col2:
            valor = f"{cards['Real']:,}".replace(",", ".") + (f" {unidade}" if unidade else "")
            card(rotulo_atribuida, valor, "#00C9A7", icon="✅")
        with col3:
            cor_delta = config.TLP_RED if cards["GAP"] < 0 else "#15803D"
            valor = f"{cards['GAP']:+,}".replace(",", ".") + (f" {unidade}" if unidade else "")
            card(rotulo_delta, valor, cor_delta, icon="📉" if cards["GAP"] < 0 else "📈")
        with col4:
            card("% Agendada", f"{cards['%Agendada'] * 100:.1f}%", config.TLP_GOLD, icon="🎯")

    st.divider()

    # ------------------------------------------------------------
    # Distribuição por Turno (Ativ. + Gap por horário e atividade)
    # ------------------------------------------------------------
    subtitulo_turno = (
        "Minutos usados e Gap por horário e atividade" if eh_minutos else "Atividades atribuídas (Real) e Gap por horário"
    )
    secao_titulo("Distribuição por Turno", subtitulo_turno)

    pivot_cota, pivot_real, pivot_gap = resumo_turno(df_dia)

    with area_com_print(f"cotas_turno_{dia_sel}{sufixo_chave}", nome_arquivo=f"distribuicao_turno_{dia_sel}{sufixo_chave}"):
        tabela_distribuicao_turno(pivot_cota, pivot_real, pivot_gap)

    st.divider()

    # ------------------------------------------------------------
    # Cotas por Cluster / Cidade (árvore expansível) + matriz %Agendada
    # ------------------------------------------------------------
    secao_titulo("Cotas por Cluster e Cidade", "Expanda um cluster para ver o detalhe por cidade")

    por_cluster, por_cidade = resumo_cluster_cidade(df_dia)
    horario_cidade = resumo_horario_cidade(df_dia)
    matriz_cluster = matriz_agendada_slot(df_dia, nivel="Cluster")

    col_esq, col_dir = st.columns([1, 1.3])

    with col_esq:
        st.caption("MINUTOS" if eh_minutos else "COTAS")
        if por_cluster.empty:
            st.info("Sem dados de cluster para este dia.")
        else:
            with area_com_print(f"cotas_arvore_{dia_sel}{sufixo_chave}", nome_arquivo=f"cotas_cluster_cidade_{dia_sel}{sufixo_chave}"):
                for _, linha in por_cluster.iterrows():
                    cluster_nome = linha["Cluster"]
                    rotulo = (
                        f"**{cluster_nome}** · Abertas {int(linha['Cotas Abertas'])} · "
                        f"Atribuídas {int(linha['Cotas Atribuídas'])} · "
                        f"Delta {int(linha['Delta']):+d} · {linha['%Agendada'] * 100:.1f}%"
                    )
                    with st.expander(rotulo):
                        cidades_cluster = (
                            por_cidade[por_cidade["Cluster"] == cluster_nome]
                            .drop(columns=["Cluster"])
                            .sort_values("Cidade")
                        )
                        horarios_cluster = horario_cidade[horario_cidade["Cluster"] == cluster_nome]

                        # Monta uma tabela só, com 2 níveis: a linha "Total" da
                        # cidade (negrito) seguida das linhas de cada Time
                        # Slot dela (indentada) — o mesmo drill-down da imagem
                        # de referência, sem precisar de expander aninhado
                        # (Streamlit não permite expander dentro de expander).
                        index_tuplas, linhas = [], []
                        for _, linha_cidade in cidades_cluster.iterrows():
                            cidade_nome = linha_cidade["Cidade"]
                            index_tuplas.append((cidade_nome, "Total"))
                            linhas.append(
                                {
                                    "Cotas Abertas": linha_cidade["Cotas Abertas"],
                                    "Cotas Atribuídas": linha_cidade["Cotas Atribuídas"],
                                    "Delta": linha_cidade["Delta"],
                                    "%Agendada": linha_cidade["%Agendada"],
                                }
                            )
                            detalhe = horarios_cluster[horarios_cluster["Cidade"] == cidade_nome]
                            for _, linha_horario in detalhe.iterrows():
                                index_tuplas.append((cidade_nome, linha_horario["Horário"]))
                                linhas.append(
                                    {
                                        "Cotas Abertas": linha_horario["Cota"],
                                        "Cotas Atribuídas": linha_horario["Real"],
                                        "Delta": linha_horario["Delta"],
                                        "%Agendada": linha_horario["%Agendada"],
                                    }
                                )

                        tabela_detalhe = pd.DataFrame(
                            linhas,
                            index=pd.MultiIndex.from_tuples(index_tuplas, names=["Cidade", "Time Slot"]),
                        )
                        tabela_detalhe_cidade(tabela_detalhe)

    with col_dir:
        st.caption("% AGENDADA POR SLOT (MINUTOS)" if eh_minutos else "% AGENDADA POR SLOT")
        if matriz_cluster.empty:
            st.info("Sem dados para a matriz de %Agendada.")
        else:
            matriz_total = matriz_agendada_slot(df_dia.assign(**{"__total__": "TOTAL"}), nivel="__total__")
            linha_total = matriz_total.loc["TOTAL"] if "TOTAL" in matriz_total.index else None

            with area_com_print(f"cotas_matriz_{dia_sel}{sufixo_chave}", nome_arquivo=f"matriz_agendada_{dia_sel}{sufixo_chave}"):
                tabela_matriz_agendada(matriz_cluster, linha_total=linha_total, nome_linha="Cluster")
