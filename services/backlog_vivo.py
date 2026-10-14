"""
Coleta do relatório "Relatório de BD - Regional Sul" (site interno da Vivo).

Este módulo SÓ conversa com o site da Vivo e devolve DataFrames prontos —
não grava nada no banco (isso é feito por upload_backlog_reparo.py) e não
importa streamlit, então pode rodar em qualquer máquina na rede corporativa.

Fontes dentro do site:
  1) Backlog.php            -> tabela "Backlog Atual" e tabela "Backlog Histórico"
                               (HTML renderizado pelo servidor).
  2) api_grafico.php        -> JSON com 30 dias (usado só no backfill).

Observações aprendidas olhando o HTML real do servidor:
  • Cada linha da tabela atual tem 24 <td>: 21 visíveis + 3 ocultos
    (display:none) no fim — TOTAL_TV, TOTAL_VOZ, TOTAL_BANDA.
  • A linha de TOTAL (rodapé) é montada pelo JavaScript do site, não vem
    pronta no HTML; por isso ela é calculada aqui em `calcular_total()`.
"""
from __future__ import annotations

import math
import os
import re
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_PADRAO = os.getenv("BACKLOG_VIVO_BASE", "http://10.124.100.224/ProjetosSul/Backlog")
TIMEOUT = 30

# Ordem exata dos <td> de cada linha da tabela "Backlog Atual" (24 colunas;
# as 3 últimas são ocultas no site).
COLUNAS_ATUAL = [
    "cluster", "encerrados_raw",
    "voz_bd", "voz_dias", "bl_bd", "bl_dias", "tv_bd", "tv_dias", "total_bd", "total_dias",
    "tmr", "aberta_massiva", "massiva_analise", "total_geral", "pend_agend_reten",
    "outl_total", "outl_pct", "outl_5d", "outl_5d_pct", "outl_10d", "outl_10d_pct",
    "prod_6d_tv", "prod_6d_voz", "prod_6d_bl",
]
MIN_COLUNAS_VISIVEIS = 21

COLUNAS_INTEIRAS = [
    "voz_bd", "bl_bd", "tv_bd", "total_bd", "aberta_massiva", "massiva_analise",
    "total_geral", "pend_agend_reten", "outl_total", "outl_5d", "outl_10d",
    "prod_6d_tv", "prod_6d_voz", "prod_6d_bl",
    "enc_bd", "enc_tec", "d0", "d1", "d2", "d3_mais", "pend", "pend_agend", "retencao",
]
COLUNAS_DECIMAIS = [
    "voz_dias", "bl_dias", "tv_dias", "total_dias", "outl_pct", "outl_5d_pct", "outl_10d_pct", "enc_pu",
]


# ---------------------------------------------------------------------
# Utilidades de conversão
# ---------------------------------------------------------------------
def num(txt) -> float | None:
    """'1,29' -> 1.29 | '28.9%' -> 28.9 | '33.8 %' -> 33.8 | '1.234,5' -> 1234.5 | '' -> None"""
    if txt is None:
        return None
    t = str(txt).replace("%", "").replace(" ", "").replace("\xa0", "").strip()
    if not t:
        return None
    if "," in t:                          # formato pt-BR: ponto = milhar, vírgula = decimal
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def inteiro(txt) -> int | None:
    v = num(txt)
    return None if v is None else int(round(v))


def tmr_para_horas(tmr: str | None) -> float | None:
    """'46:35' -> 46.583 (o site mostra HH:MM)."""
    m = re.fullmatch(r"\s*(\d+):(\d{2})\s*", tmr or "")
    return int(m[1]) + int(m[2]) / 60 if m else None


def horas_para_tmr(horas: float | None) -> str | None:
    if horas is None or pd.isna(horas):
        return None
    minutos = int(math.floor(horas * 60 + 0.5 + 1e-9))      # meio minuto arredonda pra cima (como o site)
    return f"{minutos // 60}:{minutos % 60:02d}"


