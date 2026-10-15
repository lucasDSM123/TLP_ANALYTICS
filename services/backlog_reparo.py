"""
Leitura e preparo dos dados da aba "Backlog Reparo".

Os dados são gravados no Neon por upload_backlog_reparo.py (que coleta o
relatório de BD da Vivo). Aqui só lemos e organizamos para a tela.
"""
import unicodedata

import pandas as pd
import streamlit as st
from sqlalchemy import text

import config
from services.database import ler_dados_do_neon
from services.grupos import matriz_producao

TABELA_ATUAL = "backlog_reparo_atual"
TABELA_HISTORICO = "backlog_reparo_historico"

# Ordem de exibição igual à do relatório da Vivo (SC e depois RS); clusters
# que não estiverem aqui entram depois, em ordem alfabética.
ORDEM_CLUSTERS = ["FLORIANOPOLIS", "BLUMENAU", "JOINVILLE", "CHAPECO", "PORTO ALEGRE", "CANOAS"]

_NOMES = {
    "FLORIANOPOLIS": "Florianópolis",
    "CHAPECO": "Chapecó",
    "ITAJAI": "Itajaí",
    "SAO JOSE": "São José",
    "BALNEARIO CAMBORIU": "Balneário Camboriú",
    "FOZ DO IGUACU": "Foz do Iguaçu",
    "MARINGA": "Maringá",
    "CASCAVEL": "Cascavel",
}
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def nome_cluster(cluster: str) -> str:
    """'FLORIANOPOLIS' -> 'Florianópolis' (o relatório da Vivo vem em MAIÚSCULAS, sem acento)."""
    return _NOMES.get(cluster, str(cluster).title())


def ordenar_clusters(clusters) -> list:
    """Ordena os nomes de cluster: primeiro a ordem do relatório, depois alfabética."""
    def chave(c):
        return (ORDEM_CLUSTERS.index(c), "") if c in ORDEM_CLUSTERS else (len(ORDEM_CLUSTERS), c)
    return sorted(set(clusters), key=chave)


@st.cache_data(show_spinner=False, ttl=300)
def carregar_atual() -> pd.DataFrame:
    """Foto atual (só a coleta mais recente de cada tecnologia/empreiteira)."""
    try:
        df = ler_dados_do_neon(TABELA_ATUAL)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    ultima = df.groupby(["tecnologia", "empreiteira"])["coletado_em"].transform("max")
    return df[df["coletado_em"] == ultima].reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=300)
def carregar_historico(dias: int = 120) -> pd.DataFrame:
    """Histórico diário por cluster (últimos `dias` dias)."""
    try:
        df = ler_dados_do_neon(
            f"SELECT * FROM {TABELA_HISTORICO} WHERE data >= CURRENT_DATE - {int(dias)} ORDER BY data"
        )
    except Exception:
        return pd.DataFrame()
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
    return df


def opcoes_filtro(df_atual: pd.DataFrame) -> tuple[list, dict]:
    """Tecnologias disponíveis e, para cada uma, as empreiteiras com dados."""
    if df_atual.empty:
        return [], {}
    tecnologias = sorted(df_atual["tecnologia"].unique())
    por_tec = {t: sorted(df_atual.loc[df_atual["tecnologia"] == t, "empreiteira"].unique()) for t in tecnologias}
    return tecnologias, por_tec


def separar_atual(df_atual: pd.DataFrame, tecnologia: str, empreiteira: str):
    """Devolve (linhas de cluster ordenadas, linha de total ou None) do filtro escolhido."""
    sel = df_atual[(df_atual["tecnologia"] == tecnologia) & (df_atual["empreiteira"] == empreiteira)]
    clusters = sel[~sel["eh_total"]].copy()
    ordem = {c: i for i, c in enumerate(ordenar_clusters(clusters["cluster"]))}
    clusters = clusters.sort_values("cluster", key=lambda s: s.map(ordem)).reset_index(drop=True)
    total = sel[sel["eh_total"]]
    return clusters, (total.iloc[0].to_dict() if not total.empty else None)


def filtrar_historico(df_hist: pd.DataFrame, tecnologia: str, empreiteira: str) -> pd.DataFrame:
    return df_hist[(df_hist["tecnologia"] == tecnologia) & (df_hist["empreiteira"] == empreiteira)]


