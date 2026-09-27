"""
Lógica da aba "Alongados" — réplica do que está documentado no modal
"Lógica dos Indicadores" do Backoffice Regional Sul (site da Vivo):

    Alongados = atividades com duração efetiva > 90 min (1h30)
    % de Alongados = Alongadas ÷ Total de Atividades × 100
    Categorias: BA (Instalação) · BD (Reparo) · ME · Serv. Prev. (Serviço) · Preventiva

Diferença consciente em relação ao site da Vivo: lá a duração usa o
snapshot de fechamento (22:45) e considera atividades ainda em campo com
o horário "ao vivo" da consulta. Nossa base (PRODUCAO_TLP_TRATADA) já vem
com 'Início' e 'Término' preenchidos por linha (mesmo para atividades
ainda em campo no momento da extração), então a duração é calculada
diretamente como Término − Início, tratando virada de meia-noite.
Cancelada é excluída (não tem Início/Término preenchido e não representa
trabalho real).
"""

import pandas as pd

LIMIAR_ALONGADA_MIN = 90  # > 90 minutos (1h30) = alongada

# 'Tipo' (coluna já pronta na base) -> categoria exibida na aba, no mesmo
# agrupamento usado pelo site da Vivo. 'DS' (desconexão) fica de fora —
# nunca é considerado alongado, igual à Lógica dos Indicadores do BO.
_TIPO_PARA_CATEGORIA = {
    "DEF": "BD",
    "INST": "BA",
    "ME": "ME",
    "SERV": "Serv. Prev.",
    # Não existe 'Tipo' próprio para Preventiva na base atual (base Zeus
    # marca Preventiva como um Detalhe dentro de DEF) — mantido na lista de
    # categorias por consistência com o site da Vivo; hoje sempre fica 0.
}

CATEGORIAS = ["BA", "BD", "ME", "Serv. Prev.", "Preventiva"]

ROTULO_CATEGORIA = {
    "BA": "Instalação",
    "BD": "Reparo",
    "ME": "ME",
    "Serv. Prev.": "Serviço",
    "Preventiva": "Preventiva",
}

BUCKETS_ORDEM = ["≤1,5h", "≤2,5h", "≤3,5h", "≤4,5h", ">4,5h"]


def _duracao_minutos(inicio, termino):
    """Duração em minutos entre 'Início' e 'Término' (strings 'HH:MM').
    Trata virada de meia-noite (Término menor que Início vira +24h).
    Retorna None se algum dos dois estiver ausente/ilegível."""
    if pd.isna(inicio) or pd.isna(termino):
        return None
    try:
        h1, m1 = (int(x) for x in str(inicio).split(":")[:2])
        h2, m2 = (int(x) for x in str(termino).split(":")[:2])
    except (ValueError, AttributeError, IndexError):
        return None
    minutos = (h2 * 60 + m2) - (h1 * 60 + m1)
    if minutos < 0:
        minutos += 24 * 60
    return minutos


def _bucket_duracao(minutos: float) -> str:
    if minutos <= 90:
        return "≤1,5h"
    if minutos <= 150:
        return "≤2,5h"
    if minutos <= 210:
        return "≤3,5h"
    if minutos <= 270:
        return "≤4,5h"
    return ">4,5h"


def preparar_base(df: pd.DataFrame, categorias: list = None) -> pd.DataFrame:
    """
    Recorte único usado por toda a aba Alongados: categoriza, calcula
    duração e marca quem é alongada. Todo o resto da aba (stats, tabelas
    de cluster, detalhe, ranking) parte deste DataFrame.

    Colunas adicionadas: 'Categoria', 'Duracao_Min', 'Alongada', 'Bucket'
    (Bucket só é preenchido para linhas Alongada == True).
    """
    if df.empty or "Tipo" not in df.columns or "Status" not in df.columns:
        return df.iloc[0:0].copy()

    base = df[df["Status"] != "Cancelada"].copy()
    base["Categoria"] = base["Tipo"].map(_TIPO_PARA_CATEGORIA)
    base = base[base["Categoria"].notna()]

    if categorias:
        base = base[base["Categoria"].isin(categorias)]

    if base.empty:
        base["Duracao_Min"] = pd.Series(dtype=float)
        base["Alongada"] = pd.Series(dtype=bool)
        base["Bucket"] = pd.Series(dtype=object)
        return base

    base["Duracao_Min"] = [
        _duracao_minutos(i, t) for i, t in zip(base.get("Início"), base.get("Término"))
    ]
    base = base[base["Duracao_Min"].notna()]
    base["Alongada"] = base["Duracao_Min"] > LIMIAR_ALONGADA_MIN
    base["Bucket"] = base.apply(
        lambda r: _bucket_duracao(r["Duracao_Min"]) if r["Alongada"] else None, axis=1
    )
    return base


def stats_gerais(base: pd.DataFrame) -> dict:
    """Cards do topo: total de alongadas, % de alongados, total de
    atividades, e contagem de alongadas por turno (manhã/tarde), conforme
    o horário de Início (< 12:00 = manhã)."""
    if base.empty:
        return {"alongadas": 0, "pct": 0.0, "total": 0, "manha": 0, "tarde": 0}

    total = len(base)
    alongadas_df = base[base["Alongada"]]
    alongadas = len(alongadas_df)
    pct = 0.0 if total == 0 else alongadas / total * 100

    def _hora(inicio):
        try:
            return int(str(inicio).split(":")[0])
        except (ValueError, AttributeError, IndexError):
            return None

    horas = alongadas_df["Início"].map(_hora)
    manha = int((horas < 12).sum())
    tarde = int((horas >= 12).sum())

    return {"alongadas": alongadas, "pct": pct, "total": total, "manha": manha, "tarde": tarde}