# ---------------------------------------------------------------------
# 1) TABELA "BACKLOG ATUAL"
# ---------------------------------------------------------------------
def _linha_atual(tds) -> dict:
    textos = [td.get_text(strip=True) for td in tds]
    textos += [""] * (len(COLUNAS_ATUAL) - len(textos))      # tolera menos colunas ocultas
    bruto = dict(zip(COLUNAS_ATUAL, textos))

    row: dict = {"cluster": bruto["cluster"].strip(), "tmr": bruto["tmr"] or None}
    for col in COLUNAS_ATUAL[2:]:
        if col == "tmr":
            continue
        row[col] = num(bruto[col])

    # "24 /13= 1.8" ou "23 / 17 = 1.4"  ->  BD / TEC = PU
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)\s*=\s*([\d.,]+)", bruto["encerrados_raw"])
    row["enc_bd"], row["enc_tec"], row["enc_pu"] = (int(m[1]), int(m[2]), num(m[3])) if m else (None, None, None)

    # Distribuição escondida nos atributos data-* (tooltips do site)
    td_total = next((td for td in tds if "td-total" in (td.get("class") or [])), None)
    td_pend = next((td for td in tds if "td-pend-retencao" in (td.get("class") or [])), None)
    row["d0"] = inteiro(td_total.get("data-d0")) if td_total else None
    row["d1"] = inteiro(td_total.get("data-d1")) if td_total else None
    row["d2"] = inteiro(td_total.get("data-d2")) if td_total else None
    row["d3_mais"] = inteiro(td_total.get("data-d3")) if td_total else None
    row["pend"] = inteiro(td_total.get("data-pend")) if td_total else None
    row["pend_agend"] = inteiro(td_pend.get("data-pend")) if td_pend else None
    row["retencao"] = inteiro(td_pend.get("data-ret")) if td_pend else None
    return row


def _metadados_atual(soup: BeautifulSoup) -> dict:
    """Relógios do topo da tabela: hora do último BD encerrado e data do BD histórico."""
    meta = {"ultimo_bd_encerrado": None, "bd_historico_ate": None}
    primeira = soup.select_one("#tabela_backlog thead tr")
    if primeira is None:
        return meta
    for th in primeira.find_all("th"):
        t = th.get_text(strip=True)
        if re.fullmatch(r"\d{1,2}:\d{2}", t) and meta["ultimo_bd_encerrado"] is None:
            meta["ultimo_bd_encerrado"] = t
        elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", t):
            meta["bd_historico_ate"] = datetime.strptime(t, "%d/%m/%Y").date()
    return meta


def parse_atual(soup: BeautifulSoup) -> pd.DataFrame:
    linhas = soup.select("#tabela_backlog tbody tr")
    registros = []
    for tr in linhas:
        tds = tr.find_all("td")
        if len(tds) < MIN_COLUNAS_VISIVEIS:
            raise ValueError(
                f"Linha da tabela atual com {len(tds)} <td> (esperado >= {MIN_COLUNAS_VISIVEIS}). "
                "O layout do site mudou — ajuste COLUNAS_ATUAL em services/backlog_vivo.py."
            )
        registros.append(_linha_atual(tds))

    if not registros:
        raise ValueError("Nenhuma linha encontrada em #tabela_backlog (página sem dados ou layout mudou).")

    df = pd.DataFrame(registros)
    meta = _metadados_atual(soup)
    for k, v in meta.items():
        df[k] = v
    df["tmr_horas"] = df["tmr"].map(tmr_para_horas)
    df["eh_total"] = False
    return df