def acima_da_meta(dias) -> bool:
    return dias is not None and not pd.isna(dias) and float(dias) > config.META_BACKLOG_DIAS


# ---------------------------------------------------------------------
# Tabela "Fila D0" (réplica da planilha de acompanhamento)
# ---------------------------------------------------------------------
def _chave_cluster(nome) -> str:
    """'Florianópolis' / 'FLORIANÓPOLIS' / 'FLORIANOPOLIS' -> 'FLORIANOPOLIS' (casa as duas bases)."""
    sem_acento = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return sem_acento.upper().strip()


def _num(v):
    return None if v is None or pd.isna(v) else float(v)


def montar_fila_d0(clusters: pd.DataFrame, df_prod: pd.DataFrame,
                   entrantes: dict | None = None, enc_da_matriz: bool = False) -> tuple[list[dict], dict | None]:
    """
    Monta as linhas da tabela Fila D0 (uma por cluster + total).

    Do Backlog Reparo (Vivo):
        caixa = total_bd (BDs do dia)        fila = total_dias (backlog em dias)
    Fórmulas (iguais à planilha):
        ritmo = caixa / fila
        meta  = ritmo x config.FATOR_META_BACKLOG
        gap   = meta - caixa
    Da base de produção do site (mesmos números das matrizes):
        esteira    = Esteira da matriz TT: atividades de reparo que ainda restam para tratar
        tt_atrib   = Caixa Tot da matriz TT (atividades já atribuídas / em campo)
        tt_nok     = NOK da matriz TT        tt_proj = Proj. da matriz TT
    Do relatório da Vivo (mesma fonte do Backlog atual):
        enc_bd / enc_tec = encerrados: BDs / técnicos;  enc_pu = BD ÷ TEC
    Projeção de amanhã (só se `entrantes` vier, ver entrante_medio_por_cluster):
        ent_med    = média de BDs que entram no dia da semana de amanhã
        bd_amanha  = caixa atual − projeção TT (encerrados do dia) + ent_med
        fila_amanha = bd_amanha ÷ ritmo (backlog em dias, no ritmo de hoje)
    Linha de total: soma das colunas; fila total = caixa total / ritmo total (como na planilha).

    `enc_da_matriz=True` (usado ao reconstruir um dia que já passou): os encerrados vêm da matriz TT do
    próprio dia em vez do relatório da Vivo — BD = OK, TEC = HC Ativo, PU = OK ÷ HC Ativo.
    """
    tt = {}
    if df_prod is not None and not df_prod.empty and "Cluster" in df_prod.columns:
        m = matriz_producao(df_prod, lado="TT")
        if not m.empty:
            tt = {_chave_cluster(r["Cluster"]): r for r in m.to_dict("records") if r["Cluster"] != "Total"}

    linhas = []
    for r in clusters.to_dict("records"):
        chave = _chave_cluster(r["cluster"])
        caixa, fila = _num(r["total_bd"]), _num(r["total_dias"])
        ritmo = caixa / fila if caixa is not None and fila else None
        meta = ritmo * config.FATOR_META_BACKLOG if ritmo is not None else None

        t = tt.get(chave)
        proj = _num(t["Proj."]) if t else None
        ent_med = entrantes.get(chave, (None, 0))[0] if entrantes else None
        bd_amanha = (max(0.0, caixa - proj + ent_med)
                     if None not in (caixa, proj, ent_med) else None)
        if enc_da_matriz:
            enc_bd = _num(t["OK"]) if t else None
            enc_tec = _num(t["HC Ativo"]) if t else None
            enc_pu = enc_bd / enc_tec if enc_bd is not None and enc_tec else None
        else:
            enc_bd, enc_tec, enc_pu = _num(r.get("enc_bd")), _num(r.get("enc_tec")), _num(r.get("enc_pu"))
        linhas.append({
            "ent_med": ent_med, "bd_amanha": bd_amanha,
            "fila_amanha": bd_amanha / ritmo if bd_amanha is not None and ritmo else None,
            "cluster": r["cluster"], "caixa": caixa, "fila": fila, "ritmo": ritmo, "meta": meta,
            "gap": meta - caixa if meta is not None and caixa is not None else None,
            "esteira": _num(t["Esteira"]) if t else None,
            "enc_bd": enc_bd, "enc_tec": enc_tec, "enc_pu": enc_pu,
            "tt_atrib": _num(t["Caixa Tot"]) if t else None,
            "tt_nok": _num(t["NOK"]) if t else None,
            "tt_proj": _num(t["Proj."]) if t else None,
        })

    if not linhas:
        return [], None
    return linhas, total_fila_d0(linhas)


