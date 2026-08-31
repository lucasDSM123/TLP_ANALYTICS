import pandas as pd
import streamlit as st

import config
from components.estilo_tabela import (
    CABECALHO_BG, TOTAL_BG, SUBTOTAL_BG, pill_total, wrapper_tabela,
    sanitizar_id, estilo_expansivel,
)
from components.tabela_expansivel import ativar_tabelas_expansiveis


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
            bg = TOTAL_BG()
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
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)


def _celulas_linha_matriz(row: dict, peso: str, cor_texto: str) -> str:
    """Gera as 12 células de indicadores (HC Ativo .. Proj. PU) para uma
    linha "normal" (não-Total) da matriz de produção — usado tanto pela
    linha de Cidade quanto pela linha de subtotal do Cluster na tabela
    expansível."""
    eficacia_pct = f"{row['Eficácia']:.0%}"
    cor_efic = _cor_eficacia(row["Eficácia"])
    return "".join([
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['HC Ativo']}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Caixa Tot']}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Esteira']}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Bucket']}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Média Atrib.']:.2f}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['PU']:.2f}</td>",
        f"<td><span style='color:#15803D; font-weight:{peso};'>{row['OK']}</span></td>",
        f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{row['NOK']}</span></td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Iniciada']}</td>",
        f"<td><span style='color:{cor_efic}; font-weight:700;'>{eficacia_pct}</span></td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj.']}</td>",
        f"<td style='font-weight:{peso}; color:{cor_texto};'>{row['Proj. PU']:.2f}</td>",
    ])


def _celulas_linha_matriz_total(row: dict) -> str:
    """Mesmas 12 colunas, no estilo "balão branco" usado na linha de Total."""
    eficacia_pct = f"{row['Eficácia']:.0%}"
    media_txt = f"{row['Média Atrib.']:.2f}"
    pu_txt = f"{row['PU']:.2f}"
    proj_pu_txt = f"{row['Proj. PU']:.2f}"
    return "".join([
        f"<td>{pill_total(row['HC Ativo'])}</td>",
        f"<td>{pill_total(row['Caixa Tot'])}</td>",
        f"<td>{pill_total(row['Esteira'])}</td>",
        f"<td>{pill_total(row['Bucket'])}</td>",
        f"<td>{pill_total(media_txt)}</td>",
        f"<td>{pill_total(pu_txt)}</td>",
        f"<td>{pill_total(row['OK'])}</td>",
        f"<td>{pill_total(row['NOK'])}</td>",
        f"<td>{pill_total(row['Iniciada'])}</td>",
        f"<td>{pill_total(eficacia_pct)}</td>",
        f"<td>{pill_total(row['Proj.'])}</td>",
        f"<td>{pill_total(proj_pu_txt)}</td>",
    ])