def calcular_total(df: pd.DataFrame, nome: str = "TOTAL") -> dict:
    """
    Linha de total da empreiteira (o rodapé da tabela do site, que é montado
    por JavaScript). Conferido contra o rodapé real em duas coletas:
      • contagens ............ soma dos clusters
      • PU ................... soma(enc_bd) / soma(enc_tec)
      • % outliers ........... outliers / total_geral
      • TMR .................. média simples dos clusters
      • backlog em dias ...... bd / (soma da produção de 6 dias / 6)
    """
    soma = lambda c: df[c].sum(min_count=1)  # noqa: E731

    def dias(bd, prod6):
        return round(bd / (prod6 / 6), 2) if prod6 and not pd.isna(prod6) and not pd.isna(bd) else None

    prod_voz, prod_bl, prod_tv = soma("prod_6d_voz"), soma("prod_6d_bl"), soma("prod_6d_tv")
    prod_all = sum(0 if pd.isna(p) else p for p in (prod_voz, prod_bl, prod_tv))
    total_geral = soma("total_geral")

    def pct(n):
        return round(n / total_geral * 100, 1) if total_geral and not pd.isna(total_geral) else None

    tmr_h = df["tmr_horas"].mean()
    row = {
        "cluster": nome, "eh_total": True,
        "ultimo_bd_encerrado": df["ultimo_bd_encerrado"].iloc[0],
        "bd_historico_ate": df["bd_historico_ate"].iloc[0],
        "tmr_horas": None if pd.isna(tmr_h) else tmr_h, "tmr": horas_para_tmr(tmr_h),
    }
    for c in COLUNAS_INTEIRAS:
        v = soma(c)
        row[c] = None if pd.isna(v) else int(v)
    row["enc_pu"] = round(row["enc_bd"] / row["enc_tec"], 1) if row["enc_tec"] else None
    row["voz_dias"] = dias(row["voz_bd"], prod_voz)
    row["bl_dias"] = dias(row["bl_bd"], prod_bl)
    row["tv_dias"] = dias(row["tv_bd"], prod_tv)
    row["total_dias"] = dias(row["total_bd"], prod_all)
    row["outl_pct"] = pct(row["outl_total"])
    row["outl_5d_pct"] = pct(row["outl_5d"])
    row["outl_10d_pct"] = pct(row["outl_10d"])
    return row


# ---------------------------------------------------------------------
# 2) TABELA "BACKLOG HISTÓRICO"
# ---------------------------------------------------------------------
def parse_historico(soup: BeautifulSoup, clusters_atual: set[str]) -> pd.DataFrame:
    thead = soup.select("#tabela_backlog_hist thead tr")
    if len(thead) < 2:
        raise ValueError("Cabeçalho de #tabela_backlog_hist não encontrado.")

    datas = []
    for th in thead[1].find_all("th")[1:]:
        m = re.search(r"\d{2}/\d{2}/\d{4}", th.get_text())
        if m:
            datas.append(datetime.strptime(m.group(), "%d/%m/%Y").date())

    linhas = soup.select("#tabela_backlog_hist tbody tr")
    registros = []
    for idx, tr in enumerate(linhas):
        tds = tr.find_all("td")
        if len(tds) < 1 + 2 * len(datas):
            continue
        cluster = tds[0].get_text(strip=True)
        # a última linha da tabela é o total da empreiteira (aparece com o nome dela, ex.: "TLP")
        eh_total = idx == len(linhas) - 1 and cluster not in clusters_atual
        for i, data in enumerate(datas):
            td_bd, td_dias = tds[1 + 2 * i], tds[2 + 2 * i]
            bd, dias = inteiro(td_bd.get_text(strip=True)), num(td_dias.get_text(strip=True))
            if bd is None and dias is None:
                continue
            coef = re.search(r"COEFICIENTE:\s*([\d.,]+)", td_dias.get("title", ""))
            registros.append({
                "cluster": "TOTAL" if eh_total else cluster,
                "eh_total": eh_total,
                "data": data,
                "bd": bd,
                "dias": dias,
                "coef": num(coef.group(1)) if coef else None,
                "fonte": "tabela",
            })
    return pd.DataFrame(registros)


# ---------------------------------------------------------------------
# 3) API DO GRÁFICO (30 dias) — usada no backfill
# ---------------------------------------------------------------------
def _datas_do_grafico(labels: list[str], hoje: date) -> list[date]:
    """Os labels vêm como 'dd/mm' (sem ano): assume o ano atual e recua um ano
    quando a data cairia no futuro (virada de ano)."""
    datas = []
    for lb in labels:
        dia, mes = (int(p) for p in lb.split("/")[:2])
        try:
            d = date(hoje.year, mes, dia)
        except ValueError:
            d = date(hoje.year - 1, mes, dia)
        if d > hoje + timedelta(days=1):
            d = date(d.year - 1, mes, dia)
        datas.append(d)
    return datas


