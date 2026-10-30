"""
Aba "Atribuição": quantos técnicos (HC) são necessários para atender a demanda
de hoje (D0) e dos próximos dois dias (D+1, D+2).

Reproduz a planilha "Planejamento_Presença_D0" (abas RS e SC):

    • Demanda  = nº de atividades por BUCKET e HORÁRIO (08H30, 09H30, 10H30, 14H,
                 15H, 16H e SLA = atividade sem janela definida), contando só os
                 recursos definidos em REGRAS[estado]["contar_demanda"] (TLP e
                 BUCKET TLP — mesma base tratada do Dashboard) e ignorando as
                 atividades Canceladas e Suspensas (STATUS_IGNORADOS).
    • HC       = técnicos TLP DISTINTOS com atividade no bucket naquele dia.
    • HC NEC   = ROUNDUP(demanda / 4)        (4 atividades por técnico/dia —
                 config.META_ATRIBUICAO_ALVO)
    • GAP      = ROUNDDOWN(demanda / 4 - HC)  (negativo = sobra de técnicos).
    • Atribuição = demanda / HC (atividades por técnico hoje).

Os dados vêm da tabela `atribuicao_atividades` (gravada pelo upload_atribuicao.py,
a partir dos arquivos que o atribuição.py baixa do OFSC).
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from services.database import ler_dados_do_neon

TABELA = "atribuicao_atividades"
MAPEAMENTO_PADRAO = Path("data") / "Mapeamento_Atribuicao.xlsx"
FUSO = "America/Sao_Paulo"

HORARIOS = ["08H30", "09H30", "10H30", "14H", "15H", "16H", "SLA"]
ATIVIDADES_POR_HC = config.META_ATRIBUICAO_ALVO  # 4 atividades por técnico/dia
# Capacidade por HORÁRIO (célula de cada janela do quadro): um técnico atende 1 atividade por
# janela. O GAP do horário = atividades - HC do horário (positivo = faltam técnicos naquele
# horário). A planilha só tem GAP por dia (4 atividades/técnico); este é novo.
ATIVIDADES_POR_HC_HORARIO = 1
CONTAR_HC = {"TLP"}  # só técnico TLP entra no HC (bucket/Vivo/RS Telecom não)

# Quem entra na DEMANDA em cada estado. Igual ao Dashboard, que lê a base Zeus já tratada
# (só o que é nosso: Contratada = TLP e BUCKET TLP), tanto no SC quanto no RS. A planilha
# antiga somava também VIVO e RS TELECOM no SC; pra voltar a esse comportamento, inclua
# "VIVO" e "RS TELECOM" no conjunto do SC.
# GAP: "baixo" = ROUNDDOWN (trunca em direção a zero) — é o que a planilha usa no RS
# inteiro e em Joinville/Chapecó/Lages. Só Blumenau e Florianópolis (SC) usam ROUNDUP
# na planilha, o que parece sobra de edição; aqui ficou tudo igual. Pra voltar ao
# comportamento da planilha, troque para "cima".
REGRAS = {
    "RS": {"contar_demanda": {"TLP", "BUCKET TLP"}, "gap": "baixo"},
    "SC": {"contar_demanda": {"TLP", "BUCKET TLP"}, "gap": "baixo"},
}

# Status que não contam (o Dashboard também desconta: CAIXA TOTAL = total - Suspensa - Cancelada).
STATUS_IGNORADOS = {"CANCELADA", "CANCELADO", "SUSPENSA", "SUSPENSO"}

# O OFSC às vezes traz o estado por extenso; normaliza para a sigla usada em REGRAS.
ESTADOS_SIGLA = {
    "SANTA CATARINA": "SC",
    "RIO GRANDE DO SUL": "RS",
    "PARANA": "PR",
}
COLUNAS_STATUS = ("Status", "Status da Atividade")

# Ordem/agrupamento das linhas (cluster -> buckets), igual às abas da planilha.
LAYOUT = {
    "RS": [
        ("CANOAS", ["ALVORADA", "CACHOEIRINHA", "CANOAS", "ESTEIO", "GRAVATAI"]),
        ("PORTO ALEGRE", ["PORTO ALEGRE", "VIAMAO"]),
    ],
    "SC": [
        ("BLUMENAU", ["BLUMENAU", "CAMBORIU", "ITAJAI", "NAVEGANTES", "BRUSQUE", "RIO DO SUL", "POMERODE"]),
        ("FLORIANOPOLIS", ["BGC / SOO / PAC", "IMA / GRP", "CUA / YCA", "TUBARAO"]),
        ("JOINVILLE", ["JOINVILLE", "MAFRA", "SAO BENTO DO SUL", "JARAGUA DO SUL"]),
        ("CHAPECÓ", ["CHAPECO", "CAPINZAL", "CONCORDIA", "FRAIBURGO"]),
        ("LAGES", ["LAGES"]),
    ],
}

SEM_CADASTRO = "SEM CADASTRO"


# ------------------------------------------------------------------
# Preparo (usado pelo upload_atribuicao.py)
# ------------------------------------------------------------------

def _norm(valor) -> str:
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor).strip().upper()


def _sem_acento(valor) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", _norm(valor)) if unicodedata.category(c) != "Mn")


def _sigla_estado(valor) -> str:
    """SANTA CATARINA / Santa Catarina -> SC; RIO GRANDE DO SUL -> RS; PARANÁ -> PR; o resto fica igual."""
    v = _sem_acento(valor)
    return ESTADOS_SIGLA.get(v, v)


def _ativas(df: pd.DataFrame) -> pd.DataFrame:
    """Tira as atividades Canceladas/Suspensas (se a coluna status existir — dados antigos não têm)."""
    if "status" not in df.columns:
        return df
    return df[~df["status"].map(_sem_acento).isin(STATUS_IGNORADOS)]


def carregar_mapeamento(caminho: str | Path = MAPEAMENTO_PADRAO) -> dict:
    """Lê as tabelas de apoio (as mesmas da aba PROCV da planilha):
    Cidades (cidade -> cluster/bucket), Janelas (janela -> horário) e
    Recursos (técnico/bucket -> TLP, VIVO, RS TELECOM, BUCKET TLP...)."""
    cid = pd.read_excel(caminho, sheet_name="Cidades")
    jan = pd.read_excel(caminho, sheet_name="Janelas")
    rec = pd.read_excel(caminho, sheet_name="Recursos")

    cidades: dict[str, tuple[str, str]] = {}
    for r in cid.itertuples(index=False):
        cidades.setdefault(_norm(r.CIDADE), (str(r.CLUSTER).strip(), str(r.BUCKET).strip()))
    janelas = {str(r.JANELA).strip(): str(r.TIME).strip() for r in jan.itertuples(index=False)}
    recursos: dict[str, str] = {}
    for r in rec.itertuples(index=False):  # 1ª ocorrência vence (igual ao PROCV/VLOOKUP)
        recursos.setdefault(_norm(r.RECURSO), _norm(r.CONTAR))
    return {"cidades": cidades, "janelas": janelas, "recursos": recursos}


def preparar_atividades(raw: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Do relatório bruto do OFSC (uma linha por atividade) para o formato enxuto
    usado na aba: dia, estado, recurso, cidade, cluster, bucket, janela, horario, contar."""
    obrigatorias = ["Recurso", "Janela de Serviço", "Cidade", "Estado", "Data Agendada para Execução"]
    faltando = [c for c in obrigatorias if c not in raw.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes no relatório do OFSC: {faltando}")

    out = pd.DataFrame(index=raw.index)
    out["dia"] = pd.to_datetime(raw["Data Agendada para Execução"], errors="coerce", dayfirst=True).dt.date
    out["estado"] = raw["Estado"].map(_sigla_estado)
    col_status = next((c for c in COLUNAS_STATUS if c in raw.columns), None)
    out["status"] = raw[col_status].fillna("").astype(str).str.strip() if col_status else ""
    out["recurso"] = raw["Recurso"].fillna("").astype(str).str.strip()
    out["cidade"] = raw["Cidade"].map(_norm)
    out["janela"] = raw["Janela de Serviço"].fillna("").astype(str).str.strip()
    # Janela fora da tabela (ou vazia) = SLA, igual ao IFERROR(..., "SLA") da planilha.
    out["horario"] = out["janela"].map(mapa["janelas"]).fillna("SLA")
    out["contar"] = out["recurso"].map(lambda r: mapa["recursos"].get(_norm(r), SEM_CADASTRO))
    cb = out["cidade"].map(mapa["cidades"])
    out["cluster"] = cb.map(lambda t: t[0] if isinstance(t, tuple) else "")
    out["bucket"] = cb.map(lambda t: t[1] if isinstance(t, tuple) else "")
    return out[out["dia"].notna()].reset_index(drop=True)


# ------------------------------------------------------------------
# Leitura (site)
# ------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=300)
def carregar_atividades() -> pd.DataFrame:
    """Atividades dos próximos dias gravadas no Neon (vazio se ainda não houve upload)."""
    try:
        df = ler_dados_do_neon(TABELA)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    df["dia"] = pd.to_datetime(df["dia"], errors="coerce").dt.date
    df["estado"] = df["estado"].map(_sigla_estado)  # linhas gravadas antes da normalização
    return df.dropna(subset=["dia"])


def hoje_local():
    return pd.Timestamp.now(tz=FUSO).tz_localize(None).date()


def rotulo_dia(dia) -> str:
    """D0 / D+1 / D+2 em relação a hoje (fuso de Brasília)."""
    delta = (dia - hoje_local()).days
    return "D0" if delta == 0 else (f"D+{delta}" if delta > 0 else f"D{delta}")


# ------------------------------------------------------------------
# Cálculo
# ------------------------------------------------------------------

def _arredonda_gap(valor: float, modo: str) -> int:
    # Mesmo comportamento do Excel: ROUNDDOWN trunca em direção a zero;
    # ROUNDUP afasta de zero.
    if modo == "baixo":
        return math.trunc(valor)
    return int(math.copysign(math.ceil(abs(valor)), valor)) if valor else 0


def _gap_horario(atividades: int, hc: int) -> int:
    return int(math.ceil(atividades / ATIVIDADES_POR_HC_HORARIO)) - int(hc)


def _linha(tipo: str, cluster: str, bucket: str, vals: list[int], hc: int, gap_modo: str,
           hc_horario: list[int]) -> dict:
    total = int(sum(vals))
    esperado = total / ATIVIDADES_POR_HC
    linha = {"tipo": tipo, "cluster": cluster, "bucket": bucket}
    linha.update(dict(zip(HORARIOS, (int(v) for v in vals))))
    for h, v, hc_h in zip(HORARIOS, vals, hc_horario):
        linha[f"HC_{h}"] = int(hc_h)
        linha[f"GAP_{h}"] = _gap_horario(int(v), int(hc_h))
    linha.update({
        "TOTAL": total,
        "HC": int(hc),
        "GAP": _arredonda_gap(esperado - hc, gap_modo),
        "HC_NEC": int(math.ceil(esperado)),
        "ATRIB": (total / hc) if hc else 0.0,
    })
    return linha


def _somar(tipo: str, cluster: str, filhos: list[dict], hc_distinto: int | None = None) -> dict:
    linha = {"tipo": tipo, "cluster": cluster, "bucket": ""}
    colunas_horario = [f"{p}_{h}" for h in HORARIOS for p in ("HC", "GAP")]
    for col in HORARIOS + colunas_horario + ["TOTAL", "HC", "GAP", "HC_NEC"]:
        linha[col] = int(sum(f[col] for f in filhos))
    if hc_distinto is not None:
        duplicados = linha["HC"] - int(hc_distinto)
        linha["HC"] = int(hc_distinto)
        linha["GAP"] += duplicados
    linha["ATRIB"] = (linha["TOTAL"] / linha["HC"]) if linha["HC"] else 0.0
    return linha


def calcular_quadro(ativ_dia: pd.DataFrame, estado: str) -> pd.DataFrame:
    """Quadro de um estado num dia: uma linha por bucket, subtotal por cluster e
    TOTAL GERAL. Colunas: tipo (bucket|cluster|geral), cluster, bucket, HORARIOS...,
    TOTAL, HC, GAP, HC_NEC, ATRIB."""
    regra = REGRAS[estado]
    a = ativ_dia[ativ_dia["estado"] == estado]
    ativas = _ativas(a)
    demanda = ativas[ativas["contar"].isin(regra["contar_demanda"])]
    # HC total: igual ao Dashboard, que conta o técnico mesmo que só tenha atividade cancelada/suspensa.
    tecnicos = a[a["contar"].isin(CONTAR_HC)].assign(_k=lambda d: d["recurso"].map(_norm))
    # HC por janela: só quem tem atividade ativa naquela janela.
    tecnicos_ativos = ativas[ativas["contar"].isin(CONTAR_HC)].assign(_k=lambda d: d["recurso"].map(_norm))

    cont = (demanda.groupby(["bucket", "horario"]).size().unstack(fill_value=0)
            .reindex(columns=HORARIOS, fill_value=0))
    hcs = tecnicos.groupby("bucket")["_k"].nunique()
    # HC por horário: técnicos TLP distintos com atividade naquela janela, no bucket.
    hcs_horario = (tecnicos_ativos.groupby(["bucket", "horario"])["_k"].nunique().unstack(fill_value=0)
                   .reindex(columns=HORARIOS, fill_value=0))

    linhas: list[dict] = []
    buckets_linhas: list[dict] = []
    for cluster, buckets in LAYOUT[estado]:
        filhos = []
        for b in buckets:
            vals = [cont.loc[b, h] if b in cont.index else 0 for h in HORARIOS]
            hc_h = [hcs_horario.loc[b, h] if b in hcs_horario.index else 0 for h in HORARIOS]
            filhos.append(_linha("bucket", cluster, b, vals, int(hcs.get(b, 0)), regra["gap"], hc_h))
        hc_cluster = tecnicos.loc[tecnicos["bucket"].isin(buckets), "_k"].nunique()
        linhas += filhos + [_somar("cluster", cluster, filhos, hc_cluster)]
        buckets_linhas += filhos
    todos_buckets = [b for _, bs in LAYOUT[estado] for b in bs]
    hc_geral = tecnicos.loc[tecnicos["bucket"].isin(todos_buckets), "_k"].nunique()
    linhas.append(_somar("geral", "TOTAL GERAL", buckets_linhas, hc_geral))
    return pd.DataFrame(linhas)


def fora_do_quadro(ativ_dia: pd.DataFrame, estado: str) -> pd.DataFrame:
    """Atividades que contam na demanda mas caem num bucket que NÃO aparece no quadro
    (a planilha também as ignora em silêncio) — ex.: cidade sem bucket cadastrado."""
    regra = REGRAS[estado]
    a = _ativas(ativ_dia)
    a = a[(a["estado"] == estado) & a["contar"].isin(regra["contar_demanda"])]
    no_quadro = {b for _, bs in LAYOUT[estado] for b in bs}
    f = a[~a["bucket"].isin(no_quadro)]
    if f.empty:
        return pd.DataFrame(columns=["bucket", "cidade", "atividades"])
    return (f.assign(bucket=f["bucket"].replace("", "(cidade sem bucket)"))
            .groupby(["bucket", "cidade"]).size().reset_index(name="atividades")
            .sort_values("atividades", ascending=False))


def recursos_sem_cadastro(ativ_dia: pd.DataFrame) -> pd.DataFrame:
    """Técnicos que não estão na tabela de Recursos — a planilha dá #N/A e a atividade
    some da contagem sem aviso."""
    f = _ativas(ativ_dia)
    f = f[f["contar"] == SEM_CADASTRO]
    if f.empty:
        return pd.DataFrame(columns=["recurso", "estado", "atividades"])
    return (f.groupby(["recurso", "estado"]).size().reset_index(name="atividades")
            .sort_values("atividades", ascending=False))