CAMPOS_FILA = ("caixa", "fila", "ritmo", "meta", "gap", "esteira", "enc_bd", "enc_tec", "enc_pu",
               "tt_atrib", "tt_nok", "tt_proj", "ent_med", "bd_amanha", "fila_amanha")


def total_fila_d0(linhas: list[dict]) -> dict:
    """Linha TOTAL da Fila D0 a partir das linhas dos clusters (também usada nas linhas congeladas)."""
    def soma(campo):
        vals = [l[campo] for l in linhas if l.get(campo) is not None]
        return sum(vals) if vals else None

    total = {campo: soma(campo) for campo in
             ("caixa", "ritmo", "meta", "gap", "esteira", "enc_bd", "enc_tec", "tt_atrib", "tt_nok", "tt_proj",
              "ent_med", "bd_amanha")}
    total["cluster"] = "TOTAL"
    total["enc_pu"] = total["enc_bd"] / total["enc_tec"] if total["enc_bd"] is not None and total["enc_tec"] else None
    total["fila"] = total["caixa"] / total["ritmo"] if total["caixa"] is not None and total["ritmo"] else None
    total["fila_amanha"] = (total["bd_amanha"] / total["ritmo"]
                            if total["bd_amanha"] is not None and total["ritmo"] else None)
    return total


# ---------------------------------------------------------------------
# Segmentações do topo do site (Estado / Cluster) aplicadas ao Vivo
# ---------------------------------------------------------------------
_SOMAS = [
    "enc_bd", "enc_tec", "voz_bd", "bl_bd", "tv_bd", "total_bd", "aberta_massiva", "massiva_analise",
    "total_geral", "pend_agend_reten", "pend_agend", "retencao", "outl_total", "outl_5d", "outl_10d",
    "prod_6d_voz", "prod_6d_bl", "prod_6d_tv",
]


def clusters_permitidos(df_prod: pd.DataFrame, sel_estado, sel_cluster):
    """
    Clusters que sobram depois das segmentações Estado/Cluster do topo (já aplicadas em `df_prod`).
    Devolve None quando nada foi segmentado (= mostrar todos). Os nomes são normalizados porque o
    relatório da Vivo vem sem acento (FLORIANOPOLIS) e a base do site com (FLORIANÓPOLIS).
    """
    if not (sel_estado or sel_cluster):
        return None
    if df_prod is None or df_prod.empty or "Cluster" not in df_prod.columns:
        return set()
    return {_chave_cluster(c) for c in df_prod["Cluster"].dropna().unique()}


def filtrar_clusters(df: pd.DataFrame, permitidos) -> pd.DataFrame:
    if permitidos is None or df.empty:
        return df
    return df[df["cluster"].map(_chave_cluster).isin(permitidos)].reset_index(drop=True)


