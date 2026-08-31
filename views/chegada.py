import io

import pandas as pd
import streamlit as st

from components.cards import card
from components.header import secao_titulo
from components.charts import (
    grafico_status_pizza,
    grafico_ranking,
    opcoes_grafico,
)
from components.print_button import area_com_print
from components.tabelas import tabela_chegada_expansivel_3niveis
from services.loader import opcoes_filtro, aplicar_filtro
from services.indicadores import Indicadores
from services.chegada import (
    calcular_indicador_chegada,
    resumo_geral,
    resumo_por_grupo,
    resumo_hierarquico_3niveis,
    ranking_ofensores,
    tabela_detalhada,
    resumo_tempo_inicio,
    tempo_inicio_por_janela,
    mapa_tecnico_matricula,
    aplicar_matricula_nos_netos,
)
from services.termino import (
    calcular_indicador_termino,
    resumo_tempo_termino,
    tempo_termino_por_janela,
)


def render(df, indicadores: Indicadores):
    secao_titulo("Chegada", "Aderência do técnico à Janela de Serviço (horário real x agendado)")
    st.caption("⏱️ Tolerância: início até 60 min antes da Janela ou até 30 min depois da abertura ainda conta como 'Dentro'. Exclui OS Canceladas, Não Iniciadas e em rota.")

    if "Janela" not in df.columns or "Início" not in df.columns:
        st.warning("Este indicador precisa das colunas 'Janela' e 'Início' na base, que não foram encontradas.")
        return

    # ====== FILTROS ======
    # Cluster/Cidade já são cobertos pela segmentação global do topo do site,
    # então aqui fica só o filtro específico desta aba: Janela de Serviço.
    janelas = opcoes_filtro(df, "Janela")
    janela_sel = st.radio(
        "Filtrar por Janela de Serviço",
        janelas,
        horizontal=True,
        key="chg_janela",
    )

    df_filtrado = aplicar_filtro(df, "Janela", janela_sel)

    df_chegada = calcular_indicador_chegada(df_filtrado)
    resumo = resumo_geral(df_chegada)

    if resumo["total"] == 0:
        st.info("Nenhuma OS com horário de Início registrado para este filtro.")
        return

    # ====== KPIs ======
    with area_com_print(f"chegada_cards_{janela_sel}", nome_arquivo="resumo_chegada"):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            card("OS Avaliadas", f"{resumo['total']:,}".replace(",", "."), color="#2E63C7")
        with col2:
            card("Dentro da Janela", f"{resumo['dentro']:,}".replace(",", "."), color="#15803D", subtitle=f"{resumo['pct_dentro']:.1f}%")
        with col3:
            card("Fora da Janela", f"{resumo['fora']:,}".replace(",", "."), color="#C0392B", subtitle=f"{resumo['pct_fora']:.1f}%")
        with col4:
            card("Chegou Antes", f"{resumo['antes']:,}".replace(",", "."), color="#D4AC0D")
        with col5:
            card("Chegou Depois", f"{resumo['depois']:,}".replace(",", "."), color="#D4AC0D")

    if resumo["sem_registro"]:
        st.caption(f"⚠️ {resumo['sem_registro']:,} OS sem horário de Início registrado não entram nas contagens acima.".replace(",", "."))
    if resumo.get("indefinido"):
        st.caption(f"⚠️ {resumo['indefinido']:,} OS sem Janela de Serviço definida não entram nas contagens acima.".replace(",", "."))
    if resumo.get("aguardando"):
        st.caption(f"🕒 {resumo['aguardando']:,} OS de hoje com Início Real ainda no futuro (aguardando o horário real acontecer) não entram nas contagens acima.".replace(",", "."))

    st.markdown("<br>", unsafe_allow_html=True)

    # ====== GRÁFICO + RANKING ======
    col_graf, col_rank = st.columns([1, 1])

    with col_graf:
        with area_com_print(f"chegada_pizza_{janela_sel}", nome_arquivo="chegada_dentro_x_fora"):
            st.plotly_chart(
                grafico_status_pizza(
                    {"Dentro": resumo["dentro"], "Antes": resumo["antes"], "Depois": resumo["depois"]},
                    titulo="Dentro x Fora da Janela",
                ),
                width="stretch",
                config=opcoes_grafico("chegada_dentro_x_fora"),
            )

    with col_rank:
        ranking_cluster = resumo_por_grupo(df_chegada, "Cluster")
        if not ranking_cluster.empty:
            with area_com_print(f"chegada_ranking_cluster_{janela_sel}", nome_arquivo="chegada_ranking_cluster"):
                st.plotly_chart(
                    grafico_ranking(ranking_cluster, "% Dentro", "Ranking por Cluster — % Dentro da Janela"),
                    width="stretch",
                    config=opcoes_grafico("chegada_ranking_cluster"),
                )

    st.divider()

    # ====== RESUMO POR GRUPO (Por Cluster / Por Gestores) ======
    secao_titulo("Resumo por Grupo", "Aderência à janela — escolha a segmentação abaixo")

    aba_cluster, aba_gestores = st.tabs(["Por Cluster", "Por Gestores"])

    with aba_cluster:
        with area_com_print(f"chegada_matriz_cluster_{janela_sel}", nome_arquivo="chegada_por_cluster_cidade_zona"):
            dados_cluster = resumo_hierarquico_3niveis(df_chegada, "Cluster", "Cidade", "Zona")
            tabela_chegada_expansivel_3niveis(
                dados_cluster, titulo="Por Cluster", meta_pct=80.0,
                rotulo_grupo="CLUSTER / CIDADE / ZONA", rotulo_clique="Cluster",
                id_tabela="chegada_matriz_cluster",
            )

    with aba_gestores:
        mostrar_nome_tecnico = st.checkbox(
            "Mostrar nome do técnico", value=False, key="chg_mostrar_nome_tecnico",
            help="Por padrão o técnico aparece pela matrícula. Marque para exibir o nome completo.",
        )
        dados_gestores = resumo_hierarquico_3niveis(df_chegada, "Coordenador", "Supervisor", "Técnico")
        if not mostrar_nome_tecnico:
            mapa_matricula = mapa_tecnico_matricula(df_chegada)
            dados_gestores = aplicar_matricula_nos_netos(dados_gestores, mapa_matricula)
            rotulo_tecnico = "COORDENADOR / SUPERVISOR / MATRÍCULA"
        else:
            rotulo_tecnico = "COORDENADOR / SUPERVISOR / TÉCNICO"

        with area_com_print(f"chegada_matriz_gestores_{janela_sel}", nome_arquivo="chegada_por_coordenador_supervisor_tecnico"):
            tabela_chegada_expansivel_3niveis(
                dados_gestores, titulo="Por Gestores", meta_pct=80.0,
                rotulo_grupo=rotulo_tecnico, rotulo_clique="Coordenador",
                id_tabela="chegada_matriz_gestores",
            )

    st.divider()

    # ====== TEMPO ATÉ O INÍCIO DA ATIVIDADE ======
    secao_titulo(
        "Tempo até o Início da Atividade",
        "Horário em que o atendimento costuma começar e quanto tempo leva após a abertura da Janela",
    )
    st.caption(
        "⏱️ 'Tempo Médio até Início' é a diferença média entre o horário de Início e a abertura da Janela "
        "(positivo = atraso médio; negativo = começou adiantado, em média). "
        "'Horário Mais Frequente' é a moda dos horários de Início, agrupados em blocos de 15 min."
    )

    tempo_geral = resumo_tempo_inicio(df_chegada)

    if tempo_geral["total"] == 0:
        st.info("Nenhuma OS avaliável para este filtro.")
    else:
        with area_com_print(f"chegada_tempo_inicio_cards_{janela_sel}", nome_arquivo="tempo_inicio_resumo"):
            col1, col2, col3 = st.columns(3)
            with col1:
                card("Horário Médio de Início", tempo_geral["horario_medio"], color="#2E63C7")
            with col2:
                card("Horário Mais Frequente", tempo_geral["horario_frequente"], color="#7E57C2")
            with col3:
                card("Tempo Médio até Início", tempo_geral["tempo_medio_fmt"], color="#D4AC0D",
                     subtitle="vs. abertura da Janela")

        st.markdown("<br>", unsafe_allow_html=True)

        tabela_tempo_janela = tempo_inicio_por_janela(df_chegada)
        if not tabela_tempo_janela.empty:
            with area_com_print(f"chegada_tempo_inicio_tabela_{janela_sel}", nome_arquivo="tempo_inicio_tabela_por_janela"):
                st.dataframe(
                    tabela_tempo_janela.drop(columns="_tempo_medio_min"),
                    width="stretch",
                    hide_index=True,
                    height=380,
                )

    st.divider()

    # ====== TEMPO ATÉ O FIM DA EXECUÇÃO (TÉRMINO) ======
    secao_titulo(
        "Tempo até o Fim da Execução",
        "Horário em que o atendimento costuma terminar e a diferença em relação ao fechamento da Janela",
    )
    st.caption(
        "⏱️ Mesma lógica do indicador de Início, espelhada pro Término: tolerância de até 60 min antes ou "
        "30 min depois do FECHAMENTO da Janela ainda conta como 'Dentro'. "
        "'Tempo Médio até Término' é a diferença média entre o horário de Término e o fechamento da Janela "
        "(positivo = terminou depois, em média; negativo = terminou antes, em média)."
    )

    df_termino = calcular_indicador_termino(df_filtrado)
    df_termino_filtrado = df_termino

    tempo_termino_geral = resumo_tempo_termino(df_termino_filtrado)

    if "Término" not in df_filtrado.columns:
        st.warning("Este indicador precisa da coluna 'Término' na base, que não foi encontrada.")
    elif tempo_termino_geral["total"] == 0:
        st.info("Nenhuma OS avaliável para este filtro.")
    else:
        with area_com_print(f"chegada_tempo_termino_cards_{janela_sel}", nome_arquivo="tempo_termino_resumo"):
            col1, col2, col3 = st.columns(3)
            with col1:
                card("Horário Médio de Término", tempo_termino_geral["horario_medio"], color="#2E63C7")
            with col2:
                card("Horário Mais Frequente", tempo_termino_geral["horario_frequente"], color="#7E57C2")
            with col3:
                card("Tempo Médio até Término", tempo_termino_geral["tempo_medio_fmt"], color="#D4AC0D",
                     subtitle="vs. fechamento da Janela")

        st.markdown("<br>", unsafe_allow_html=True)

        tabela_termino_janela = tempo_termino_por_janela(df_termino_filtrado)
        if not tabela_termino_janela.empty:
            with area_com_print(f"chegada_tempo_termino_tabela_{janela_sel}", nome_arquivo="tempo_termino_tabela_por_janela"):
                st.dataframe(
                    tabela_termino_janela.drop(columns="_tempo_medio_min"),
                    width="stretch",
                    hide_index=True,
                    height=380,
                )

    st.divider()

    # ====== OFENSORES (TOP 10 CHEGADAS "DEPOIS", ACUMULADO) ======
    secao_titulo(
        "Ofensores — Chegadas Fora do Horário",
        "Top 10 acumulado de OS iniciadas como 'Depois' da Janela de Serviço",
    )

    col_top_tecnico, col_top_supervisor = st.columns(2)

    with col_top_tecnico:
        ranking_tecnicos = ranking_ofensores(df_chegada, "Técnico", top_n=10)
        with area_com_print(f"chegada_ofensores_tecnico_{janela_sel}", nome_arquivo="chegada_top10_tecnicos_ofensores"):
            if ranking_tecnicos.empty:
                st.info("Nenhuma chegada 'Depois' registrada para este filtro.")
            else:
                st.plotly_chart(
                    grafico_ranking(
                        ranking_tecnicos[["Técnico", "Qtd Depois"]],
                        "Qtd Depois",
                        "Top 10 Técnicos — Qtd. Chegadas Depois",
                    ),
                    width="stretch",
                    config=opcoes_grafico("chegada_top10_tecnicos_ofensores"),
                )
                st.dataframe(ranking_tecnicos, width="stretch", hide_index=True)

    with col_top_supervisor:
        ranking_supervisores = ranking_ofensores(df_chegada, "Supervisor", top_n=10)
        with area_com_print(f"chegada_ofensores_supervisor_{janela_sel}", nome_arquivo="chegada_top10_supervisores_ofensores"):
            if ranking_supervisores.empty:
                st.info("Nenhuma chegada 'Depois' registrada para este filtro.")
            else:
                st.plotly_chart(
                    grafico_ranking(
                        ranking_supervisores[["Supervisor", "Qtd Depois"]],
                        "Qtd Depois",
                        "Top 10 Supervisores — Qtd. Chegadas Depois (equipe)",
                    ),
                    width="stretch",
                    config=opcoes_grafico("chegada_top10_supervisores_ofensores"),
                )
                st.dataframe(ranking_supervisores, width="stretch", hide_index=True)

    st.divider()

    # ====== TABELA DETALHADA (nível técnico/OS) ======
    secao_titulo("Detalhamento", "Janela x Início real por OS/técnico")

    col_filtro_status, col_filtro_tecnico = st.columns([1, 1])

    with col_filtro_status:
        status_opcoes = ["Todos", "Dentro", "Fora", "Antes", "Depois", "Aguardando"]
        status_sel = st.selectbox("Filtrar por status de chegada", status_opcoes, key="chg_status")

    detalhe = tabela_detalhada(df_chegada)

    with col_filtro_tecnico:
        tecnicos_opcoes = opcoes_filtro(detalhe, "Técnico")
        tecnico_sel = st.selectbox("Filtrar por técnico", tecnicos_opcoes, key="chg_tecnico")

    if status_sel == "Fora":
        detalhe = detalhe[detalhe["Status Chegada"].isin(["Antes", "Depois"])]
    elif status_sel != "Todos":
        detalhe = detalhe[detalhe["Status Chegada"] == status_sel]

    detalhe = aplicar_filtro(detalhe, "Técnico", tecnico_sel)

    st.dataframe(detalhe, width="stretch", hide_index=True, height=460)

    # Exportação em Excel respeitando os filtros aplicados (segmentação
    # global do topo do site + Janela de Serviço + status de chegada e
    # técnico selecionados nesta aba).
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        detalhe.to_excel(writer, index=False, sheet_name="Detalhamento Chegada")

    nome_arquivo_status = status_sel.lower() if status_sel != "Todos" else "todos"
    st.download_button(
        "⬇️ Baixar Excel filtrado",
        data=buffer.getvalue(),
        file_name=f"tlp_chegada_detalhamento_{nome_arquivo_status}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="chg_download_excel",
    )
