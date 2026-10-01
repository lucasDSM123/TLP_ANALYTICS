import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.header import secao_titulo
from components.charts import (
    grafico_eficacia_diaria, grafico_produtividade_diaria, cabecalho_grafico_combo, opcoes_grafico,
)
from components.tabelas import tabela_fechamento_diario, tabela_consolidado_grupo, tabela_comparativo_mensal
from components.print_button import area_com_print, sanitizar_chave
from services.grupos import serie_diaria_por_grupo, resumo_mes_por_grupo, resumo_mes_total, _linha_resumo_soma
from services import historico_mensal
from services.loader import carregar_base
from services.chegada import (
    calcular_indicador_chegada, resumo_geral as resumo_geral_chegada, percentual_dentro_por_grupo,
    serie_diaria_percentual_dentro,
)

# Dimensões disponíveis para o fechamento mensal — rótulo exibido -> nome da coluna no df
DIMENSOES = {"Estado": "Estado", "Cluster": "Cluster", "Supervisor": "Supervisor"}

_MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO",
}


def _rotulo_mes_atual(df_dia_grupo: pd.DataFrame) -> str:
    """Nome do mês corrente (em maiúsculas) com base na data mais recente
    presente na série diária do grupo — usado como cabeçalho da coluna
    'mês atual' na tabela comparativa."""
    if df_dia_grupo.empty or "Data" not in df_dia_grupo.columns:
        return "MÊS ATUAL"
    try:
        return _MESES_PT.get(df_dia_grupo["Data"].max().month, "MÊS ATUAL")
    except AttributeError:
        return "MÊS ATUAL"


def _linha_total_para_comparativo(linha_total: dict) -> dict:
    """Converte a linha de total (chaves em PT-BR, como vem de
    resumo_mes_por_grupo/_linha_resumo_soma) para o formato de chaves
    usado em services.historico_mensal (minúsculas/sem acento), permitindo
    comparar o mês corrente (calculado ao vivo) com o mês anterior
    (congelado)."""
    return {
        "eficacia": linha_total.get("Eficácia"),
        "concluida": linha_total.get("Concluída"),
        "improdutiva": linha_total.get("Improdutiva"),
        "tecnicos": linha_total.get("Técnicos"),
        "atribuicao": linha_total.get("Atribuição"),
        "pu": linha_total.get("PU"),
    }


def _com_total_mes(df_dia: pd.DataFrame, linha_total: dict, coluna_grupo: str) -> pd.DataFrame:
    """Anexa a linha 'Total Mês' (vinda de resumo_mes_por_grupo) ao final
    da série diária de um grupo, no formato esperado por tabela_fechamento_diario."""
    if df_dia.empty:
        return df_dia
    total = {"Data": "Total Mês"}
    total.update({k: v for k, v in linha_total.items() if k != coluna_grupo})
    return pd.concat([df_dia, pd.DataFrame([total])], ignore_index=True)


def _cor_grupo(indice: int, valor: str, coluna_grupo: str) -> str:
    """Cor do grupo: fixa (marca) para Estado, cíclica na paleta do site para outras dimensões (ex.: Cluster)."""
    if coluna_grupo == "Estado":
        return "#00C9A7" if valor == "SC" else config.TLP_ORANGE
    return config.CHART_COLORWAY[indice % len(config.CHART_COLORWAY)]


_COLS_ANTERIOR = ["Concluída", "Improdutiva", "Técnicos", "Atribuição", "PU", "Eficácia"]


