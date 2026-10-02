"""
Números CONGELADOS dos fechamentos mensais já fechados, extraídos do
PAINEL do Excel/Power BI — usados como base de comparação mês a mês na
aba "Acumulado Mês" (mês anterior x mês corrente).

Diferente do restante do site, esses valores NÃO são recalculados a partir
da base ao vivo: são uma "foto" fixa de cada mês já fechado (o painel do
Excel pode ter pequenos ajustes/curadoria manual que o cálculo ao vivo do
site não reproduz 1:1, então usamos o número oficial do painel como
referência, não o recálculo do site). O mês corrente continua sendo
calculado normalmente pelos serviços existentes (services.grupos) a partir
dos dados reais.

COMO FUNCIONA A ESCOLHA DO "MÊS ANTERIOR" (automática — não precisa mexer
aqui todo mês):
  `fechamento_mes_anterior(...)` olha a data mais recente da base ao vivo,
  pega o mês ANTERIOR a ela (ex.: base mais recente em Setembro -> mês
  anterior = Agosto) e procura ESSE mês exato no registro `_HISTORICO`
  abaixo. Se o mês exato não estiver cadastrado (ex.: ninguém congelou
  Agosto ainda), a comparação simplesmente não aparece — em vez de cair
  de volta pro último mês cadastrado (Julho), como acontecia antes e
  fazia a tela comparar Setembro com Julho por engano.

QUANDO UM NOVO MÊS FECHAR, o único passo manual é congelar os números
dele aqui:
  1. Adicionar um novo bloco `_<MES>_<ANO>_ESTADO` / `_..._CLUSTER` com os
     valores extraídos do painel fechado.
  2. Registrar esse bloco em `_HISTORICO`, na chave `(ano, mes)` (mês em
     número, 1-12).
Nenhuma outra mudança de código é necessária — a tela passa a comparar
com o mês novo automaticamente assim que a base ao vivo virar o mês.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st


def _normalizar(texto: str) -> str:
    """Normaliza nomes de Estado/Cluster para comparação robusta (maiúsculas,
    sem acento e sem espaços nas pontas) — a grafia exata usada na base ao
    vivo pode variar (ex.: 'Florianópolis' vs 'FLORIANOPOLIS').
    """
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper()


# Cada entrada: eficacia (fração 0-1), concluida, improdutiva, tecnicos
# (soma diária, mesma regra do site), atribuicao e pu (já divididos, 2 casas).

_JULHO_2026_ESTADO = {
    "SC": dict(eficacia=0.76, concluida=7768, improdutiva=2467, tecnicos=2560, atribuicao=4.00, pu=3.03),
    "RS": dict(eficacia=0.69, concluida=5877, improdutiva=2626, tecnicos=1883, atribuicao=4.52, pu=3.12),
}

_JULHO_2026_CLUSTER = {
    "FLORIANOPOLIS": dict(eficacia=0.78, concluida=2796, improdutiva=804, tecnicos=923, atribuicao=3.90, pu=3.03),
    "BLUMENAU":       dict(eficacia=0.74, concluida=1977, improdutiva=697, tecnicos=634, atribuicao=4.22, pu=3.12),
    "JOINVILLE":      dict(eficacia=0.75, concluida=2561, improdutiva=876, tecnicos=807, atribuicao=4.26, pu=3.17),
    "LAGES":          dict(eficacia=0.86, concluida=101,  improdutiva=17,  tecnicos=35,  atribuicao=3.37, pu=2.89),
    "CHAPECO":        dict(eficacia=0.76, concluida=333,  improdutiva=104, tecnicos=134, atribuicao=3.26, pu=2.49),
    "PORTO ALEGRE":   dict(eficacia=0.66, concluida=4096, improdutiva=2097, tecnicos=1379, atribuicao=4.49, pu=2.97),
    "CANOAS":         dict(eficacia=0.77, concluida=1781, improdutiva=529, tecnicos=536, atribuicao=4.31, pu=3.32),
}

# Agosto/2026 — nível Estado e Cluster, ambos confirmados (print do painel
# fechado). Lages não entra mais aqui: a operação lá foi encerrada (== 0
# em Setembro), então não faz sentido comparar contra um mês anterior —
# fica de fora tanto do Estado (o total de SC já é só a soma dos clusters
# ativos) quanto do Cluster (sem entrada = comparação não aparece pra
# Lages, como já acontecia com qualquer grupo sem histórico).
_AGOSTO_2026_ESTADO = {
    "SC": dict(eficacia=0.73, concluida=7040, improdutiva=2639, tecnicos=2396, atribuicao=4.04, pu=2.94),
    "RS": dict(eficacia=0.68, concluida=5750, improdutiva=2659, tecnicos=1832, atribuicao=4.59, pu=3.14),
}

_AGOSTO_2026_CLUSTER = {
    "FLORIANOPOLIS":  dict(eficacia=0.76, concluida=2665, improdutiva=862,  tecnicos=879,  atribuicao=4.01, pu=3.03),
    "BLUMENAU":       dict(eficacia=0.67, concluida=1677, improdutiva=842,  tecnicos=566,  atribuicao=4.45, pu=2.96),
    "JOINVILLE":      dict(eficacia=0.72, concluida=2382, improdutiva=928,  tecnicos=790,  atribuicao=4.19, pu=3.02),
    "CHAPECO":        dict(eficacia=0.71, concluida=287,  improdutiva=120,  tecnicos=131,  atribuicao=3.11, pu=2.19),
    "PORTO ALEGRE":   dict(eficacia=0.64, concluida=3845, improdutiva=2127, tecnicos=1344, atribuicao=4.44, pu=2.86),
    "CANOAS":         dict(eficacia=0.78, concluida=1905, improdutiva=532,  tecnicos=502,  atribuicao=4.85, pu=3.79),
    # LAGES: não cadastrado de propósito — não atuamos mais lá (ver nota acima).
}

# Setembro/2026 — fechamento congelado (prints do painel fechado).
# Estado: números da planilha de Estado (mesma fonte usada em Agosto).
# Cluster: números da planilha de Clusters. Lages fica de fora de propósito
# (operação encerrada — ver nota de Agosto).
_SETEMBRO_2026_ESTADO = {
    "SC": dict(eficacia=0.74, concluida=6872, improdutiva=2392, tecnicos=2257, atribuicao=4.10, pu=3.04),
    "RS": dict(eficacia=0.68, concluida=5880, improdutiva=2704, tecnicos=1905, atribuicao=4.51, pu=3.09),
}

_SETEMBRO_2026_CLUSTER = {
    "FLORIANOPOLIS":  dict(eficacia=0.75, concluida=2669, improdutiva=870,  tecnicos=890,  atribuicao=3.98, pu=3.00),
    "BLUMENAU":       dict(eficacia=0.68, concluida=1778, improdutiva=838,  tecnicos=566,  atribuicao=4.62, pu=3.14),
    "JOINVILLE":      dict(eficacia=0.75, concluida=2140, improdutiva=725,  tecnicos=645,  atribuicao=4.44, pu=3.32),
    "CHAPECO":        dict(eficacia=0.68, concluida=285,  improdutiva=132,  tecnicos=131,  atribuicao=3.18, pu=2.18),
    "PORTO ALEGRE":   dict(eficacia=0.65, concluida=3943, improdutiva=2100, tecnicos=1389, atribuicao=4.35, pu=2.84),
    "CANOAS":         dict(eficacia=0.76, concluida=1935, improdutiva=604,  tecnicos=543,  atribuicao=4.68, pu=3.56),
}

# Setembro/2026 — nível Supervisor. Diferente de Estado/Cluster, NÃO vem do
# painel do Excel: foi gerado a partir da base completa de Setembro com a
# mesma regra de cálculo do site (services.grupos.resumo_mes_por_grupo) e
# congelado aqui. Soma dos supervisores confere com o total de SC + RS.
_SETEMBRO_2026_SUPERVISOR = {
    "ANDERSON LUIS MONTEIRO PORTALLI":   dict(eficacia=0.7673, concluida=1840, improdutiva=558, tecnicos=502, atribuicao=4.78, pu=3.67),
    "BUCKET":                            dict(eficacia=0.7258, concluida=45, improdutiva=17, tecnicos=14, atribuicao=4.43, pu=3.21),
    "DANIEL COSTA":                      dict(eficacia=0.713, concluida=534, improdutiva=215, tecnicos=169, atribuicao=4.43, pu=3.16),
    "EDEQUE DARLON PILON":               dict(eficacia=0.7384, concluida=539, improdutiva=191, tecnicos=207, atribuicao=3.53, pu=2.60),
    "EVERTON COSTA TEIXEIRA":            dict(eficacia=0.7047, concluida=389, improdutiva=163, tecnicos=123, atribuicao=4.50, pu=3.16),
    "JOAO FABIO DOS SANTOS CARDOSO":     dict(eficacia=0.6258, concluida=1067, improdutiva=638, tecnicos=386, atribuicao=4.42, pu=2.76),
    "JOSUE DE LIMA ALVES":               dict(eficacia=0.745, concluida=1151, improdutiva=394, tecnicos=365, atribuicao=4.23, pu=3.15),
    "MARCELO PAVANATI":                  dict(eficacia=0.7537, concluida=554, improdutiva=181, tecnicos=185, atribuicao=3.97, pu=2.99),
    "MARIO ALEJANDRO CATANO":            dict(eficacia=0.7484, concluida=699, improdutiva=235, tecnicos=221, atribuicao=4.23, pu=3.16),
    "ORLANDO MAIA JUNIOR":               dict(eficacia=0.797, concluida=636, improdutiva=162, tecnicos=186, atribuicao=4.29, pu=3.42),
    "PAULO ROBERTO JESUS BRANCO":        dict(eficacia=0.7421, concluida=803, improdutiva=279, tecnicos=268, atribuicao=4.04, pu=3.00),
    "RAFAEL MUNIZ CASTILHO":             dict(eficacia=0.7417, concluida=514, improdutiva=179, tecnicos=178, atribuicao=3.89, pu=2.89),
    "RICARDO SCHVARTZHAUPT":             dict(eficacia=0.6805, concluida=1497, improdutiva=703, tecnicos=487, atribuicao=4.52, pu=3.07),
    "RODRIGO MEREDIGYA GONCALVES":       dict(eficacia=0.6835, concluida=285, improdutiva=132, tecnicos=131, atribuicao=3.18, pu=2.18),
    "THIAGO VINICIUS MODESTO MONTEIRO":  dict(eficacia=0.6925, concluida=491, improdutiva=218, tecnicos=179, atribuicao=3.96, pu=2.74),
    "TIAGO MARLON DOS SANTOS":           dict(eficacia=0.7411, concluida=481, improdutiva=168, tecnicos=140, atribuicao=4.64, pu=3.44),
    "WANDER LOHAN MARCON PEREIRA":       dict(eficacia=0.6494, concluida=1228, improdutiva=663, tecnicos=421, atribuicao=4.51, pu=2.92),
}

# Registro de todos os meses já congelados — chave (ano, mês [1-12]).
# `fechamento_mes_anterior` usa isso pra achar automaticamente o mês
# imediatamente anterior ao mês corrente da base ao vivo; não precisa
# apontar "o mês atual" em lugar nenhum, só cadastrar o mês aqui quando
# ele fechar.
_HISTORICO = {
    (2026, 7): {"rotulo": "JULHO", "estado": _JULHO_2026_ESTADO, "cluster": _JULHO_2026_CLUSTER},
    (2026, 8): {"rotulo": "AGOSTO", "estado": _AGOSTO_2026_ESTADO, "cluster": _AGOSTO_2026_CLUSTER},
    (2026, 9): {"rotulo": "SETEMBRO", "estado": _SETEMBRO_2026_ESTADO, "cluster": _SETEMBRO_2026_CLUSTER,
                "supervisor": _SETEMBRO_2026_SUPERVISOR},
}


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    """(ano, mês) do mês imediatamente anterior a `(ano, mes)`."""
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def mes_referencia_anterior(data_referencia: date = None) -> tuple[int, int]:
    """(ano, mês) do mês que deve ser usado como comparação — o mês
    imediatamente anterior a `data_referencia` (usa hoje se omitido)."""
    ref = data_referencia or date.today()
    return _mes_anterior(ref.year, ref.month)


_ROTULOS_MES = {1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
                7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"}


@st.cache_data(show_spinner=False, ttl=600)
def _congelado_neon(ano: int, mes: int) -> dict | None:
    """Mês congelado AUTOMATICAMENTE na virada (tabela fechamento_congelado do
    Neon — ver services/congelamento_automatico.py). None se não houver."""
    from services.congelamento_automatico import ler_congelado
    return ler_congelado(ano, mes)


def _diario_neon(nome_grupo: str, coluna_grupo: str, ano: int, mes: int) -> pd.DataFrame | None:
    dados = _congelado_neon(ano, mes)
    if not dados:
        return None
    chave = _normalizar(nome_grupo)
    for nome, df in (dados.get(coluna_grupo) or {}).items():
        if _normalizar(nome) == chave:
            return df
    return None


def fechamento_mes_anterior(nome_grupo: str, coluna_grupo: str = "Cluster",
                             data_referencia: date = None) -> dict | None:
    """
    Retorna o fechamento congelado do mês ANTERIOR a `data_referencia`
    (por padrão, o mês anterior a hoje) para um Estado, Cluster ou Supervisor pelo
    nome, ou `None` se esse mês específico ainda não tiver sido congelado
    aqui, ou se o Estado/Cluster não tiver referência cadastrada nele —
    nos dois casos a comparação simplesmente não é exibida, em vez de
    cair para um mês antigo por engano.
    """
    ano, mes = mes_referencia_anterior(data_referencia)
    bloco = _HISTORICO.get((ano, mes))
    chave_tabela = {"Estado": "estado", "Supervisor": "supervisor"}.get(coluna_grupo, "cluster")
    tabela = bloco.get(chave_tabela) if bloco else None

    if tabela is not None:
        # Cadastrado à mão (números oficiais do painel): é a palavra final —
        # inclusive para grupos deixados de fora de propósito (ex.: Lages).
        chave = _normalizar(nome_grupo)
        for nome, valores in tabela.items():
            if _normalizar(nome) == chave:
                return dict(valores)
        return None

    # Plano automático: mês congelado na virada (tabela do Neon).
    diario = _diario_neon(nome_grupo, coluna_grupo, ano, mes)
    if diario is None or diario.empty:
        return None
    from services.grupos import _linha_resumo_soma  # import tardio: evita ciclo
    total = _linha_resumo_soma(nome_grupo, coluna_grupo, diario)
    return dict(eficacia=total["Eficácia"], concluida=int(total["Concluída"]),
                improdutiva=int(total["Improdutiva"]), tecnicos=int(total["Técnicos"]),
                atribuicao=total["Atribuição"], pu=total["PU"])


def rotulo_mes_anterior(data_referencia: date = None) -> str:
    """Rótulo (ex.: 'AGOSTO') do mês usado como comparação, ou string
    vazia se esse mês ainda não tiver sido congelado."""
    ano, mes = mes_referencia_anterior(data_referencia)
    bloco = _HISTORICO.get((ano, mes))
    if bloco:
        return bloco["rotulo"]
    return _ROTULOS_MES[mes] if _congelado_neon(ano, mes) else ""


# ---------------------------------------------------------------------------
# Fechamento DIÁRIO congelado (dia a dia do mês fechado)
# ---------------------------------------------------------------------------
# Um arquivo JSON por mês em services/historico_diario/AAAA-MM.json, gerado
# por `python congelar_mes.py <base.xlsx> <ano> <mês>` (Estado, Cluster e
# Supervisor). É usado na matriz "Fechamento Diário" da aba Acumulado Mês
# para mostrar, ao lado de cada dia do mês atual, o MESMO DIA do mês anterior.
_PASTA_DIARIO = Path(__file__).parent / "historico_diario"

_COLUNAS_DIARIO = {
    "concluida": "Concluída", "improdutiva": "Improdutiva", "tecnicos": "Técnicos",
    "caixa_total": "Caixa Total", "atribuicao": "Atribuição", "pu": "PU", "eficacia": "Eficácia",
}


@lru_cache(maxsize=None)
def _carregar_diario(ano: int, mes: int) -> dict | None:
    arquivo = _PASTA_DIARIO / f"{ano}-{mes:02d}.json"
    if not arquivo.exists():
        return None
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fechamento_diario_mes_anterior(nome_grupo: str, coluna_grupo: str = "Cluster",
                                    data_referencia: date = None) -> pd.DataFrame | None:
    """
    Fechamento diário congelado do mês ANTERIOR a `data_referencia` para um
    Estado, Cluster ou Supervisor. Retorna um DataFrame indexado pelo DIA do
    mês (1–31) com as colunas Concluída, Improdutiva, Técnicos, Caixa Total,
    Atribuição, PU e Eficácia — ou `None` se esse mês não tiver arquivo
    congelado ou o grupo não existir nele.
    """
    ano, mes = mes_referencia_anterior(data_referencia)
    dados = _carregar_diario(ano, mes)  # arquivo JSON cadastrado à mão (vence)
    if dados:
        chave = _normalizar(nome_grupo)
        for nome, dias in (dados.get(coluna_grupo) or {}).items():
            if _normalizar(nome) == chave:
                df = pd.DataFrame.from_dict({int(d): v for d, v in dias.items()}, orient="index")
                return df.rename(columns=_COLUNAS_DIARIO).sort_index()
        return None
    return _diario_neon(nome_grupo, coluna_grupo, ano, mes)  # plano automático