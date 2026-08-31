import pandas as pd
import streamlit as st

import config
from components.cards import card
from components.estilo_tabela import (
    CABECALHO_BG, TOTAL_BG, pill_total, wrapper_tabela, sanitizar_id, estilo_expansivel,
)
from components.tabela_expansivel import ativar_tabelas_expansiveis

_CORES_FAIXA = {
    "P0": config.TLP_RED,
    "P1": config.TLP_ORANGE,
    "P2": config.TLP_GOLD,
    "P3": "#00C9A7",
    ">P3": "#22C55E",
}
_FAIXAS = ["P0", "P1", "P2", "P3", ">P3"]


def tabela_analise_p(df_matriz: pd.DataFrame, coluna_grupo: str, titulo: str = "Análise P — Produtividade"):
    """
    Renderiza a matriz P0..>P3 como tabela HTML estilizada, réplica visual
    da tabela "PRODUTIVIDADE POR SUPERVISOR - TÉCNICO" do Power BI (uma
    coluna por faixa, cores por faixa, linha de TOTAL em destaque).
    """
    if df_matriz.empty or coluna_grupo not in df_matriz.columns:
        st.info(f"Sem dados de {coluna_grupo} para os filtros atuais.")
        return

    linhas_html = []
    for i, (_, row) in enumerate(df_matriz.iterrows()):
        is_total = str(row[coluna_grupo]).upper() == "TOTAL"
        peso = "800" if is_total else "600"

        if is_total:
            bg = TOTAL_BG()
            cor_nome = "#FFFFFF"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_nome = config.TEXT

        celulas = [f"<td style='text-align:left; font-weight:{peso}; color:{cor_nome};'>{row[coluna_grupo]}</td>"]
        for faixa in _FAIXAS:
            cor = _CORES_FAIXA[faixa]
            valor = int(row[faixa])
            if is_total:
                celulas.append(f"<td>{pill_total(valor)}</td>")
            else:
                celulas.append(f"<td style='color:{cor}; font-weight:{peso};'>{valor}</td>")
        linhas_html.append(f"<tr style='{bg}'>{''.join(celulas)}</tr>")

    header_html = "<th style='text-align:left;'>" + coluna_grupo.upper() + "</th>" + "".join(
        f"<th style='text-align:center; color:#FFE9CC;'>{f}</th>" for f in _FAIXAS
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = f"<h5 style='color:{config.TEXT}; margin-bottom:6px;'>{titulo}</h5>{wrapper_tabela(tabela)}"
    st.markdown(html, unsafe_allow_html=True)


_FAIXAS_DETALHADO = ["P0", "P1", "P2", "P3", "P4", "P5", "P≥6"]
_CORES_FAIXA_DETALHADO = {
    "P0": config.TLP_RED,
    "P1": config.TLP_ORANGE,
    "P2": config.TLP_GOLD,
    "P3": "#00C9A7",
    "P4": "#7B8CDE",
    "P5": "#3B82F6",
    "P≥6": "#22C55E",
}


def _tabela_html(df_tabela: pd.DataFrame, coluna_grupo: str, formato_percentual: bool = False) -> str:
    linhas_html = []
    for i, (_, row) in enumerate(df_tabela.iterrows()):
        is_total = str(row[coluna_grupo]).upper() in ("TOTAL", "TOTAL GERAL")
        peso = "800" if is_total else "600"

        if is_total:
            bg = TOTAL_BG()
            cor_nome = "#FFFFFF"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_nome = config.TEXT

        celulas = [f"<td style='text-align:left; font-weight:{peso}; color:{cor_nome};'>{row[coluna_grupo]}</td>"]
        for faixa in _FAIXAS_DETALHADO:
            cor = _CORES_FAIXA_DETALHADO[faixa]
            valor = row[faixa]
            texto = f"{valor:.1f}%" if formato_percentual else f"{int(valor)}"
            if is_total:
                celulas.append(f"<td>{pill_total(texto)}</td>")
            else:
                celulas.append(f"<td style='color:{cor}; font-weight:{peso};'>{texto}</td>")
        if not formato_percentual and "TOTAL" in df_tabela.columns:
            if is_total:
                celulas.append(f"<td>{pill_total(int(row['TOTAL']))}</td>")
            else:
                celulas.append(f"<td style='font-weight:{peso}; color:{config.TEXT};'>{int(row['TOTAL'])}</td>")
        linhas_html.append(f"<tr style='{bg}'>{''.join(celulas)}</tr>")

    colunas_extra_header = "<th style='text-align:center;'>TOTAL</th>" if (not formato_percentual and "TOTAL" in df_tabela.columns) else ""
    header_html = "<th style='text-align:left;'>" + coluna_grupo.upper() + "</th>" + "".join(
        f"<th style='text-align:center; color:#FFE9CC;'>{f}{'%' if formato_percentual else ''}</th>"
        for f in _FAIXAS_DETALHADO
    ) + colunas_extra_header

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )
    return wrapper_tabela(tabela)


