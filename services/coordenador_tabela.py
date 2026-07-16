import pandas as pd

import config
from services.indicadores import Indicadores


def _linha_metricas(sub: pd.DataFrame, nome: str) -> dict:
    """
    Calcula todas as métricas de uma linha da tabela (seja linha de
    Supervisor ou linha de subtotal do Coordenador), reaproveitando a
    classe Indicadores para bater com o resto do site.

    META = HC Ativo * config.META_PU_ALVO (cada técnico deve concluir
    META_PU_ALVO atividades). GAP = Concluída Total (BA+TT) - META —
    confirmado contra a planilha original célula a célula.
    """
    ind = Indicadores(sub)

    hc = ind.hc_real()["HC"]
    caixa = ind.caixa_total()["TOTAL"]
    esteira = ind.esteira()["TOTAL"]
    media_atrib = ind.media_atribuicao()["GERAL"]
    pu = ind.pu()["GERAL"]
    concluido = ind.concluido()
    eficacia = ind.eficacia()["GERAL"]
    projecao = ind.projecao()["GERAL"]
    projecao_pu = ind.projecao_pu()["GERAL"]
    iniciada = ind.iniciada()["TOTAL"]

    ok_ba = int(((sub["Status"] == "Concluída") & (sub["Lado"] == "BA")).sum()) if "Lado" in sub.columns else 0
    ok_tt = int(((sub["Status"] == "Concluída") & (sub["Lado"] == "TT")).sum()) if "Lado" in sub.columns else 0
    ok_total = ok_ba + ok_tt

    meta = hc * config.META_PU_ALVO
    gap = ok_total - meta

    return {
        "Nome": nome,
        "HC Ativo": hc,
        "Caixa Total": caixa,
        "Esteira": esteira,
        "Média Atribuição": media_atrib,
        "PU": pu,
        "Concluída BA": ok_ba,
        "Concluída TT": ok_tt,
        "Não Concluída": concluido["NOK"],
        "Iniciada": iniciada,
        "Eficácia": eficacia,
        "Projeção": projecao,
        "Projeção PU": projecao_pu,
        "Meta": meta,
        "Gap": gap,
    }


def tabela_coordenadores(df: pd.DataFrame) -> list[dict]:
    """
    Monta a estrutura hierárquica Coordenador -> Supervisores -> subtotal,
    igual à tabela "PRODUÇÃO POR COORDENADOR" do Power BI/Excel.

    Retorna uma lista de grupos:
    [{"coordenador": str, "supervisores": [linha, ...], "subtotal": linha}, ...]
    """
    obrigatorias = {"Coordenador", "Supervisor", "Status", "Cluster"}
    if df.empty or not obrigatorias.issubset(df.columns):
        return []

    grupos = []
    coordenadores = sorted(c for c in df["Coordenador"].dropna().unique() if c != "BUCKET")

    for coordenador in coordenadores:
        sub_coord = df[df["Coordenador"] == coordenador]

        supervisores = []
        for supervisor in sorted(sub_coord["Supervisor"].dropna().unique()):
            sub_sup = sub_coord[sub_coord["Supervisor"] == supervisor]
            if sub_sup.empty:
                continue
            supervisores.append(_linha_metricas(sub_sup, supervisor))

        if not supervisores:
            continue

        clusters = frozenset(sub_coord["Cluster"].dropna().unique())
        rotulo_subtotal = config.SIGLAS_CLUSTER.get(clusters, "TOTAL")
        subtotal = _linha_metricas(sub_coord, rotulo_subtotal)

        grupos.append({"coordenador": coordenador, "supervisores": supervisores, "subtotal": subtotal})

    return grupos