def total_dos_clusters(clusters: pd.DataFrame, total_site: dict | None, permitidos) -> dict | None:
    """
    Linha de total coerente com a segmentação. Sem segmentação, usa o total oficial do relatório.
    Com segmentação, soma os clusters que sobraram e recalcula os dias (BDs ÷ média produtiva dos
    6 dias úteis = prod_6d/6, mesma regra do site da Vivo). O TMR não dá para somar: com um único
    cluster vale o dele; com vários fica vazio.
    """
    if permitidos is None:
        return total_site
    if clusters.empty:
        return None
    if len(clusters) == 1:
        return clusters.iloc[0].to_dict()

    t = {c: clusters[c].sum(min_count=1) for c in _SOMAS if c in clusters.columns}

    def dias(bd, prod):
        return float(bd) / (float(prod) / 6) if not pd.isna(bd) and not pd.isna(prod) and prod else None

    t["voz_dias"] = dias(t.get("voz_bd"), t.get("prod_6d_voz"))
    t["bl_dias"] = dias(t.get("bl_bd"), t.get("prod_6d_bl"))
    t["tv_dias"] = dias(t.get("tv_bd"), t.get("prod_6d_tv"))
    prods = [t.get(k) for k in ("prod_6d_voz", "prod_6d_bl", "prod_6d_tv")]
    t["total_dias"] = dias(t.get("total_bd"), None if any(pd.isna(p) for p in prods) else sum(prods))
    t["enc_pu"] = t["enc_bd"] / t["enc_tec"] if not pd.isna(t.get("enc_bd")) and t.get("enc_tec") else None
    geral = t.get("total_geral")
    for k in ("outl_total", "outl_5d", "outl_10d"):
        t[f"{k}_pct" if k != "outl_total" else "outl_pct"] = (
            t[k] / geral * 100 if not pd.isna(t.get(k)) and geral else None
        )
    t["tmr"] = None
    t["cluster"] = "TOTAL"
    return t


def historico_segmentado(hist: pd.DataFrame, permitidos) -> pd.DataFrame:
    """Histórico só dos clusters permitidos, com a linha TOTAL recalculada (BD somado; dias = BD ÷ coef somado)."""
    if permitidos is None or hist.empty:
        return hist
    h = hist[(~hist["eh_total"]) & hist["cluster"].map(_chave_cluster).isin(permitidos)].copy()
    if h.empty:
        return h
    tot = h.groupby("data", as_index=False).agg(bd=("bd", "sum"), coef=("coef", "sum"))
    tot["dias"] = tot["bd"] / tot["coef"].where(tot["coef"] > 0)
    tot["cluster"], tot["eh_total"] = "TOTAL", True
    for c in ("tecnologia", "empreiteira"):
        tot[c] = h[c].iloc[0]
    return pd.concat([h, tot], ignore_index=True)


# ---------------------------------------------------------------------
# Entrante médio de BDs por dia da semana
# ---------------------------------------------------------------------
def encerrados_tt_por_dia(df_base: pd.DataFrame) -> tuple[dict, set]:
    """
    Encerrados (OK) do lado TT por cluster e por dia, a partir da base de produção do site
    (mesmo critério do OK_TT da matriz TT: Lado == TT e Status == Concluída).
    Devolve ({(cluster normalizado, data): qtd}, conjunto de datas que existem na base).
    A base só guarda o mês corrente — é daí que vem o limite de histórico.
    """
    if df_base is None or df_base.empty or not {"Data", "Cluster", "Lado", "Status"} <= set(df_base.columns):
        return {}, set()
    datas = pd.to_datetime(df_base["Data"], errors="coerce", dayfirst=True).dt.normalize()
    base = pd.DataFrame({"d": datas, "k": df_base["Cluster"].map(_chave_cluster),
                         "ok": (df_base["Lado"] == "TT") & (df_base["Status"] == "Concluída")})
    base = base.dropna(subset=["d"])
    ok = base[base["ok"]].groupby(["k", "d"]).size()
    return {(k, d): int(n) for (k, d), n in ok.items()}, set(base["d"].unique())


def entrante_medio_por_cluster(hist: pd.DataFrame, encerrados: dict, datas_base: set,
                               hoje: pd.Timestamp, bd_hoje: dict, dia_alvo: int,
                               janela: int = 30) -> dict:
    """
    Média de BDs que ENTRAM por dia, só nos dias da semana == `dia_alvo` (0 = segunda … 6 = domingo).

        entrante(d) = backlog(d) − (backlog(d−1) − encerrados(d−1))

    Ex.: ontem 89 BDs, 40 encerrados → sobram 49; hoje amanheceu com 90 → entraram 41.
    `bd_hoje` ({cluster: BDs agora}) completa o dia de hoje quando o histórico ainda não o tem.
    Só entram na média os dias com backlog de d e d−1 e com o dia d−1 presente na base de produção.
    Devolve {cluster normalizado: (média, nº de ocorrências)}.
    """
    saida = {}
    if hist is None or hist.empty:
        return saida
    h = hist[~hist["eh_total"]]
    inicio = hoje - pd.Timedelta(days=janela - 1)
    for cluster, g in h.groupby("cluster"):
        k = _chave_cluster(cluster)
        serie = {pd.Timestamp(d).normalize(): float(b) for d, b in zip(g["data"], g["bd"]) if not pd.isna(b)}
        if k in bd_hoje and hoje not in serie:
            serie[hoje] = float(bd_hoje[k])
        vals = []
        for d, bd in serie.items():
            ant = d - pd.Timedelta(days=1)
            if d < inicio or d > hoje or d.weekday() != dia_alvo or ant not in serie or ant not in datas_base:
                continue
            vals.append(bd - (serie[ant] - encerrados.get((k, ant), 0)))
        if vals:
            saida[k] = (sum(vals) / len(vals), len(vals))
    return saida