def tabela_analise_p_cluster(contagem: pd.DataFrame, percentual: pd.DataFrame, resumo: dict, coluna_grupo: str = "Cluster"):
    """
    Renderiza a Análise P por Cluster: cards de resumo (Técnicos P0 / P1 /
    Total) + tabela de contagem e tabela de percentual lado a lado —
    réplica visual do site de referência (Power BI).
    """
    if contagem.empty or percentual.empty:
        st.info(f"Sem dados de Análise P por {coluna_grupo} para os filtros atuais.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        card("TÉCNICOS P0", resumo["P0"], config.TLP_RED)
    with c2:
        card("TÉCNICOS P1", resumo["P1"], config.TLP_ORANGE)
    with c3:
        card("TOTAL TÉCNICOS", resumo["TOTAL"], "#7B8CDE")

    st.write("")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Contagem por {coluna_grupo}</h5>", unsafe_allow_html=True)
        st.markdown(_tabela_html(contagem, coluna_grupo, formato_percentual=False), unsafe_allow_html=True)
    with col_b:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Percentual por {coluna_grupo}</h5>", unsafe_allow_html=True)
        st.markdown(_tabela_html(percentual, coluna_grupo, formato_percentual=True), unsafe_allow_html=True)


def _celulas_linha_p(linha: dict, peso: str, formato_percentual: bool) -> str:
    """Gera as células P0..P5/P≥6 (+ TOTAL, se contagem) de uma linha
    "normal" (não-Total) — usado tanto pela linha de Cidade quanto pela
    linha de subtotal do Cluster na tabela expansível de Análise P."""
    total = linha.get("TOTAL", 0)
    celulas = []
    for faixa in _FAIXAS_DETALHADO:
        cor = _CORES_FAIXA_DETALHADO[faixa]
        valor = linha[faixa]
        if formato_percentual:
            pct = 0.0 if not total else (valor / total) * 100
            texto = f"{pct:.1f}%"
        else:
            texto = f"{int(valor)}"
        celulas.append(f"<td style='color:{cor}; font-weight:{peso};'>{texto}</td>")
    if not formato_percentual:
        celulas.append(f"<td style='font-weight:{peso}; color:{config.TEXT};'>{int(total)}</td>")
    return "".join(celulas)


def _celulas_linha_p_total(linha: dict, formato_percentual: bool) -> str:
    """Linha de Total (estilo "balão branco") a partir de uma linha que JÁ
    vem com os valores prontos (contagens ou percentuais, conforme o
    caso) — ex.: a linha "Total Geral" de contagem_cluster/
    percentual_cluster, que já vem com o percentual calculado, sem
    precisar dividir de novo por TOTAL (diferente das linhas de Cluster/
    Cidade da tabela expansível, que só têm as contagens brutas)."""
    celulas = []
    for faixa in _FAIXAS_DETALHADO:
        valor = linha[faixa]
        texto = f"{valor:.1f}%" if formato_percentual else f"{int(valor)}"
        celulas.append(f"<td>{pill_total(texto)}</td>")
    if not formato_percentual and "TOTAL" in linha:
        celulas.append(f"<td>{pill_total(int(linha['TOTAL']))}</td>")
    return "".join(celulas)


def _tabela_html_expansivel(grupos: list, coluna_grupo: str, id_tabela: str,
                             formato_percentual: bool = False, total_row: dict = None) -> str:
    if not grupos:
        return ""

    linhas_html = []
    for grupo in grupos:
        classe_grupo = f"{id_tabela}_{sanitizar_id(grupo['cluster'])}"
        subtotal = grupo["subtotal"]

        cel_nome_cluster = (
            "<td style='text-align:left; font-weight:800; color:{cor};'>"
            "<span class='seta-exp' style='display:inline-block; width:14px;'>▶</span> {nome}</td>"
        ).format(cor=config.TLP_ORANGE, nome=grupo["cluster"])
        linhas_html.append(
            f"<tr class='linha-cluster-expansivel' data-alvo='{classe_grupo}' "
            f"style='background:{config.SURFACE}; cursor:pointer; border-top:2px solid {config.CARD_BORDER};'>"
            f"{cel_nome_cluster}{_celulas_linha_p(subtotal, '800', formato_percentual)}</tr>"
        )

        for i, cidade in enumerate(grupo["cidades"]):
            bg = config.CARD if i % 2 == 0 else config.SURFACE
            cel_nome_cidade = (
                f"<td style='text-align:left; font-weight:500; font-style:italic; "
                f"color:{config.TEXT_MUTED}; padding-left:30px;'>{cidade['Nome']}</td>"
            )
            linhas_html.append(
                f"<tr class='{classe_grupo} linha-cidade-expansivel' style='display:none; background:{bg};'>"
                f"{cel_nome_cidade}{_celulas_linha_p(cidade, '500', formato_percentual)}</tr>"
            )

    linha_total_html = ""
    if total_row:
        cel_nome_total = f"<td style='text-align:left; font-weight:800; color:#FFFFFF;'>{total_row.get('Nome', 'Total Geral')}</td>"
        linha_total_html = f"<tr style='{TOTAL_BG()}'>{cel_nome_total}{_celulas_linha_p_total(total_row, formato_percentual)}</tr>"

    colunas_extra_header = "<th style='text-align:center;'>TOTAL</th>" if not formato_percentual else ""
    header_html = "<th style='text-align:left;'>CLUSTER / CIDADE</th>" + "".join(
        f"<th style='text-align:center; color:#FFE9CC;'>{f}{'%' if formato_percentual else ''}</th>"
        for f in _FAIXAS_DETALHADO
    ) + colunas_extra_header

    tabela = (
        f"<table style='width:100%; min-width:900px; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}{linha_total_html}</tbody>"
        f"</table>"
    )
    return estilo_expansivel() + wrapper_tabela(tabela)


def tabela_analise_p_cluster_cidade(grupos: list, resumo: dict = None, coluna_grupo: str = "Cluster",
                                     total_contagem: dict = None, total_percentual: dict = None,
                                     id_tabela: str = "analise_p"):
    """
    Mesma Análise P por Cluster de `tabela_analise_p_cluster`, mas
    destrinchada em dois níveis — Cluster -> Cidade —, com o Cluster como
    linha "cabeçalho" clicável (seta ▶/▼) que abre/fecha as cidades dentro
    dele. Todas as cidades começam fechadas.

    `grupos` vem de `services.analise_p.matriz_analise_p_cluster_cidade`:
    [{"cluster": str, "cidades": [linha, ...], "subtotal": linha}, ...]
    `total_contagem`/`total_percentual`, se informados, viram a linha
    "Total Geral" fixa no rodapé de cada tabela (mesmas chaves de uma
    linha normal — P0..P5/P≥6 [+ TOTAL, na de contagem] — com
    "Nome" = "Total Geral").
    """
    if not grupos:
        st.info(f"Sem dados de Análise P por {coluna_grupo} e Cidade para os filtros atuais.")
        return

    ativar_tabelas_expansiveis()

    if resumo:
        c1, c2, c3 = st.columns(3)
        with c1:
            card("TÉCNICOS P0", resumo["P0"], config.TLP_RED)
        with c2:
            card("TÉCNICOS P1", resumo["P1"], config.TLP_ORANGE)
        with c3:
            card("TOTAL TÉCNICOS", resumo["TOTAL"], "#7B8CDE")
        st.write("")

    st.markdown(
        f"<p style='color:{config.TEXT_MUTED}; font-size:12.5px; margin:-4px 0 8px 0;'>"
        f"Clique num Cluster para ver as cidades</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Contagem por {coluna_grupo} / Cidade</h5>", unsafe_allow_html=True)
        st.markdown(
            _tabela_html_expansivel(grupos, coluna_grupo, f"{id_tabela}_contagem",
                                     formato_percentual=False, total_row=total_contagem),
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(f"<h5 style='color:{config.TEXT};'>Percentual por {coluna_grupo} / Cidade</h5>", unsafe_allow_html=True)
        st.markdown(
            _tabela_html_expansivel(grupos, coluna_grupo, f"{id_tabela}_percentual",
                                     formato_percentual=True, total_row=total_percentual),
            unsafe_allow_html=True,
        )


def _tabela_html_expansivel_3niveis(grupos: list, id_tabela: str, formato_percentual: bool = False,
                                     total_row: dict = None) -> str:
    """Mesma ideia de `_tabela_html_expansivel`, mas com um terceiro nível
    de detalhamento (Coordenador -> Supervisor -> Técnico). O Técnico é o
    nível folha — não é clicável, só uma linha a mais, ainda mais recuada
    e clarinha."""
    if not grupos:
        return ""

    linhas_html = []
    for coord in grupos:
        classe_coord = f"{id_tabela}_{sanitizar_id(coord['nome'])}"

        cel_nome_coord = (
            "<td style='text-align:left; font-weight:800; color:{cor};'>"
            "<span class='seta-exp' style='display:inline-block; width:14px;'>▶</span> {nome}</td>"
        ).format(cor=config.TLP_ORANGE, nome=coord["nome"])
        linhas_html.append(
            f"<tr class='linha-cluster-expansivel' data-alvo='{classe_coord}' "
            f"style='background:{config.SURFACE}; cursor:pointer; border-top:2px solid {config.CARD_BORDER};'>"
            f"{cel_nome_coord}{_celulas_linha_p(coord['subtotal'], '800', formato_percentual)}</tr>"
        )

        for sup in coord["supervisores"]:
            classe_sup = f"{classe_coord}_{sanitizar_id(sup['nome'])}"
            cel_nome_sup = (
                "<td style='text-align:left; font-weight:700; padding-left:24px; color:{cor};'>"
                "<span class='seta-exp' style='display:inline-block; width:12px;'>▶</span> {nome}</td>"
            ).format(cor=config.TLP_ORANGE, nome=sup["nome"])
            linhas_html.append(
                f"<tr class='{classe_coord} linha-cidade-expansivel linha-cluster-expansivel' "
                f"data-alvo='{classe_sup}' style='cursor:pointer; display:none;'>"
                f"{cel_nome_sup}{_celulas_linha_p(sup['subtotal'], '700', formato_percentual)}</tr>"
            )

            for tecnico in sup["tecnicos"]:
                cel_nome_tec = (
                    f"<td style='text-align:left; font-weight:400; font-style:italic; "
                    f"color:{config.TEXT_MUTED}; padding-left:48px;'>{tecnico['Nome']}</td>"
                )
                linhas_html.append(
                    f"<tr class='{classe_sup} linha-cidade-expansivel' style='display:none;'>"
                    f"{cel_nome_tec}{_celulas_linha_p(tecnico, '400', formato_percentual)}</tr>"
                )

    linha_total_html = ""
    if total_row:
        cel_nome_total = f"<td style='text-align:left; font-weight:800; color:#FFFFFF;'>{total_row.get('Nome', 'Total Geral')}</td>"
        linha_total_html = f"<tr style='{TOTAL_BG()}'>{cel_nome_total}{_celulas_linha_p_total(total_row, formato_percentual)}</tr>"

    colunas_extra_header = "<th style='text-align:center;'>TOTAL</th>" if not formato_percentual else ""
    header_html = "<th style='text-align:left;'>COORDENADOR / SUPERVISOR / TÉCNICO</th>" + "".join(
        f"<th style='text-align:center; color:#FFE9CC;'>{f}{'%' if formato_percentual else ''}</th>"
        for f in _FAIXAS_DETALHADO
    ) + colunas_extra_header

    tabela = (
        f"<table style='width:100%; min-width:950px; border-collapse:collapse; font-size:13px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}{linha_total_html}</tbody>"
        f"</table>"
    )
    return estilo_expansivel() + wrapper_tabela(tabela)


def tabela_analise_p_coordenador_supervisor_tecnico(grupos: list, resumo: dict = None,
                                                      total_contagem: dict = None, total_percentual: dict = None,
                                                      id_tabela: str = "analise_p_cst"):
    """
    Análise P destrinchada em TRÊS níveis — Coordenador -> Supervisor ->
    Técnico —, cada nível clicável (Coordenador e Supervisor abrem/fecham
    o próximo nível; Técnico é a linha folha). Todos começam fechados.

    `grupos` vem de
    `services.analise_p.matriz_analise_p_coordenador_supervisor_tecnico`:
    [{"nome": coordenador, "subtotal": linha, "supervisores": [
        {"nome": supervisor, "subtotal": linha, "tecnicos": [linha, ...]},
        ...
    ]}, ...]
    `total_contagem`/`total_percentual`, se informados, viram a linha
    "Total Geral" fixa no rodapé de cada tabela.
    """
    if not grupos:
        st.info("Sem dados de Análise P por Coordenador / Supervisor / Técnico para os filtros atuais.")
        return

    ativar_tabelas_expansiveis()

    if resumo:
        c1, c2, c3 = st.columns(3)
        with c1:
            card("TÉCNICOS P0", resumo["P0"], config.TLP_RED)
        with c2:
            card("TÉCNICOS P1", resumo["P1"], config.TLP_ORANGE)
        with c3:
            card("TOTAL TÉCNICOS", resumo["TOTAL"], "#7B8CDE")
        st.write("")

    st.markdown(
        f"<p style='color:{config.TEXT_MUTED}; font-size:12.5px; margin:-4px 0 8px 0;'>"
        f"Clique num Coordenador (e depois num Supervisor) para ver os detalhes</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<h5 style='color:{cor};'>Contagem por Coordenador / Supervisor / Técnico</h5>"
                     .format(cor=config.TEXT), unsafe_allow_html=True)
        st.markdown(
            _tabela_html_expansivel_3niveis(grupos, f"{id_tabela}_contagem",
                                             formato_percentual=False, total_row=total_contagem),
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown("<h5 style='color:{cor};'>Percentual por Coordenador / Supervisor / Técnico</h5>"
                     .format(cor=config.TEXT), unsafe_allow_html=True)
        st.markdown(
            _tabela_html_expansivel_3niveis(grupos, f"{id_tabela}_percentual",
                                             formato_percentual=True, total_row=total_percentual),
            unsafe_allow_html=True,
        )