def tabela_cluster(base: pd.DataFrame) -> tuple:
    """
    Monta as duas tabelas 'por Cluster': Contagem (nº de alongadas por
    faixa de duração) e Percentual (idem ÷ total de atividades do
    cluster naquele recorte × 100). Retorna (contagem_df, percentual_df),
    cada uma já com a linha TOTAL no final.
    """
    if base.empty or "Cluster" not in base.columns:
        vazio = pd.DataFrame(columns=["Cluster"] + BUCKETS_ORDEM + ["Total"])
        return vazio, vazio

    total_por_cluster = base.groupby("Cluster").size()

    alongadas = base[base["Alongada"]]
    pivot = (
        alongadas.pivot_table(index="Cluster", columns="Bucket", values="Duracao_Min", aggfunc="count")
        .reindex(columns=BUCKETS_ORDEM)
        .fillna(0)
        .astype(int)
    )
    # Garante que todo cluster do recorte apareça, mesmo sem nenhuma alongada
    pivot = pivot.reindex(total_por_cluster.index).fillna(0).astype(int)
    pivot["Total"] = pivot[BUCKETS_ORDEM].sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False)

    linha_total = pivot[BUCKETS_ORDEM + ["Total"]].sum()
    contagem = pivot.reset_index()
    contagem.loc[len(contagem)] = ["TOTAL"] + linha_total.tolist()

    percentual = pivot[BUCKETS_ORDEM + ["Total"]].div(total_por_cluster, axis=0) * 100
    percentual = percentual.reset_index()
    total_geral_ativ = total_por_cluster.sum()
    linha_total_pct = (linha_total / total_geral_ativ * 100) if total_geral_ativ else linha_total * 0
    percentual.loc[len(percentual)] = ["TOTAL"] + linha_total_pct.tolist()

    return contagem, percentual


def detalhe_alongadas(base: pd.DataFrame) -> pd.DataFrame:
    """Tabela 'Detalhe das Atividades': só as alongadas, ordenadas da mais
    longa pra mais curta (mesmo critério do site da Vivo)."""
    if base.empty:
        return base

    cols_disponiveis = [
        c for c in [
            "Cluster", "Cidade", "Login Técnico", "Técnico", "Contratada",
            "Ordem de Serviço", "Categoria", "Segmento", "Status",
            "Duracao_Min", "Início", "Término",
        ]
        if c in base.columns
    ]
    detalhe = base[base["Alongada"]][cols_disponiveis].copy()
    if detalhe.empty:
        return detalhe

    detalhe["Categoria"] = detalhe["Categoria"].map(lambda c: ROTULO_CATEGORIA.get(c, c))
    detalhe["Duração"] = detalhe["Duracao_Min"].map(lambda m: f"{int(m // 60)}h {int(m % 60):02d}min")
    detalhe["Início / Fim"] = detalhe["Início"].astype(str) + " - " + detalhe["Término"].astype(str)
    detalhe = detalhe.sort_values("Duracao_Min", ascending=False)
    detalhe = detalhe.drop(columns=["Duracao_Min", "Início", "Término"])
    return detalhe


def ranking_tecnicos(base: pd.DataFrame) -> pd.DataFrame:
    """
    Ranking de técnicos por nº de alongadas, com:
      - Alon.: total de atividades alongadas do técnico no recorte
      - Concl./Dia: concluídas ÷ nº de dias distintos presentes no recorte
        (técnico-dia, mesmo princípio usado no restante do site para PU)
      - Total Ativ.: total de atividades do técnico no recorte (já sem
        Cancelada e já filtrado pelas categorias selecionadas)
      - % Alon.: Alon. ÷ Total Ativ. × 100
      - Dur. Média: duração média das atividades ALONGADAS do técnico
    """
    col_tec = "Login Técnico" if "Login Técnico" in base.columns else "Técnico"
    if base.empty or col_tec not in base.columns:
        return pd.DataFrame(columns=["Login", "Cluster", "Alon.", "Concl./Dia", "Total Ativ.", "% Alon.", "Dur. Média"])

    n_dias = base["Data"].nunique() if "Data" in base.columns else 1
    n_dias = max(n_dias, 1)

    linhas = []
    for login, sub in base.groupby(col_tec):
        if pd.isna(login) or str(login).upper().startswith("BKT"):
            continue
        alon_sub = sub[sub["Alongada"]]
        n_alon = len(alon_sub)
        if n_alon == 0:
            continue
        total_ativ = len(sub)
        concluidas = int((sub["Status"] == "Concluída").sum())
        cluster = sub["Cluster"].mode().iat[0] if "Cluster" in sub.columns and not sub["Cluster"].mode().empty else "-"
        linhas.append({
            "Login": login,
            "Cluster": cluster,
            "Alon.": n_alon,
            "Concl./Dia": round(concluidas / n_dias, 2),
            "Total Ativ.": total_ativ,
            "% Alon.": round(n_alon / total_ativ * 100, 1) if total_ativ else 0.0,
            "Dur. Média": round(alon_sub["Duracao_Min"].mean(), 0),
        })

    ranking = pd.DataFrame(linhas)
    if ranking.empty:
        return ranking
    ranking = ranking.sort_values("Alon.", ascending=False).reset_index(drop=True)
    ranking["Dur. Média"] = ranking["Dur. Média"].map(lambda m: f"{int(m // 60)}h {int(m % 60):02d}min")
    return ranking
