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

import unicodedata
from datetime import date


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

# Registro de todos os meses já congelados — chave (ano, mês [1-12]).
# `fechamento_mes_anterior` usa isso pra achar automaticamente o mês
# imediatamente anterior ao mês corrente da base ao vivo; não precisa
# apontar "o mês atual" em lugar nenhum, só cadastrar o mês aqui quando
# ele fechar.
_HISTORICO = {
    (2026, 7): {"rotulo": "JULHO", "estado": _JULHO_2026_ESTADO, "cluster": _JULHO_2026_CLUSTER},
    (2026, 8): {"rotulo": "AGOSTO", "estado": _AGOSTO_2026_ESTADO, "cluster": _AGOSTO_2026_CLUSTER},
}


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    """(ano, mês) do mês imediatamente anterior a `(ano, mes)`."""
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def mes_referencia_anterior(data_referencia: date = None) -> tuple[int, int]:
    """(ano, mês) do mês que deve ser usado como comparação — o mês
    imediatamente anterior a `data_referencia` (usa hoje se omitido)."""
    ref = data_referencia or date.today()
    return _mes_anterior(ref.year, ref.month)


def fechamento_mes_anterior(nome_grupo: str, coluna_grupo: str = "Cluster",
                             data_referencia: date = None) -> dict | None:
    """
    Retorna o fechamento congelado do mês ANTERIOR a `data_referencia`
    (por padrão, o mês anterior a hoje) para um Estado ou Cluster pelo
    nome, ou `None` se esse mês específico ainda não tiver sido congelado
    aqui, ou se o Estado/Cluster não tiver referência cadastrada nele —
    nos dois casos a comparação simplesmente não é exibida, em vez de
    cair para um mês antigo por engano.
    """
    bloco = _HISTORICO.get(mes_referencia_anterior(data_referencia))
    if not bloco:
        return None
    tabela = bloco["estado"] if coluna_grupo == "Estado" else bloco["cluster"]
    chave = _normalizar(nome_grupo)
    for nome, valores in tabela.items():
        if _normalizar(nome) == chave:
            return dict(valores)
    return None


def rotulo_mes_anterior(data_referencia: date = None) -> str:
    """Rótulo (ex.: 'AGOSTO') do mês usado como comparação, ou string
    vazia se esse mês ainda não tiver sido congelado."""
    bloco = _HISTORICO.get(mes_referencia_anterior(data_referencia))
    return bloco["rotulo"] if bloco else ""