def tabela_matriz_expansivel(grupos: list, titulo: str, cor_titulo: str = None,
                              total: dict = None, id_tabela: str = None,
                              rotulo_grupo: str = "CLUSTER / CIDADE",
                              rotulo_clique: str = "Cluster"):
    """
    Mesma matriz de produção de `tabela_matriz` (colunas idênticas), só que
    destrinchada em dois níveis — grupo principal -> subgrupo (ex.: Cluster
    -> Cidade, ou Coordenador -> Supervisor) —, com o grupo principal como
    linha "cabeçalho" clicável (seta ▶/▼) que abre/fecha os subgrupos
    dentro dele. Todos os subgrupos começam fechados.

    `grupos` vem de `services.grupos.matriz_producao_cluster_cidade` (que,
    apesar do nome, é genérica — funciona com qualquer par de colunas):
    [{"cluster": str, "cidades": [linha, ...], "subtotal": linha}, ...]
    `total`, se informado, vira a linha "TOTAL" fixa no rodapé (mesmas
    chaves de uma linha normal, com "Nome" = "Total").
    `rotulo_grupo` é o texto do cabeçalho da 1ª coluna (ex.: "CLUSTER /
    CIDADE" ou "COORDENADOR / SUPERVISOR"). `rotulo_clique` é usado na
    dica abaixo do título (ex.: "Cluster" ou "Coordenador").
    """
    cor_titulo = cor_titulo or config.TLP_ORANGE

    if not grupos:
        st.markdown(
            f"<h4 style='color:{cor_titulo}; text-align:center;'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    colunas = [rotulo_grupo, "HC ATIVO", "CAIXA TOT", "ESTEIRA", "BUCKET",
               "MÉDIA ATRIB.", "PU", "OK", "NOK", "INICIADA", "EFICÁCIA", "PROJ.", "PROJ. PU"]

    id_tabela = sanitizar_id(id_tabela or titulo)
    ativar_tabelas_expansiveis()

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
            f"{cel_nome_cluster}{_celulas_linha_matriz(subtotal, '800', config.TEXT)}</tr>"
        )

        for i, cidade in enumerate(grupo["cidades"]):
            bg = config.CARD if i % 2 == 0 else config.SURFACE
            cel_nome_cidade = (
                f"<td style='text-align:left; font-weight:500; font-style:italic; "
                f"color:{config.TEXT_MUTED}; padding-left:30px;'>{cidade['Nome']}</td>"
            )
            linhas_html.append(
                f"<tr class='{classe_grupo} linha-cidade-expansivel' style='display:none; background:{bg};'>"
                f"{cel_nome_cidade}{_celulas_linha_matriz(cidade, '500', config.TEXT)}</tr>"
            )

    linha_total_html = ""
    if total:
        cel_nome_total = f"<td style='text-align:left; font-weight:800; color:#FFFFFF;'>{total.get('Nome', 'Total')}</td>"
        linha_total_html = f"<tr style='{TOTAL_BG()}'>{cel_nome_total}{_celulas_linha_matriz_total(total)}</tr>"

    header_html = "".join(
        f"<th style='text-align:{'left' if c == rotulo_grupo else 'center'};'>{c}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; min-width:1200px; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}{linha_total_html}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px; text-align:center;'>{titulo}</h4>"
        f"<p style='color:{config.TEXT_MUTED}; font-size:12.5px; margin:-4px 0 8px 0;'>"
        f"Clique num {rotulo_clique} para ver os detalhes</p>"
        f"{estilo_expansivel()}"
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
            bg = TOTAL_BG()
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
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{cor_titulo}; margin-bottom:6px;'>{titulo}</h4>"
        f"{wrapper_tabela(tabela, altura_max=480)}"
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
            bg = TOTAL_BG()
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
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
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


def _celulas_linha_chegada(g: dict, peso: str, meta_pct: float) -> str:
    """
    Gera as 6 células (Dentro/Antes/Depois/Fora/Total/% Dentro) de uma
    linha do indicador de Chegada. Dentro e Antes em verde (chegou dentro
    do horário ou só um pouco adiantado); Depois e Fora em vermelho
    (chegou fora do horário). % Dentro vira badge verde/vermelho conforme
    a meta (`meta_pct`, padrão 80%).
    """
    cor_pct = "#15803D" if g["pct"] >= meta_pct else config.TLP_RED
    bg_pct = "rgba(34,197,94,0.14)" if g["pct"] >= meta_pct else "rgba(232,57,29,0.12)"
    return "".join([
        f"<td><span style='color:#15803D; font-weight:{peso};'>{g['dentro']}</span></td>",
        f"<td><span style='color:#15803D; font-weight:{peso};'>{g['antes']}</span></td>",
        f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{g['depois']}</span></td>",
        f"<td><span style='color:{config.TLP_RED}; font-weight:{peso};'>{g['fora']}</span></td>",
        f"<td style='font-weight:{peso}; color:{config.TEXT};'>{g['total']}</td>",
        "<td><span style='display:inline-block; min-width:56px; padding:3px 10px; "
        f"border-radius:999px; background:{bg_pct}; color:{cor_pct}; font-weight:800;'>{g['pct']:.1f}%</span></td>",
    ])


def tabela_chegada_expansivel(dados: list, titulo: str = "Por Cluster", meta_pct: float = 80.0,
                               rotulo_grupo: str = "CLUSTER / CIDADE", id_tabela: str = "chegada_matriz"):
    """
    Matriz única (Cluster clicável -> Cidades dentro dele) do indicador de
    Chegada, no mesmo padrão visual/comportamento das demais tabelas
    expansíveis do site (cabeçalho em gradiente, seta ▶/▼, subgrupos
    fechados por padrão). `dados` vem de `services.chegada.resumo_hierarquico`.
    """
    if not dados:
        st.markdown(
            f"<h4 style='color:{config.TLP_ORANGE}; text-align:center;'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    id_tabela = sanitizar_id(id_tabela)
    ativar_tabelas_expansiveis()

    colunas = [rotulo_grupo, "DENTRO", "ANTES", "DEPOIS", "FORA", "TOTAL", "% DENTRO"]

    linhas_html = []
    for grupo in dados:
        classe_grupo = f"{id_tabela}_{sanitizar_id(grupo['nome'])}"

        cel_nome = (
            "<td style='text-align:left; font-weight:800; color:{cor};'>"
            "<span class='seta-exp' style='display:inline-block; width:14px;'>▶</span> {nome}</td>"
        ).format(cor=config.TLP_ORANGE, nome=grupo["nome"])
        linhas_html.append(
            f"<tr class='linha-cluster-expansivel' data-alvo='{classe_grupo}' "
            f"style='background:{config.SURFACE}; cursor:pointer; border-top:2px solid {config.CARD_BORDER};'>"
            f"{cel_nome}{_celulas_linha_chegada(grupo, '800', meta_pct)}</tr>"
        )

        for i, filho in enumerate(grupo["filhos"]):
            bg = config.CARD if i % 2 == 0 else config.SURFACE
            cel_nome_filho = (
                f"<td style='text-align:left; font-weight:500; font-style:italic; "
                f"color:{config.TEXT_MUTED}; padding-left:30px;'>{filho['nome']}</td>"
            )
            linhas_html.append(
                f"<tr class='{classe_grupo} linha-cidade-expansivel' style='display:none; background:{bg};'>"
                f"{cel_nome_filho}{_celulas_linha_chegada(filho, '500', meta_pct)}</tr>"
            )

    header_html = "".join(
        f"<th style='text-align:{'left' if c == rotulo_grupo else 'center'};'>{c}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; min-width:640px; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{config.TLP_ORANGE}; margin-bottom:6px; text-align:center;'>{titulo}</h4>"
        f"<p style='color:{config.TEXT_MUTED}; font-size:12.5px; margin:-4px 0 8px 0; text-align:center;'>"
        f"Clique num Cluster para ver as Cidades</p>"
        f"{estilo_expansivel()}"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)


def tabela_chegada_expansivel_3niveis(
    dados: list, titulo: str = "Por Cluster", meta_pct: float = 80.0,
    rotulo_grupo: str = "CLUSTER / CIDADE / ZONA", rotulo_clique: str = "Cluster",
    id_tabela: str = "chegada_matriz_3n",
):
    """
    Mesma ideia de `tabela_chegada_expansivel`, só que com mais um nível de
    detalhamento (ex.: Cluster -> Cidade -> Zona, ou Coordenador ->
    Supervisor -> Técnico). O 3º nível é a linha folha — não é clicável,
    só uma linha a mais, ainda mais recuada. Todos os níveis começam
    fechados. `dados` vem de `services.chegada.resumo_hierarquico_3niveis`.
    """
    if not dados:
        st.markdown(
            f"<h4 style='color:{config.TLP_ORANGE}; text-align:center;'>{titulo}</h4>"
            f"<p style='color:{config.TEXT_MUTED};'>Sem dados para os filtros selecionados.</p>",
            unsafe_allow_html=True,
        )
        return

    id_tabela = sanitizar_id(id_tabela)
    ativar_tabelas_expansiveis()

    colunas = [rotulo_grupo, "DENTRO", "ANTES", "DEPOIS", "FORA", "TOTAL", "% DENTRO"]

    linhas_html = []
    for grupo in dados:
        classe_grupo = f"{id_tabela}_{sanitizar_id(grupo['nome'])}"

        cel_nome = (
            "<td style='text-align:left; font-weight:800; color:{cor};'>"
            "<span class='seta-exp' style='display:inline-block; width:14px;'>▶</span> {nome}</td>"
        ).format(cor=config.TLP_ORANGE, nome=grupo["nome"])
        linhas_html.append(
            f"<tr class='linha-cluster-expansivel' data-alvo='{classe_grupo}' "
            f"style='background:{config.SURFACE}; cursor:pointer; border-top:2px solid {config.CARD_BORDER};'>"
            f"{cel_nome}{_celulas_linha_chegada(grupo, '800', meta_pct)}</tr>"
        )

        for filho in grupo["filhos"]:
            classe_filho = f"{classe_grupo}_{sanitizar_id(filho['nome'])}"
            cel_nome_filho = (
                "<td style='text-align:left; font-weight:700; padding-left:24px; color:{cor};'>"
                "<span class='seta-exp' style='display:inline-block; width:12px;'>▶</span> {nome}</td>"
            ).format(cor=config.TLP_ORANGE, nome=filho["nome"])
            linhas_html.append(
                f"<tr class='{classe_grupo} linha-cidade-expansivel linha-cluster-expansivel' "
                f"data-alvo='{classe_filho}' style='cursor:pointer; display:none; background:{config.CARD};'>"
                f"{cel_nome_filho}{_celulas_linha_chegada(filho, '700', meta_pct)}</tr>"
            )

            for i, neto in enumerate(filho["netos"]):
                bg = config.SURFACE if i % 2 == 0 else config.CARD
                cel_nome_neto = (
                    f"<td style='text-align:left; font-weight:500; font-style:italic; "
                    f"color:{config.TEXT_MUTED}; padding-left:46px;'>{neto['nome']}</td>"
                )
                linhas_html.append(
                    f"<tr class='{classe_filho} linha-cidade-expansivel' style='display:none; background:{bg};'>"
                    f"{cel_nome_neto}{_celulas_linha_chegada(neto, '500', meta_pct)}</tr>"
                )

    header_html = "".join(
        f"<th style='text-align:{'left' if c == rotulo_grupo else 'center'};'>{c}</th>"
        for c in colunas
    )

    tabela = (
        f"<table style='width:100%; min-width:640px; border-collapse:collapse; font-size:13.5px; color:{config.TEXT};'>"
        f"<thead><tr style='{CABECALHO_BG()}'>{header_html}</tr></thead>"
        f"<tbody style='text-align:center;'>{''.join(linhas_html)}</tbody>"
        f"</table>"
    )

    html = (
        f"<h4 style='color:{config.TLP_ORANGE}; margin-bottom:6px; text-align:center;'>{titulo}</h4>"
        f"<p style='color:{config.TEXT_MUTED}; font-size:12.5px; margin:-4px 0 8px 0; text-align:center;'>"
        f"Clique num {rotulo_clique} (e depois no item seguinte) para ver os detalhes</p>"
        f"{estilo_expansivel()}"
        f"{wrapper_tabela(tabela)}"
    )

    st.markdown(html, unsafe_allow_html=True)