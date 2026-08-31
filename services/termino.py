"""
Indicador de Término — mesma lógica do indicador de Chegada
(services/chegada.py), só que comparando o horário real de TÉRMINO contra
o FECHAMENTO da Janela de Serviço, em vez do horário de Início contra a
ABERTURA da Janela.

    Janela (ex.: "08:30 - 10:30") x Término (ex.: "10:45")
    -> DENTRO (Término cai dentro da tolerância em volta do fechamento)
    -> FORA   (Término é bem antes ou bem depois do fechamento da Janela)

Reaproveita os parsers e helpers de tempo já existentes em chegada.py (não
duplica a lógica de "converter texto em horário", "formatar minutos" etc.).
"""

from datetime import datetime, time, timedelta

import pandas as pd

from services.chegada import (
    COL_JANELA,
    COL_STATUS,
    COL_DATA,
    STATUS_EXCLUIDOS,
    STATUS_DENTRO,
    STATUS_ANTES,
    STATUS_DEPOIS,
    STATUS_SEM_REGISTRO,
    STATUS_INDEFINIDO,
    STATUS_AGUARDANDO,
    _parse_hora,
    parse_janela,
    _para_datetime,
    _e_hoje,
    _minutos_desde_meianoite,
    _formatar_minutos_como_hora,
    _formatar_duracao,
    _horario_mais_frequente,
)

COL_TERMINO = "Término"

# Tolerâncias espelhadas do indicador de Chegada (TOLERANCIA_ATRASO /
# TOLERANCIA_ANTECIPACAO em chegada.py), só que aplicadas ao FECHAMENTO da
# Janela em vez da abertura: o técnico pode terminar até
# TOLERANCIA_ATRASO_TERMINO depois do fechamento, ou até
# TOLERANCIA_ANTECIPACAO_TERMINO antes dele, que ainda conta como "Dentro".
TOLERANCIA_ATRASO_TERMINO = timedelta(minutes=30)
TOLERANCIA_ANTECIPACAO_TERMINO = timedelta(minutes=60)

STATUS_COL = "Status Término"


def classificar_termino(janela, termino_real, data_os=None, agora: datetime | None = None) -> str:
    """Classifica uma OS em Dentro / Antes / Depois / Aguardando / Sem Registro / Indefinido
    com base no horário de Término frente ao fechamento da Janela (ver módulo)."""
    hora_termino = _parse_hora(termino_real)
    if hora_termino is None:
        return STATUS_SEM_REGISTRO

    if agora is not None and _e_hoje(data_os, agora):
        if _para_datetime(hora_termino) > _para_datetime(time(agora.hour, agora.minute)):
            return STATUS_AGUARDANDO

    janela_ini, janela_fim = parse_janela(janela)
    if janela_ini is None or janela_fim is None:
        return STATUS_INDEFINIDO
    if janela_fim < janela_ini:
        return STATUS_INDEFINIDO

    termino_dt = _para_datetime(hora_termino)
    janela_ini_dt = _para_datetime(janela_ini)
    janela_fim_dt = _para_datetime(janela_fim)

    # o limite de antecipação nunca ultrapassa o início da própria janela
    limite_antecipacao_dt = max(janela_fim_dt - TOLERANCIA_ANTECIPACAO_TERMINO, janela_ini_dt)
    limite_atraso_dt = janela_fim_dt + TOLERANCIA_ATRASO_TERMINO

    if termino_dt < limite_antecipacao_dt:
        return STATUS_ANTES
    if termino_dt > limite_atraso_dt:
        return STATUS_DEPOIS
    return STATUS_DENTRO


def calcular_indicador_termino(df: pd.DataFrame, agora: datetime | None = None) -> pd.DataFrame:
    """Recebe o dataframe base (com Janela e Término) e devolve uma cópia
    com a coluna adicional "Status Término". Mesmas exclusões de Status
    (Cancelada / Não Iniciada / em rota) do indicador de Chegada."""
    if agora is None:
        agora = datetime.now()

    df = df.copy()

    if COL_STATUS in df.columns:
        df = df[~df[COL_STATUS].isin(STATUS_EXCLUIDOS)]

    if COL_JANELA not in df.columns or COL_TERMINO not in df.columns:
        df[STATUS_COL] = STATUS_INDEFINIDO
        return df

    coluna_data = df[COL_DATA] if COL_DATA in df.columns else [None] * len(df)
    df[STATUS_COL] = [
        classificar_termino(j, t, d, agora)
        for j, t, d in zip(df[COL_JANELA], df[COL_TERMINO], coluna_data)
    ]
    return df


def _base_avaliavel(df: pd.DataFrame) -> pd.DataFrame:
    """Só as linhas com Status Término avaliável (exclui Sem Registro/Indefinido)."""
    return df[df[STATUS_COL].isin([STATUS_DENTRO, STATUS_ANTES, STATUS_DEPOIS])]