# ---------------------------------------------------------------------
# Congelamento da tabela Fila D0 (linha inteira, por dia e por cluster)
# ---------------------------------------------------------------------
# Enquanto o dia está aberto, a tabela é calculada ao vivo (backlog da Vivo, produção TT, entrante médio
# mudam o tempo todo) e cada cálculo do DIA ATUAL é gravado no Neon, sobrescrevendo o anterior. Na virada
# da meia-noite o último valor gravado fica para sempre: dias anteriores a hoje só LEEM o que foi gravado,
# nunca recalculam — assim dá para comparar a projeção de ontem com o backlog que realmente amanheceu.
#
# Dias que já passaram e NÃO têm fechamento gravado (anteriores ao congelamento) são reconstruídos:
#   Caixa atual / Fila  = backlog do dia na tabela de histórico (medido no início da manhã)
#   Encerrados          = OK / HC Ativo / PU da matriz Produção TT do dia
#   demais colunas      = mesmas fórmulas de sempre, sobre esses valores
TABELA_FILA_D0 = "backlog_reparo_fila_d0"
FUSO = "America/Sao_Paulo"  # o servidor (Streamlit Cloud) roda em UTC; a virada do dia é a de Brasília
_tabela_fila_d0_ok = False


def agora_sp() -> pd.Timestamp:
    """Data/hora atual de Brasília (sem fuso), para decidir o que é "hoje" e o que já virou."""
    return pd.Timestamp.now(tz=FUSO).tz_localize(None)


def _engine():
    from services.database import obter_engine
    return obter_engine()


def criar_tabela_fila_d0(engine=None) -> None:
    """Cria a tabela (idempotente). Mesma definição de sql/backlog_reparo.sql."""
    global _tabela_fila_d0_ok
    engine = engine or _engine()
    colunas = ",\n                ".join(f"{c} double precision" for c in CAMPOS_FILA)
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABELA_FILA_D0} (
                data_ref   date      NOT NULL,
                cluster    text      NOT NULL,
                {colunas},
                gravado_em timestamp,
                PRIMARY KEY (data_ref, cluster)
            )
        """))
    _tabela_fila_d0_ok = True


def gravar_fila_d0(data_ref, linhas: list[dict], agora: pd.Timestamp, engine=None) -> int:
    """
    Grava (upsert) as linhas da Fila D0 do dia `data_ref`. Só aceita o dia de hoje: dias que já
    viraram são imutáveis. Devolve quantas linhas gravou.
    """
    data_ref = pd.Timestamp(data_ref).normalize()
    if data_ref != agora.normalize():
        return 0
    regs = [{"data_ref": data_ref.date(), "cluster": _chave_cluster(l["cluster"]), "gravado_em": agora.to_pydatetime(),
             **{c: _num(l.get(c)) for c in CAMPOS_FILA}} for l in linhas if _num(l.get("caixa")) is not None]
    if not regs:
        return 0
    engine = engine or _engine()
    if not _tabela_fila_d0_ok:
        criar_tabela_fila_d0(engine)
    cols = ("data_ref", "cluster") + CAMPOS_FILA + ("gravado_em",)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {TABELA_FILA_D0} ({", ".join(cols)})
            VALUES ({", ".join(":" + c for c in cols)})
            ON CONFLICT (data_ref, cluster) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in cols[2:])}
        """), regs)
    return len(regs)


