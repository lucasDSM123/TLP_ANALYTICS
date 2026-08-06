import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import CABECALHO_BG, TOTAL_BG, pill_total, wrapper_tabela


def _cor_eficacia(valor: float) -> str:
    """Retorna a cor (verde/dourado/vermelho) de acordo com a faixa de eficácia."""
    if valor >= 0.80:
        return "#15803D"
    if valor >= 0.60:
        return config.TLP_GOLD
    return config.TLP_RED


def tabela_matriz(df_matriz: pd.DataFrame, titulo: str, cor_titulo: str = None):
    """
    Renderiza a matriz de produção (BA ou TT) como uma tabela HTML estilizada,
    no padrão visual único do site (cabeçalho em gradiente, números em
    destaque e linha de Total com fundo de marca), com badges de alto
    contraste na coluna Eficácia e nas colunas OK/NOK.
    """
    cor_titulo = cor_titulo or config.TLP_ORANGE

    if df_matriz.empty:
        st.markdown(
            f"<h4 style='color:{cor_titulo};'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    colunas = ["Cluster", "HC Ativo", "Caixa Tot", "Esteira", "Bucket",
               "Média Atrib.", "PU", "OK", "NOK", "Iniciada", "Eficácia",
               "Proj.", "Proj. PU"]

    # NOTA: todo o HTML abaixo é montado SEM indentação (linhas começando na
    # coluna 0) de propósito. Se strings HTML multi-linha passadas para
    # st.markdown tiverem 4+ espaços de indentação, o parser de Markdown do
    # Streamlit interpreta parte do conteúdo como bloco de código e quebra o
    # HTML no meio (o efeito visual é texto solto como "</tbody>" aparecendo
    # na tela, com a tabela cortada).

    linhas_html = []
    for i, (_, row) in enumerate(df_matriz.iterrows()):
        is_total = row["Cluster"] == "Total"
        peso = "800" if is_total else "600"
        eficacia_pct = f"{row['Eficácia']:.0%}"
        cor_efic = _cor_eficacia(row["Eficácia"])

        if is_total:
            bg = TOTAL_BG
            cor_texto = "#FFFFFF"
            media_txt = f"{row['Média Atrib.']:.2f}"
            pu_txt = f"{row['PU']:.2f}"
            proj_pu_txt = f"{row['Proj. PU']:.2f}"
            cel_cluster = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{row['Cluster']}</td>"
            cel_hc = f"<td>{pill_total(row['HC Ativo'])}</td>"
            cel_caixa = f"<td>{pill_total(row['Caixa Tot'])}</td>"
            cel_esteira = f"<td>{pill_total(row['Esteira'])}</td>"
            cel_bucket = f"<td>{pill_total(row['Bucket'])}</td>"
            cel_media = f"<td>{pill_total(media_txt)}</td>"
            cel_pu = f"<td>{pill_total(pu_txt)}</td>"
            cel_ok = f"<td>{pill_total(row['OK'])}</td>"
            cel_nok = f"<td>{pill_total(row['NOK'])}</td>"
            cel_iniciada = f"<td>{pill_total(row['Iniciada'])}</td>"
            cel_efic = f"<td>{pill_total(eficacia_pct)}</td>"
            cel_proj = f"<td>{pill_total(row['Proj.'])}</td>"
            cel_proj_pu = f"<td>{pill_total(proj_pu_txt)}</td>"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_texto = config.TEXT
            cel_cluster = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{row['Cluster']}</td>"
            cel_hc = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['HC Ativo']}</td>"
            cel_caixa = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Caixa Tot']}</td>"
            cel_esteira = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Esteira']}</td>"
            cel_bucket = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Bucket']}</td>"
            cel_media = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Média Atrib.']:.2f}</td>"
            cel_pu = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['PU']:.2f}</td>"
            cel_ok = f"<td><span style='color:#15803D; font-weight:{peso};'>{row['OK']}</span></td>"
            cel_nok = f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{row['NOK']}</span></td>"
            cel_iniciada = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Iniciada']}</td>"
            cel_efic = f"<td><span style='color:{cor_efic}; font-weight:700;'>{eficacia_pct}</span></td>"
            cel_proj = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj.']}</td>"
            cel_proj_pu = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj. PU']:.2f}</td>"

        celulas = "".join([
            cel_cluster, cel_hc, cel_caixa, cel_esteira, cel_bucket, cel_media,
            cel_pu, cel_ok, cel_nok, cel_iniciada, cel_efic, cel_proj, cel_proj_pu,
        ])

        linhas_html.append(f"<tr style='{bg}'>{celulas}</tr>")

    header_html = "".join(
        f"<th style='text-align:{'left' if c == 'Cluster' else 'center'};'>{c.upper()}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)


def tabela_fechamento_diario(df_dia: pd.DataFrame, titulo: str, cor_titulo: str = None):
    """
    Tabela de fechamento diário (réplica do PAINEL do Excel/Power BI):
    uma linha por dia com Concluída, Improdutiva, Técnicos, Atribuição, PU
    e Eficácia, e uma linha 'Total Mês' ao final com o acumulado do
    período — no mesmo padrão visual das demais tabelas do site (cabeçalho
    em gradiente, badges na coluna Eficácia, linha de Total em destaque).

    Espera um DataFrame já ordenado por Data, com colunas: Data, Concluída,
    Improdutiva, Técnicos, Atribuição, PU, Eficácia. A última linha pode
    (opcionalmente) já vir com Data == "Total Mês" — caso contrário, use em
    conjunto com a linha de resumo retornada por resumo_mes_por_estado.
    """
    cor_titulo = cor_titulo or config.TLP_ORANGE

    if df_dia.empty:
        st.markdown(
            f"<h4 style='color:{cor_titulo};'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    colunas = ["Data", "Concluída", "Improdutiva", "Técnicos", "Atribuição", "PU", "Eficácia"]

    linhas_html = []
    for i, (_, row) in enumerate(df_dia.iterrows()):
        is_total = str(row["Data"]) == "Total Mês"
        peso = "800" if is_total else "600"
        eficacia_pct = f"{row['Eficácia']:.0%}"
        cor_efic = _cor_eficacia(row["Eficácia"])
        pu_alvo = row["PU"] >= config.META_PU_ALVO
        atrib_alvo = row["Atribuição"] >= config.META_ATRIBUICAO_ALVO
        cor_pu = "#15803D" if pu_alvo else config.TLP_RED
        cor_atrib = "#15803D" if atrib_alvo else config.TLP_RED

        atrib_txt = f"{row['Atribuição']:.2f}"
        pu_txt = f"{row['PU']:.2f}"

        if is_total:
            bg = TOTAL_BG
            cel_data = f"<td style='text-align:left; font-weight:{peso}; color:#FFFFFF;'>{row['Data']}</td>"
            cel_concluida = f"<td>{pill_total(row['Concluída'])}</td>"
            cel_improd = f"<td>{pill_total(row['Improdutiva'])}</td>"
            cel_tecnicos = f"<td>{pill_total(row['Técnicos'])}</td>"
            cel_atrib = f"<td>{pill_total(atrib_txt)}</td>"
            cel_pu = f"<td>{pill_total(pu_txt)}</td>"
            cel_efic = f"<td>{pill_total(eficacia_pct)}</td>"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_texto = config.TEXT
            data_txt = row["Data"].strftime("%d/%m/%Y") if hasattr(row["Data"], "strftime") else str(row["Data"])
            cel_data = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{data_txt}</td>"
            cel_concluida = f"<td><span style='color:#15803D; font-weight:{peso};'>{row['Concluída']}</span></td>"
            cel_improd = f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{row['Improdutiva']}</span></td>"
            cel_tecnicos = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Técnicos']}</td>"
            cel_atrib = f"<td><span style='color:{cor_atrib}; font-weight:700;'>{atrib_txt}</span></td>"
            cel_pu = f"<td><span style='color:{cor_pu}; font-weight:700;'>{pu_txt}</span></td>"
            cel_efic = f"<td><span style='color:{cor_efic}; font-weight:700;'>{eficacia_pct}</span></td>"

        celulas = "".join([cel_data, cel_concluida, cel_improd, cel_tecnicos, cel_atrib, cel_pu, cel_efic])
        linhas_html.append(f"<tr style='{bg}'>{celulas}</tr>")

    header_html = "".join(
        f"<th style='text-align:{'left' if c == 'Data' else 'center'};'>{c.upper()}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)


def tabela_consolidado_grupo(df_resumo: pd.DataFrame, titulo: str, coluna_grupo: str = "Estado", cor_titulo: str = None):
    """
    Tabela "Consolidado por <coluna_grupo>" (réplica do topo do PAINEL do
    Excel/Power BI): uma linha por grupo (Estado, Cluster etc.) com os
    totais acumulados do mês (Concluída, Improdutiva, Técnicos, Atribuição,
    PU, Eficácia) e uma linha 'Total' ao final com o consolidado geral —
    mesmo padrão visual das demais tabelas do site.

    Espera o DataFrame retornado por services.grupos.resumo_mes_por_grupo
    (colunas: <coluna_grupo>, Concluída, Improdutiva, Técnicos, Atribuição,
    PU, Eficácia; a linha de Total já vem com <coluna_grupo> == "Total").
    """
    cor_titulo = cor_titulo or config.TLP_ORANGE

    if df_resumo.empty or coluna_grupo not in df_resumo.columns:
        st.markdown(
            f"<h4 style='color:{cor_titulo};'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    colunas = [coluna_grupo, "Concluída", "Improdutiva", "Técnicos", "Atribuição", "PU", "Eficácia"]

    linhas_html = []
    for i, (_, row) in enumerate(df_resumo.iterrows()):
        is_total = str(row[coluna_grupo]) == "Total"
        peso = "800" if is_total else "600"
        eficacia_pct = f"{row['Eficácia']:.0%}"
        cor_efic = _cor_eficacia(row["Eficácia"])
        pu_alvo = row["PU"] >= config.META_PU_ALVO
        atrib_alvo = row["Atribuição"] >= config.META_ATRIBUICAO_ALVO
        cor_pu = "#15803D" if pu_alvo else config.TLP_RED
        cor_atrib = "#15803D" if atrib_alvo else config.TLP_RED

        atrib_txt = f"{row['Atribuição']:.2f}"
        pu_txt = f"{row['PU']:.2f}"

        if is_total:
            bg = TOTAL_BG
            cel_grupo = f"<td style='text-align:left; font-weight:{peso}; color:#FFFFFF;'>{row[coluna_grupo]}</td>"
            cel_concluida = f"<td>{pill_total(row['Concluída'])}</td>"
            cel_improd = f"<td>{pill_total(row['Improdutiva'])}</td>"
            cel_tecnicos = f"<td>{pill_total(row['Técnicos'])}</td>"
            cel_atrib = f"<td>{pill_total(atrib_txt)}</td>"
            cel_pu = f"<td>{pill_total(pu_txt)}</td>"
            cel_efic = f"<td>{pill_total(eficacia_pct)}</td>"
        else:
            bg = f"background:{config.CARD if i % 2 == 0 else config.SURFACE};"
            cor_texto = config.TEXT
            cel_grupo = f"<td style='text-align:left; font-weight:{peso}; color:{cor_texto};'>{row[coluna_grupo]}</td>"
            cel_concluida = f"<td><span style='color:#15803D; font-weight:{peso};'>{row['Concluída']}</span></td>"
            cel_improd = f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{row['Improdutiva']}</span></td>"
            cel_tecnicos = f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Técnicos']}</td>"
            cel_atrib = f"<td><span style='color:{cor_atrib}; font-weight:700;'>{atrib_txt}</span></td>"
            cel_pu = f"<td><span style='color:{cor_pu}; font-weight:700;'>{pu_txt}</span></td>"
            cel_efic = f"<td><span style='color:{cor_efic}; font-weight:700;'>{eficacia_pct}</span></td>"

        celulas = "".join([cel_grupo, cel_concluida, cel_improd, cel_tecnicos, cel_atrib, cel_pu, cel_efic])
        linhas_html.append(f"<tr style='{bg}'>{celulas}</tr>")

    header_html = "".join(
        f"<th style='text-align:{'left' if c == coluna_grupo else 'center'};'>{c.upper()}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)


def tabela_consolidado_estado(df_resumo: pd.DataFrame, titulo: str, cor_titulo: str = None):
    """Atalho de `tabela_consolidado_grupo` para o agrupamento por Estado."""
    tabela_consolidado_grupo(df_resumo, titulo, "Estado", cor_titulo)


def tabela_comparativo_mensal(nome_grupo: str, mes_anterior: dict, mes_atual: dict,
                               rotulo_mes_anterior: str = "JULHO", rotulo_mes_atual: str = "AGOSTO"):
    """
    Tabela "MÊS ANTERIOR | Δ | MÊS ATUAL" — compara o fechamento congelado
    do mês passado (`mes_anterior`, vindo de services.historico_mensal, um
    valor fixo) com o fechamento do mês corrente (`mes_atual`, calculado ao
    vivo a partir da base — mesmas chaves que `_linha_resumo_soma` produz,
    já traduzidas para minúsculas/sem acento: eficacia, concluida,
    improdutiva, tecnicos, atribuicao, pu).

    Réplica do bloco de comparação mensal do PAINEL do Excel/Power BI. Se
    `mes_anterior` for None (grupo novo, sem histórico), a tabela não é
    desenhada.
    """
    if not mes_anterior or not mes_atual:
        return

    # (rótulo, chave, tipo de formatação, direção favorável — True = "subir é bom",
    # False = "descer é bom", None = neutro/sem cor de julgamento; mostrar_sinal =
    # exibe o delta com o sinal real (-542) em vez de seta + valor absoluto)
    linhas_spec = [
        ("Eficácia %", "eficacia", "pct", True, False),
        ("Concluída", "concluida", "int", True, False),
        ("Improdutiva", "improdutiva", "int", False, False),
        ("Técnicos", "tecnicos", "int", True, True),
        ("Atribuição", "atribuicao", "dec2", True, False),
        ("PU", "pu", "dec2", True, False),
    ]

    def fmt(v, tipo, forcar_sinal=False):
        if v is None:
            return "—"
        if tipo == "pct":
            texto = f"{v:+.0%}" if forcar_sinal else f"{v:.0%}"
            return texto
        if tipo == "int":
            texto = f"{v:+,.0f}" if forcar_sinal else f"{v:,.0f}"
            return texto.replace(",", ".")
        return f"{v:+.2f}" if forcar_sinal else f"{v:.2f}"

    linhas_html = []
    for rotulo, chave, tipo, favoravel_se_sobe, mostrar_sinal in linhas_spec:
        v_ant = mes_anterior.get(chave)
        v_atu = mes_atual.get(chave)
        delta = None if (v_ant is None or v_atu is None) else v_atu - v_ant

        if delta is None or favoravel_se_sobe is None:
            cor_delta = config.TEXT_MUTED
            seta = "→"
        else:
            favoravel = (delta >= 0) if favoravel_se_sobe else (delta <= 0)
            cor_delta = "#15803D" if favoravel else config.TLP_RED
            seta = "▲" if delta >= 0 else "▼"

        if delta is None:
            delta_txt = "—"
        elif tipo == "pct":
            delta_txt = f"{seta} {delta:+.0%}"
        elif mostrar_sinal:
            delta_txt = f"{seta} {fmt(delta, tipo, forcar_sinal=True)}"
        else:
            delta_txt = f"{seta} {fmt(abs(delta), tipo)}"

        linhas_html.append(
            "<tr>"
            f"<td style='text-align:left; font-weight:600; color:{config.TEXT};'>{rotulo}</td>"
            f"<td style='color:{config.TEXT}; font-weight:700;'>{fmt(v_ant, tipo)}</td>"
            f"<td><span style='color:{cor_delta}; font-weight:700;'>{delta_txt}</span></td>"
            f"<td style='font-weight:800; color:{config.TEXT};'>{fmt(v_atu, tipo)}</td>"
            "</tr>"
        )

    tabela = (
        f"<table style='width:100%; border-collapse:collapse; font-size:13.5px; color:{config.TEXT}; text-align:center;'>"
        "<thead><tr>"
        "<th style='text-align:left;'></th>"
        f"<th style='background:{config.TEXT}; color:#FFFFFF;'>{rotulo_mes_anterior}</th>"
        f"<th style='background:{config.CARD_BORDER}; color:{config.TEXT};'>&#9650;</th>"
        f"<th style='background:{config.BRAND_GRADIENT}; color:#FFFFFF;'>{rotulo_mes_atual}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        "</table>"
    )

    html = (
        f"<h4 style='color:{config.TLP_ORANGE}; margin-bottom:6px;'>"
        f"Comparativo com o Mês Anterior — {nome_grupo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )
    st.markdown(html, unsafe_allow_html=True)