def filtrar_por_status_termino(df: pd.DataFrame, status_sel: str) -> pd.DataFrame:
    """
    Filtra pelo status selecionado no seletor da aba: "Todos" (sem filtro),
    "Dentro", "Antes", "Depois" ou "Fora" (Antes + Depois agrupados).
    """
    if status_sel == "Todos" or STATUS_COL not in df.columns:
        return df
    if status_sel == "Fora":
        return df[df[STATUS_COL].isin([STATUS_ANTES, STATUS_DEPOIS])]
    return df[df[STATUS_COL] == status_sel]


def resumo_geral_termino(df: pd.DataFrame) -> dict:
    """KPIs gerais: total avaliado, % dentro, contagem antes/depois — espelha resumo_geral de chegada.py."""
    avaliavel = _base_avaliavel(df)
    total = len(avaliavel)
    dentro = int((avaliavel[STATUS_COL] == STATUS_DENTRO).sum())
    antes = int((avaliavel[STATUS_COL] == STATUS_ANTES).sum())
    depois = int((avaliavel[STATUS_COL] == STATUS_DEPOIS).sum())

    return {
        "total": total,
        "dentro": dentro,
        "fora": antes + depois,
        "antes": antes,
        "depois": depois,
        "pct_dentro": (dentro / total * 100) if total else 0.0,
        "pct_fora": ((antes + depois) / total * 100) if total else 0.0,
        "sem_registro": int((df[STATUS_COL] == STATUS_SEM_REGISTRO).sum()),
        "indefinido": int((df[STATUS_COL] == STATUS_INDEFINIDO).sum()),
        "aguardando": int((df[STATUS_COL] == STATUS_AGUARDANDO).sum()),
    }


def _stats_tempo_termino(sub: pd.DataFrame) -> dict:
    """
    Estatísticas de tempo de término para um recorte já avaliável:
        - total: qtd de OS consideradas
        - tempo_medio_min: média de (Término - fechamento da Janela) em
          minutos. Positivo = terminou depois do fechamento, em média;
          negativo = terminou antes, em média.
        - horario_medio: média simples dos horários de Término (HH:MM)
        - horario_frequente: horário de término mais frequente (moda, em
          blocos de 15 min)
    """
    minutos_termino = []
    minutos_diff = []
    for janela, termino in zip(sub[COL_JANELA], sub[COL_TERMINO]):
        h_termino = _parse_hora(termino)
        _, janela_fim = parse_janela(janela)
        if h_termino is None or janela_fim is None:
            continue
        m_termino = _minutos_desde_meianoite(h_termino)
        minutos_termino.append(m_termino)
        minutos_diff.append(m_termino - _minutos_desde_meianoite(janela_fim))

    total = len(minutos_termino)
    if total == 0:
        return {"total": 0, "tempo_medio_min": None, "horario_medio": None, "horario_frequente": None}

    return {
        "total": total,
        "tempo_medio_min": sum(minutos_diff) / total,
        "horario_medio": _formatar_minutos_como_hora(sum(minutos_termino) / total),
        "horario_frequente": _horario_mais_frequente(minutos_termino),
    }


def resumo_tempo_termino(df: pd.DataFrame) -> dict:
    """KPIs gerais sobre o tempo de término do atendimento (independente da Janela)."""
    avaliavel = _base_avaliavel(df)
    stats = _stats_tempo_termino(avaliavel)
    return {
        "total": stats["total"],
        "tempo_medio_min": stats["tempo_medio_min"],
        "tempo_medio_fmt": _formatar_duracao(stats["tempo_medio_min"]) if stats["total"] else "—",
        "horario_medio": stats["horario_medio"] or "—",
        "horario_frequente": stats["horario_frequente"] or "—",
    }


def tempo_termino_por_janela(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mesmas métricas de `resumo_tempo_termino`, quebradas por Janela de
    Serviço, ordenado cronologicamente pelo FECHAMENTO de cada janela.

    Inclui a coluna auxiliar "_tempo_medio_min" (numérica, para uso em
    gráfico) que não deve ser exibida diretamente numa tabela ao usuário.
    """
    colunas_saida = [
        "Janela", "Qtd", "Horário Médio", "Horário Mais Frequente",
        "Tempo Médio até Término", "_tempo_medio_min",
    ]
    if COL_JANELA not in df.columns:
        return pd.DataFrame(columns=colunas_saida)

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return pd.DataFrame(columns=colunas_saida)

    linhas = []
    for janela, grupo in avaliavel.groupby(COL_JANELA):
        stats = _stats_tempo_termino(grupo)
        if stats["total"] == 0:
            continue
        _, janela_fim = parse_janela(janela)
        linhas.append({
            "Janela": janela,
            "Qtd": stats["total"],
            "Horário Médio": stats["horario_medio"],
            "Horário Mais Frequente": stats["horario_frequente"],
            "Tempo Médio até Término": _formatar_duracao(stats["tempo_medio_min"]),
            "_tempo_medio_min": round(stats["tempo_medio_min"], 1),
            "_ordem": _minutos_desde_meianoite(janela_fim) if janela_fim else 9999,
        })

    if not linhas:
        return pd.DataFrame(columns=colunas_saida)

    resultado = pd.DataFrame(linhas).sort_values("_ordem").drop(columns="_ordem").reset_index(drop=True)
    return resultado[colunas_saida]