def _anexar_mes_anterior(df_dia_grupo: pd.DataFrame, linha_total: dict, grupo: str,
                         coluna_grupo: str, diario_base=None):
    """Anexa ao fechamento diário do grupo as colunas 'Ant ...' com o MESMO DIA
    do mês anterior (dia 1 com dia 1, dia 2 com dia 2...), e à linha de total o
    acumulado do mês anterior ATÉ O MESMO DIA (dias 1..N, onde N é o último dia
    do mês atual) — assim o Total Mês compara período com período.

    Fonte: fechamento diário congelado (services/historico_diario). Se o mês
    anterior ainda não foi congelado, usa `diario_base()` (callable que devolve
    a série diária calculada da base, se o mês anterior ainda estiver no banco).
    Sem nenhuma das duas, devolve tudo como veio (a tabela fica sem o bloco).
    Retorna (df_dia_grupo, linha_total, rotulo_mes_anterior)."""
    if df_dia_grupo.empty:
        return df_dia_grupo, linha_total, ""

    data_ref = df_dia_grupo["Data"].max()
    ant = historico_mensal.fechamento_diario_mes_anterior(grupo, coluna_grupo, data_referencia=data_ref)
    rotulo = historico_mensal.rotulo_mes_anterior(data_ref)

    if (ant is None or ant.empty) and diario_base is not None:
        serie = diario_base()
        if serie is not None and not serie.empty:
            sub = serie[serie[coluna_grupo] == grupo]
            if not sub.empty:
                ant = sub.assign(_dia=sub["Data"].apply(lambda d: d.day)).set_index("_dia").sort_index()
                mes_ant = 12 if data_ref.month == 1 else data_ref.month - 1
                rotulo = _MESES_PT[mes_ant]

    if ant is None or ant.empty:
        return df_dia_grupo, linha_total, ""

    dias = df_dia_grupo["Data"].apply(lambda d: d.day)
    df_dia_grupo = df_dia_grupo.copy()
    for coluna in _COLS_ANTERIOR:
        df_dia_grupo[f"Ant {coluna}"] = dias.map(ant[coluna])

    total_ant = _linha_resumo_soma(grupo, coluna_grupo, ant[ant.index <= dias.max()])
    linha_total = dict(linha_total)
    for coluna in _COLS_ANTERIOR:
        linha_total[f"Ant {coluna}"] = total_ant[coluna]
    return df_dia_grupo, linha_total, rotulo