def baixar_grafico(sessao: requests.Session, base: str, tecnologia: str, empreiteira: str,
                   *, cluster_group: str = "", cluster: str = "") -> dict:
    params = {"tecnologia": tecnologia, "empreiteira": empreiteira}
    if cluster:
        params["cluster"] = cluster
    else:
        params["clusterGroup"] = cluster_group or "SUL"
    r = sessao.get(f"{base}/api_grafico.php", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError as e:
        raise ValueError(f"api_grafico.php não devolveu JSON (início: {r.text[:200]!r})") from e


def grafico_para_df(payload: dict, nome_cluster: str, eh_total: bool, hoje: date | None = None) -> pd.DataFrame:
    hoje = hoje or date.today()
    labels = payload.get("labels") or []
    return pd.DataFrame({
        "cluster": nome_cluster,
        "eh_total": eh_total,
        "data": _datas_do_grafico(labels, hoje),
        "bd": [inteiro(v) for v in payload.get("bd", [])],
        "dias": [num(v) for v in payload.get("dias", [])],
        "coef": [num(v) for v in payload.get("coef", [])],
        "fonte": "grafico",
    })


def coletar_backfill(sessao: requests.Session, base: str, tecnologia: str, empreiteira: str,
                     aviso=print) -> pd.DataFrame:
    """30 dias de histórico: total (grupo SUL) + cada cluster disponível.
    Falha em um cluster não derruba os demais."""
    total = baixar_grafico(sessao, base, tecnologia, empreiteira, cluster_group="SUL")
    partes = [grafico_para_df(total, "TOTAL", True)]
    for nome in total.get("availableClusters", []):
        nome = (nome or "").strip()
        if not nome:
            continue
        try:
            partes.append(grafico_para_df(
                baixar_grafico(sessao, base, tecnologia, empreiteira, cluster=nome), nome, False))
        except Exception as e:  # noqa: BLE001 — queremos seguir com os outros clusters
            aviso(f"⚠️ Backfill do cluster {nome} falhou: {e!r}")
    return pd.concat(partes, ignore_index=True)


# ---------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------
def coletar(tecnologia: str, empreiteira: str, backfill: bool = False, base: str = BASE_PADRAO,
            aviso=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (atual, historico) já com tecnologia, empreiteira, chave e coletado_em."""
    coletado_em = pd.Timestamp.now().floor("s")
    sessao = requests.Session()

    r = sessao.get(f"{base}/Backlog.php", params={"tecnologia": tecnologia, "empreiteira": empreiteira},
                   timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    clusters = parse_atual(soup)
    atual = pd.concat([clusters, pd.DataFrame([calcular_total(clusters)])], ignore_index=True)
    hist = parse_historico(soup, set(clusters["cluster"]))

    if backfill:
        try:
            graf = coletar_backfill(sessao, base, tecnologia, empreiteira, aviso=aviso)
            # a tabela do site (mais recente) tem prioridade sobre o gráfico no mesmo dia
            hist = pd.concat([hist, graf], ignore_index=True)
            hist = hist.drop_duplicates(subset=["cluster", "data"], keep="first")
        except Exception as e:  # noqa: BLE001
            aviso(f"⚠️ Backfill do gráfico falhou ({e!r}); seguindo só com a tabela do site.")

    for df in (atual, hist):
        df.insert(0, "empreiteira", empreiteira)
        df.insert(0, "tecnologia", tecnologia)
    atual["coletado_em"] = coletado_em      # o histórico não leva data de coleta (ver sql/backlog_reparo.sql)
    atual["chave"] = atual[["tecnologia", "empreiteira", "cluster"]].agg("|".join, axis=1)
    hist["chave"] = (hist["tecnologia"] + "|" + hist["empreiteira"] + "|" + hist["cluster"]
                     + "|" + hist["data"].map(lambda d: d.strftime("%Y-%m-%d")))

    # inteiros "de verdade" (Int64 aceita vazio) — evita '13.0' no COPY para colunas integer do Neon
    for c in COLUNAS_INTEIRAS:
        if c in atual.columns:
            atual[c] = pd.to_numeric(atual[c]).round().astype("Int64")
    hist["bd"] = pd.to_numeric(hist["bd"]).round().astype("Int64")
    return atual, hist