def ler_fila_d0(data_ref, engine=None) -> tuple[dict, pd.Timestamp | None]:
    """({cluster normalizado: {campo: valor}}, hora da última gravação) do dia."""
    try:
        engine = engine or _engine()
        with engine.connect() as conn:
            df = pd.read_sql(text(f"SELECT cluster, {', '.join(CAMPOS_FILA)}, gravado_em FROM {TABELA_FILA_D0} "
                                  f"WHERE data_ref = :d"), conn, params={"d": pd.Timestamp(data_ref).date()})
    except Exception:
        return {}, None  # tabela ainda não existe / banco indisponível = "sem fechamento gravado"
    if df.empty:
        return {}, None
    dados = {r["cluster"]: {c: _num(r[c]) for c in CAMPOS_FILA} for r in df.to_dict("records")}
    return dados, pd.to_datetime(df["gravado_em"]).max()


def _clusters_do_historico(clusters: pd.DataFrame, hist: pd.DataFrame, ref: pd.Timestamp) -> pd.DataFrame:
    """Troca o backlog "agora" (Vivo) pelo backlog que o histórico registrou para o dia `ref`."""
    mapa = {}
    if hist is not None and not hist.empty:
        h = hist[(~hist["eh_total"]) & (pd.to_datetime(hist["data"]).dt.normalize() == ref)]
        mapa = {_chave_cluster(c): (b, d) for c, b, d in zip(h["cluster"], h["bd"], h["dias"])}
    base = clusters[["cluster"]].copy().reset_index(drop=True)
    base["total_bd"] = [mapa.get(_chave_cluster(c), (None, None))[0] for c in base["cluster"]]
    base["total_dias"] = [mapa.get(_chave_cluster(c), (None, None))[1] for c in base["cluster"]]
    return base


def fila_d0_do_dia(clusters: pd.DataFrame, df_prod: pd.DataFrame, entrantes: dict | None, hist: pd.DataFrame,
                   data_ref, data_coleta, qtd_datas_sel: int, agora: pd.Timestamp | None = None, engine=None):
    """
    Monta a tabela Fila D0 do dia `data_ref`. Devolve (linhas, total, estado, gravado_em); estado:
      "ao_vivo"      dia de hoje: calculado agora (e gravado, se a tela estiver "limpa")
      "congelado"    dia anterior a hoje com fechamento gravado: valores lidos do Neon
      "reconstruido" dia anterior a hoje sem fechamento gravado: refeito pelo histórico + matriz TT
      "sem_registro" dia anterior a hoje sem fechamento nem histórico: colunas do backlog vazias
    O congelamento/reconstrução só vale com exatamente 1 data selecionada (com várias, a produção TT
    soma os dias e o número não representaria um dia). A gravação só ocorre no dia de hoje, com a
    coleta da Vivo de hoje, exatamente 1 data selecionada.
    """
    agora = agora if agora is not None else agora_sp()
    hoje, ref = agora.normalize(), pd.Timestamp(data_ref).normalize()

    if qtd_datas_sel == 1 and ref < hoje:
        congelado, gravado_em = ler_fila_d0(ref, engine)
        linhas = [{"cluster": nome, **congelado[_chave_cluster(nome)]}
                  for nome in clusters["cluster"] if _chave_cluster(nome) in congelado]
        if linhas:
            return linhas, total_fila_d0(linhas), "congelado", gravado_em
        linhas, total = montar_fila_d0(_clusters_do_historico(clusters, hist, ref), df_prod, entrantes,
                                       enc_da_matriz=True)
        tem_backlog = any(l["caixa"] is not None for l in linhas)
        return linhas, total, ("reconstruido" if tem_backlog else "sem_registro"), None

    linhas, total = montar_fila_d0(clusters, df_prod, entrantes)
    if (qtd_datas_sel == 1 and ref == hoje and pd.Timestamp(data_coleta).normalize() == hoje):
        try:
            gravar_fila_d0(ref, linhas, agora, engine)
        except Exception:
            pass  # gravar é "extra": nunca pode derrubar a tela
    return linhas, total, "ao_vivo", None