def _datas(serie: pd.Series) -> pd.Series:
    """Converte a coluna Data (texto dd/mm/aa) em datetime."""
    datas = pd.to_datetime(serie, format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return datas


def _meses_disponiveis(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Lista de (ano, mês) presentes na base, do mais recente ao mais antigo."""
    if df.empty or "Data" not in df.columns:
        return []
    datas = _datas(df["Data"]).dropna()
    meses = {(d.year, d.month) for d in datas}
    return sorted(meses, reverse=True)


def _filtrar_mes(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    """Mantém só as linhas do mês/ano informado."""
    if df.empty or "Data" not in df.columns:
        return df
    datas = _datas(df["Data"])
    return df[(datas.dt.year == ano) & (datas.dt.month == mes)]


def _base_mes_anterior(ano: int, mes: int) -> pd.DataFrame:
    """Base completa do mês anterior a (ano, mês), vinda do banco, com os
    mesmos filtros de Estado/Cluster/Cidade/Coordenador marcados no topo
    (o filtro de Data não se aplica: aqui queremos o mês fechado inteiro).
    Usada na comparação de Supervisor, que não tem fechamento congelado."""
    base = carregar_base()
    if base is None or base.empty:
        return pd.DataFrame()
    for coluna, chave in (("Estado", "filtro_sel_estado"), ("Cluster", "filtro_sel_cluster"),
                          ("Cidade", "filtro_sel_cidade"), ("Coordenador", "filtro_sel_coordenador")):
        selecao = st.session_state.get(chave) or []
        if selecao and coluna in base.columns:
            base = base[base[coluna].isin(selecao)]
    ano_ant, mes_ant = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return _filtrar_mes(base, ano_ant, mes_ant)


def render(df, indicadores):

    secao_titulo("Acumulado Mês", "Fechamento mensal consolidado — réplica do PAINEL do Excel/Power BI")

    # Seletor de mês: a base pode conter mais de um mês (ex.: Setembro
    # inteiro + 01/10). Por padrão mostra o mês mais recente; dá pra
    # escolher um mês anterior para ver o fechamento diário dele.
    meses = _meses_disponiveis(df)
    if meses:
        rotulos_meses = {m: f"{_MESES_PT[m[1]].capitalize()}/{m[0]}" for m in meses}
        mes_sel = st.radio(
            "Mês", options=meses, format_func=lambda m: rotulos_meses[m],
            horizontal=True, key="acumulado_mes_mes",
        )
        df = _filtrar_mes(df, *mes_sel)
        indicadores = indicadores.__class__(df)
    else:
        mes_sel = None

    # ====== RESUMO GERAL DO PERÍODO FILTRADO ======
    hc = indicadores.hc_real()
    concluido = indicadores.concluido()
    eficacia = indicadores.eficacia()

    # PU e Atribuição do resumo geral seguem a MESMA regra do Total das
    # tabelas abaixo (soma da Concluída/Caixa Total/Técnicos de cada dia e
    # só então divide) — NÃO usar indicadores.pu()/media_atribuicao() direto
    # aqui, pois eles contam Técnicos como únicos do período inteiro (um
    # número bem menor que a soma diária), o que inflava o PU exibido no
    # card muito acima do valor real (visto na matriz/Total logo abaixo).
    total_geral = resumo_mes_total(df) or {}
    pu_geral = total_geral.get("PU", 0.0)
    atribuicao_geral = total_geral.get("Atribuição", 0.0)

    # Acumulado do indicador de Chegada (% Dentro da Janela) no período
    # filtrado — mesma lógica/tolerâncias já usadas na aba "Chegada"
    # (services.chegada), só que aqui aparece como resumo acumulado do mês.
    pct_chegada_geral = None
    if "Janela" in df.columns and "Início" in df.columns:
        resumo_chegada_geral = resumo_geral_chegada(calcular_indicador_chegada(df))
        if resumo_chegada_geral["total"]:
            pct_chegada_geral = resumo_chegada_geral["pct_dentro"]

    with area_com_print("acumulado_mes_cards_resumo", nome_arquivo="resumo_geral_acumulado_mes"):
        colunas_cards = st.columns(7 if pct_chegada_geral is not None else 6)
        col1, col2, col3, col4, col5, col6 = colunas_cards[:6]
        with col1:
            card("TÉCNICOS", hc["HC"], config.TLP_ORANGE, f"BA: {hc['BA']} | TT: {hc['TT']}")
        with col2:
            card("CONCLUÍDA", f"{concluido['OK']:,}".replace(",", "."), "#15803D")
        with col3:
            card("IMPRODUTIVA", f"{concluido['NOK']:,}".replace(",", "."), config.TLP_RED)
        with col4:
            card("EFICÁCIA", f"{eficacia['GERAL']:.0%}", config.TLP_GOLD, f"Meta: {config.META_EFICACIA_ALVO:.0%}")
        with col5:
            card("ATRIBUIÇÃO", f"{atribuicao_geral:.2f}", "#7B8CDE", f"Meta: {config.META_ATRIBUICAO_ALVO:.1f}")
        with col6:
            card("PU", f"{pu_geral:.2f}", "#00C9A7", f"Meta: {config.META_PU_ALVO:.1f}")
        if pct_chegada_geral is not None:
            with colunas_cards[6]:
                card("% CHEGADA", f"{pct_chegada_geral:.1f}%", "#2E63C7", "Dentro da Janela")

    st.divider()

    # ====== SELETOR DE DIMENSÃO (Estado ou Cluster) ======
    dimensoes_disponiveis = {rotulo: col for rotulo, col in DIMENSOES.items() if col in df.columns}

    if not dimensoes_disponiveis:
        st.info("Nenhuma coluna de agrupamento (Estado/Cluster) disponível na base filtrada.")
        return

    rotulo_dim = st.radio(
        "Agrupar fechamento por",
        options=list(dimensoes_disponiveis.keys()),
        horizontal=True,
        key="acumulado_mes_dimensao",
    )
    coluna_grupo = dimensoes_disponiveis[rotulo_dim]

    st.divider()

    # ====== CONSOLIDADO POR GRUPO (Estado ou Cluster) ======
    secao_titulo(f"Consolidado por {rotulo_dim}", f"Totais acumulados do mês — cada {rotulo_dim.lower()} e o Total geral")
    resumo_grupo = resumo_mes_por_grupo(df, coluna_grupo)

    # Anexa o acumulado do indicador de Chegada (% Dentro da Janela) como
    # coluna extra, quebrado pela mesma dimensão (Estado/Cluster/Supervisor)
    # — não entra na tabela se a base não tiver Janela/Início.
    mapa_chegada = percentual_dentro_por_grupo(df, coluna_grupo)
    if mapa_chegada and not resumo_grupo.empty:
        resumo_grupo["% Chegada"] = resumo_grupo[coluna_grupo].map(mapa_chegada)

    with area_com_print("acumulado_mes_consolidado", nome_arquivo=f"consolidado_por_{coluna_grupo}"):
        tabela_consolidado_grupo(resumo_grupo, f"TOTAL DO MÊS POR {rotulo_dim.upper()}", coluna_grupo)

    st.divider()

    # ====== FECHAMENTO DIÁRIO DETALHADO POR GRUPO ======
    secao_titulo("Fechamento Diário", f"Detalhamento dia a dia por {rotulo_dim.lower()}, com o total do mês ao final")

    serie_grupo = serie_diaria_por_grupo(df, coluna_grupo)
    serie_chegada_grupo = serie_diaria_percentual_dentro(df, coluna_grupo)

    if resumo_grupo.empty or serie_grupo.empty:
        st.info("Sem dados para os filtros selecionados.")
    else:
        # Comparativo de Supervisor: fechamento do mês anterior calculado da base.
        resumo_anterior, rotulo_mes_anterior_base = None, ""
        if coluna_grupo == "Supervisor" and mes_sel:
            base_ant = _base_mes_anterior(*mes_sel)
            if not base_ant.empty and coluna_grupo in base_ant.columns:
                resumo_anterior = resumo_mes_por_grupo(base_ant, coluna_grupo)
                mes_ant_num = 12 if mes_sel[1] == 1 else mes_sel[1] - 1
                rotulo_mes_anterior_base = _MESES_PT[mes_ant_num]

        # Fallback do diário do mês anterior (só se ele NÃO estiver congelado e
        # ainda estiver no banco) — calculado uma única vez, sob demanda.
        _cache_diario_base = {}

        def _diario_base():
            if "serie" not in _cache_diario_base:
                base_ant = _base_mes_anterior(*mes_sel) if mes_sel else pd.DataFrame()
                ok = not base_ant.empty and coluna_grupo in base_ant.columns
                _cache_diario_base["serie"] = serie_diaria_por_grupo(base_ant, coluna_grupo) if ok else pd.DataFrame()
            return _cache_diario_base["serie"]

        grupos = [g for g in resumo_grupo[coluna_grupo] if g != "Total"]
        abas = st.tabs(grupos) if grupos else []

        for i, (aba, grupo) in enumerate(zip(abas, grupos)):
            with aba:
                df_dia_grupo = (
                    serie_grupo[serie_grupo[coluna_grupo] == grupo]
                    .drop(columns=[coluna_grupo])
                    .sort_values("Data")
                )

                # Anexa o % Chegada (indicador de Chegada) dia a dia, quando
                # disponível — mesma junção por Data usada no restante da
                # tabela; dias sem OS avaliável na Chegada ficam com "—".
                if not serie_chegada_grupo.empty:
                    df_dia_grupo = df_dia_grupo.merge(
                        serie_chegada_grupo[serie_chegada_grupo[coluna_grupo] == grupo][["Data", "% Chegada"]],
                        on="Data", how="left",
                    )

                linha_total = resumo_grupo[resumo_grupo[coluna_grupo] == grupo].iloc[0].to_dict()
                if mapa_chegada:
                    linha_total["% Chegada"] = mapa_chegada.get(grupo)
                cor = _cor_grupo(i, grupo, coluna_grupo)

                # Mesmo dia do mês anterior ao lado de cada dia (congelado).
                df_dia_grupo, linha_total, rotulo_dia_anterior = _anexar_mes_anterior(
                    df_dia_grupo, linha_total, grupo, coluna_grupo, diario_base=_diario_base,
                )

                data_ref = df_dia_grupo["Data"].max() if not df_dia_grupo.empty else None
                mes_anterior = historico_mensal.fechamento_mes_anterior(
                    grupo, coluna_grupo, data_referencia=data_ref,
                )
                rotulo_anterior = historico_mensal.rotulo_mes_anterior(data_ref)

                # Supervisor não tem fechamento congelado: o mês anterior sai
                # da própria base (mesma regra de cálculo do mês atual).
                if mes_anterior is None and resumo_anterior is not None and not resumo_anterior.empty:
                    linha_ant = resumo_anterior[resumo_anterior[coluna_grupo] == grupo]
                    if not linha_ant.empty:
                        mes_anterior = _linha_total_para_comparativo(linha_ant.iloc[0].to_dict())
                        rotulo_anterior = rotulo_mes_anterior_base

                if mes_anterior:
                    with area_com_print(f"acumulado_mes_comparativo_{grupo}",
                                         nome_arquivo=f"comparativo_mensal_{grupo}"):
                        tabela_comparativo_mensal(
                            grupo, mes_anterior, _linha_total_para_comparativo(linha_total),
                            rotulo_mes_anterior=rotulo_anterior,
                            rotulo_mes_atual=_rotulo_mes_atual(df_dia_grupo),
                        )
                    st.write("")

                with area_com_print(f"acumulado_mes_fechamento_{grupo}",
                                     nome_arquivo=f"fechamento_diario_{grupo}"):
                    tabela_fechamento_diario(
                        _com_total_mes(df_dia_grupo, linha_total, coluna_grupo),
                        f"FECHAMENTO DIÁRIO — {grupo}", cor_titulo=cor,
                        rotulo_anterior=rotulo_dia_anterior,
                        rotulo_atual=_rotulo_mes_atual(df_dia_grupo),
                    )

                num_dias = len(df_dia_grupo)
                largura_minima = max(760, num_dias * 65)

                chave_efic = sanitizar_chave(f"acumulado_mes_eficacia_{grupo}")
                with area_com_print(f"acumulado_mes_eficacia_{grupo}",
                                     nome_arquivo=f"eficacia_diaria_{grupo}"):
                    st.markdown(
                        f"<style>.st-key-{chave_efic} [data-testid='stPlotlyChart']"
                        f"{{min-width:{largura_minima}px;}}</style>"
                        + cabecalho_grafico_combo("Eficácia Diária", [
                            ("Concluída", "#15803D", "barra"),
                            ("Improdutiva", config.TLP_RED, "barra"),
                            ("Eficácia %", config.TEXT_MUTED, "linha"),
                        ]),
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        grafico_eficacia_diaria(df_dia_grupo), width='stretch',
                        key=f"acumulado_mes_eficacia_chart_{grupo}",
                        config=opcoes_grafico(f"eficacia_diaria_{grupo}"),
                    )

                st.write("")

                chave_prod = sanitizar_chave(f"acumulado_mes_produtividade_{grupo}")
                with area_com_print(f"acumulado_mes_produtividade_{grupo}",
                                     nome_arquivo=f"produtividade_diaria_{grupo}"):
                    st.markdown(
                        f"<style>.st-key-{chave_prod} [data-testid='stPlotlyChart']"
                        f"{{min-width:{largura_minima}px;}}</style>"
                        + cabecalho_grafico_combo("Produtividade Diária", [
                            ("Técnicos", config.TEXT, "barra"),
                            ("PU", config.TLP_ORANGE, "linha"),
                        ]),
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        grafico_produtividade_diaria(df_dia_grupo), width='stretch',
                        key=f"acumulado_mes_produtividade_chart_{grupo}",
                        config=opcoes_grafico(f"produtividade_diaria_{grupo}"),
                    )