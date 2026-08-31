"""
Indicador de Chegada — compara o horário real de Início do técnico contra a
Janela de Serviço agendada para a atividade, classificando cada OS como
Dentro ou Fora da janela (Antes / Depois).

Réplica em Python da aba "IND. CHEGADA" da planilha de Produtividade:
    Janela (ex.: "08:30 - 10:30") x Início (ex.: "08:47")
    -> DENTRO (Início cai dentro do intervalo da Janela)
    -> FORA   (Início é antes do começo ou depois do fim da Janela)

Linhas sem horário de Início não entram nas métricas de aderência — ficam
marcadas como "Sem Registro". OS "Cancelada", "Não Iniciada" e "em rota"
são excluídas do indicador (ver STATUS_EXCLUIDOS).
"""

import re
from datetime import datetime, time, timedelta

import pandas as pd

COL_JANELA = "Janela"
COL_INICIO = "Início"
COL_STATUS = "Status"
COL_DATA = "Data"

STATUS_CANCELADA = "Cancelada"
STATUS_NAO_INICIADA = "Não Iniciada"
STATUS_EM_ROTA = "em rota"

# Status que não fazem sentido no indicador de chegada (o técnico ainda nem
# começou o atendimento, então não há Início real pra comparar com a Janela).
STATUS_EXCLUIDOS = (STATUS_CANCELADA, STATUS_NAO_INICIADA, STATUS_EM_ROTA)

STATUS_DENTRO = "Dentro"
STATUS_ANTES = "Antes"
STATUS_DEPOIS = "Depois"
STATUS_SEM_REGISTRO = "Sem Registro"
STATUS_INDEFINIDO = "Indefinido"
# OS de hoje cujo horário de "Início Real" registrado ainda está no futuro
# em relação ao momento atual (ex.: agora são 13:12 e a linha já traz um
# Início de 14:00). Isso é sinal de dado ainda não confirmado/placeholder
# vindo da base — a linha não deve ser avaliada como Dentro/Antes/Depois
# até que esse horário realmente já tenha passado.
STATUS_AGUARDANDO = "Aguardando"

# Tempo limite de tolerância para o início: o técnico tem até esse tempo
# após a abertura da Janela para começar o atendimento. Passou disso, já
# conta como "Depois" (chegou fora do horário) — mesmo que o horário de
# início ainda esteja dentro do intervalo da Janela.
# Ex.: Janela 08:30-10:30 -> limite é 09:00. Início às 9:01 = Depois.
TOLERANCIA_ATRASO = timedelta(minutes=30)

# Tolerância de antecipação: o técnico pode iniciar até esse tempo antes da
# abertura da Janela que ainda é considerado "Dentro" (chegou dentro do
# horário). Ex.: Janela 08:30-10:30 -> a partir de 07:30 já é Dentro.
# Só conta como "Antes" (fora do horário) quem iniciar antes desse limite.
TOLERANCIA_ANTECIPACAO = timedelta(minutes=60)

_RE_HORA = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*$")


def _para_datetime(t: time) -> datetime:
    """Combina um horário com uma data fixa só para permitir aritmética/comparação."""
    return datetime.combine(datetime(2000, 1, 1), t)


def _parse_hora(texto) -> time | None:
    """Converte 'HH:MM' ou 'HH' em datetime.time. Retorna None se inválido."""
    if texto is None:
        return None
    if isinstance(texto, time):
        return texto
    if hasattr(texto, "hour"):  # datetime / Timestamp
        return time(texto.hour, texto.minute)

    m = _RE_HORA.match(str(texto))
    if not m:
        return None
    hora = int(m.group(1))
    minuto = int(m.group(2)) if m.group(2) else 0
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None
    return time(hora, minuto)


def parse_janela(texto) -> tuple[time | None, time | None]:
    """Converte uma Janela de Serviço ('08:30 - 10:30') em (início, fim)."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return None, None
    partes = str(texto).split("-")
    if len(partes) != 2:
        return None, None
    return _parse_hora(partes[0]), _parse_hora(partes[1])


def _e_hoje(data_os, agora: datetime) -> bool:
    """Confere se a Data da linha (texto 'dd/mm/aa' ou 'dd/mm/aaaa') é o dia de `agora`."""
    if data_os is None or (isinstance(data_os, float) and pd.isna(data_os)):
        return False
    if hasattr(data_os, "date"):
        return data_os.date() == agora.date()
    dt = pd.to_datetime(str(data_os), errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return False
    return dt.date() == agora.date()


def classificar_linha(janela, inicio_real, data_os=None, agora: datetime | None = None) -> str:
    """Classifica uma OS em Dentro / Antes / Depois / Aguardando / Sem Registro / Indefinido.

    Regra de atraso: o técnico tem até TOLERANCIA_ATRASO (30 min) após o
    horário de abertura da Janela pra iniciar o atendimento. Iniciar depois
    desse limite já é "Depois" (fora do horário), mesmo que o horário de
    início ainda caia dentro do intervalo da Janela.

    Regra de antecipação: o técnico pode iniciar até TOLERANCIA_ANTECIPACAO
    (60 min) antes da abertura da Janela que ainda conta como "Dentro".
    Só é "Antes" (fora do horário) quem iniciar antes desse limite.

    Regra de "flag de data"/hora atual: se a OS é de hoje e o horário de
    Início Real registrado ainda está no futuro em relação a `agora`, a
    linha não é avaliada ainda — isso indica um Início ainda não confirmado
    (placeholder) vindo da base, não um atendimento que já aconteceu.
    """
    hora_inicio = _parse_hora(inicio_real)
    if hora_inicio is None:
        return STATUS_SEM_REGISTRO

    if agora is not None and _e_hoje(data_os, agora):
        if _para_datetime(hora_inicio) > _para_datetime(time(agora.hour, agora.minute)):
            return STATUS_AGUARDANDO

    janela_ini, janela_fim = parse_janela(janela)
    if janela_ini is None or janela_fim is None:
        return STATUS_INDEFINIDO

    if janela_fim < janela_ini:
        # Janela cruza a meia-noite (raro) — trata como indefinido pra não
        # gerar falso "fora" por causa de um dado de origem inconsistente.
        return STATUS_INDEFINIDO

    inicio_dt = _para_datetime(hora_inicio)
    janela_ini_dt = _para_datetime(janela_ini)
    janela_fim_dt = _para_datetime(janela_fim)

    # o limite de atraso nunca ultrapassa o fim da própria janela
    limite_atraso_dt = min(janela_ini_dt + TOLERANCIA_ATRASO, janela_fim_dt)
    limite_antecipacao_dt = janela_ini_dt - TOLERANCIA_ANTECIPACAO

    if inicio_dt < limite_antecipacao_dt:
        return STATUS_ANTES
    if inicio_dt > limite_atraso_dt:
        return STATUS_DEPOIS
    return STATUS_DENTRO


def calcular_indicador_chegada(df: pd.DataFrame, agora: datetime | None = None) -> pd.DataFrame:
    """
    Recebe o dataframe base (com as colunas Janela e Início) e devolve uma
    cópia com as colunas adicionais:
        - Status Chegada: Dentro / Antes / Depois / Aguardando / Sem Registro / Indefinido
        - Dentro da Janela: True/False (None quando não avaliável)

    OS com Status "Cancelada", "Não Iniciada" ou "em rota" são excluídas do
    indicador (considera-se os demais status: Concluída, Não Concluída,
    Suspensa, Iniciada).

    `agora` (padrão: datetime.now()) é usado para não avaliar, como
    Dentro/Antes/Depois, OS de hoje cujo Início Real registrado ainda esteja
    no futuro em relação ao momento atual — essas ficam como "Aguardando".
    """
    if agora is None:
        agora = datetime.now()

    df = df.copy()

    if COL_STATUS in df.columns:
        df = df[~df[COL_STATUS].isin(STATUS_EXCLUIDOS)]

    if COL_JANELA not in df.columns or COL_INICIO not in df.columns:
        df["Status Chegada"] = STATUS_INDEFINIDO
        df["Dentro da Janela"] = None
        return df

    coluna_data = df[COL_DATA] if COL_DATA in df.columns else [None] * len(df)
    df["Status Chegada"] = [
        classificar_linha(j, i, d, agora)
        for j, i, d in zip(df[COL_JANELA], df[COL_INICIO], coluna_data)
    ]
    df["Dentro da Janela"] = df["Status Chegada"].map(
        {STATUS_DENTRO: True, STATUS_ANTES: False, STATUS_DEPOIS: False}
    )
    return df


def _base_avaliavel(df: pd.DataFrame) -> pd.DataFrame:
    """Só as linhas com Status Chegada avaliável (exclui Sem Registro/Indefinido)."""
    return df[df["Status Chegada"].isin([STATUS_DENTRO, STATUS_ANTES, STATUS_DEPOIS])]


def resumo_geral(df: pd.DataFrame) -> dict:
    """KPIs gerais: total avaliado, % dentro, contagem antes/depois."""
    avaliavel = _base_avaliavel(df)
    total = len(avaliavel)
    dentro = int((avaliavel["Status Chegada"] == STATUS_DENTRO).sum())
    antes = int((avaliavel["Status Chegada"] == STATUS_ANTES).sum())
    depois = int((avaliavel["Status Chegada"] == STATUS_DEPOIS).sum())

    return {
        "total": total,
        "dentro": dentro,
        "fora": antes + depois,
        "antes": antes,
        "depois": depois,
        "pct_dentro": (dentro / total * 100) if total else 0.0,
        "pct_fora": ((antes + depois) / total * 100) if total else 0.0,
        "sem_registro": int((df["Status Chegada"] == STATUS_SEM_REGISTRO).sum()),
        "indefinido": int((df["Status Chegada"] == STATUS_INDEFINIDO).sum()),
        "aguardando": int((df["Status Chegada"] == STATUS_AGUARDANDO).sum()),
    }


def resumo_por_grupo(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """
    Resumo (Dentro / Fora / % Dentro) agrupado por uma coluna (ex.: Cluster,
    Cidade, Supervisor). Ordenado por % Dentro decrescente.
    """
    if coluna not in df.columns:
        return pd.DataFrame(columns=[coluna, "Dentro", "Fora", "Total", "% Dentro"])

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return pd.DataFrame(columns=[coluna, "Dentro", "Fora", "Total", "% Dentro"])

    agrupado = (
        avaliavel.groupby(coluna)["Status Chegada"]
        .value_counts()
        .unstack(fill_value=0)
    )
    for status in (STATUS_DENTRO, STATUS_ANTES, STATUS_DEPOIS):
        if status not in agrupado.columns:
            agrupado[status] = 0

    resultado = pd.DataFrame(
        {
            coluna: agrupado.index,
            "Dentro": agrupado[STATUS_DENTRO].values,
            "Antes": agrupado[STATUS_ANTES].values,
            "Depois": agrupado[STATUS_DEPOIS].values,
        }
    )
    resultado["Fora"] = resultado["Antes"] + resultado["Depois"]
    resultado["Total"] = resultado["Dentro"] + resultado["Fora"]
    resultado["% Dentro"] = (resultado["Dentro"] / resultado["Total"] * 100).round(1)
    resultado = resultado.sort_values("% Dentro", ascending=False).reset_index(drop=True)
    return resultado[[coluna, "Dentro", "Antes", "Depois", "Fora", "Total", "% Dentro"]]


def resumo_hierarquico(df: pd.DataFrame, coluna_pai: str = "Cluster", coluna_filho: str = "Cidade") -> list:
    """
    Agrupa o indicador em dois níveis (ex.: Cluster -> Cidade) pronto para
    a tabela expansível: [{"nome", "dentro", "antes", "depois", "fora",
    "total", "pct", "filhos": [mesma estrutura, sem "filhos"]}, ...],
    ordenado por % Dentro decrescente (grupo pai e, dentro dele, os filhos).
    """
    if coluna_pai not in df.columns or coluna_filho not in df.columns:
        return []

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return []

    def _stats(sub: pd.DataFrame) -> dict:
        dentro = int((sub["Status Chegada"] == STATUS_DENTRO).sum())
        antes = int((sub["Status Chegada"] == STATUS_ANTES).sum())
        depois = int((sub["Status Chegada"] == STATUS_DEPOIS).sum())
        fora = antes + depois
        total = dentro + fora
        pct = round(dentro / total * 100, 1) if total else 0.0
        return {"dentro": dentro, "antes": antes, "depois": depois, "fora": fora, "total": total, "pct": pct}

    resultado = []
    for nome_pai, grupo_pai in avaliavel.groupby(coluna_pai):
        item = {"nome": str(nome_pai), **_stats(grupo_pai), "filhos": []}
        for nome_filho, grupo_filho in grupo_pai.groupby(coluna_filho):
            item["filhos"].append({"nome": str(nome_filho), **_stats(grupo_filho)})
        item["filhos"].sort(key=lambda f: f["pct"], reverse=True)
        resultado.append(item)

    resultado.sort(key=lambda g: g["pct"], reverse=True)
    return resultado


def resumo_hierarquico_3niveis(
    df: pd.DataFrame, coluna_pai: str, coluna_meio: str, coluna_filho: str
) -> list:
    """
    Mesma ideia de `resumo_hierarquico`, só que com mais um nível de
    detalhamento (ex.: Cluster -> Cidade -> Zona, ou Coordenador ->
    Supervisor -> Técnico), pronta para a tabela expansível de 3 níveis:
    [{"nome", "dentro", "antes", "depois", "fora", "total", "pct",
      "filhos": [{"nome", ..., "netos": [{"nome", ...}, ...]}, ...]}, ...]
    Ordenado por % Dentro decrescente em todos os níveis.
    """
    colunas_necessarias = (coluna_pai, coluna_meio, coluna_filho)
    if any(c not in df.columns for c in colunas_necessarias):
        return []

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return []

    def _stats(sub: pd.DataFrame) -> dict:
        dentro = int((sub["Status Chegada"] == STATUS_DENTRO).sum())
        antes = int((sub["Status Chegada"] == STATUS_ANTES).sum())
        depois = int((sub["Status Chegada"] == STATUS_DEPOIS).sum())
        fora = antes + depois
        total = dentro + fora
        pct = round(dentro / total * 100, 1) if total else 0.0
        return {"dentro": dentro, "antes": antes, "depois": depois, "fora": fora, "total": total, "pct": pct}

    resultado = []
    for nome_pai, grupo_pai in avaliavel.groupby(coluna_pai):
        item = {"nome": str(nome_pai), **_stats(grupo_pai), "filhos": []}
        for nome_meio, grupo_meio in grupo_pai.groupby(coluna_meio):
            filho = {"nome": str(nome_meio), **_stats(grupo_meio), "netos": []}
            for nome_filho, grupo_filho in grupo_meio.groupby(coluna_filho):
                filho["netos"].append({"nome": str(nome_filho), **_stats(grupo_filho)})
            filho["netos"].sort(key=lambda n: n["pct"], reverse=True)
            item["filhos"].append(filho)
        item["filhos"].sort(key=lambda f: f["pct"], reverse=True)
        resultado.append(item)

    resultado.sort(key=lambda g: g["pct"], reverse=True)
    return resultado


def ranking_ofensores(df: pd.DataFrame, coluna: str, top_n: int | None = 10) -> pd.DataFrame:
    """
    Ranking dos "ofensores" — quem mais acumulou chegadas classificadas
    como "Depois" (iniciou o atendimento além da tolerância de atraso da
    Janela), agrupado por uma coluna (ex.: "Técnico" ou "Supervisor").

    Retorna colunas [coluna, "Qtd Depois", "Total Avaliado", "% Depois"],
    ordenado por "Qtd Depois" decrescente. Passe `top_n=None` para trazer
    todo mundo, sem cortar no top N.
    """
    colunas_saida = [coluna, "Qtd Depois", "Total Avaliado", "% Depois"]
    if coluna not in df.columns:
        return pd.DataFrame(columns=colunas_saida)

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return pd.DataFrame(columns=colunas_saida)

    agrupado = (
        avaliavel.groupby(coluna)["Status Chegada"]
        .value_counts()
        .unstack(fill_value=0)
    )
    if STATUS_DEPOIS not in agrupado.columns:
        agrupado[STATUS_DEPOIS] = 0

    resultado = pd.DataFrame(
        {
            coluna: agrupado.index,
            "Qtd Depois": agrupado[STATUS_DEPOIS].values,
            "Total Avaliado": agrupado.sum(axis=1).values,
        }
    )
    resultado["% Depois"] = (resultado["Qtd Depois"] / resultado["Total Avaliado"] * 100).round(1)
    resultado = resultado.sort_values(
        ["Qtd Depois", "% Depois"], ascending=False
    ).reset_index(drop=True)

    # só entram ofensores de fato (pelo menos 1 chegada "Depois")
    resultado = resultado[resultado["Qtd Depois"] > 0]

    if top_n:
        resultado = resultado.head(top_n)
    return resultado.reset_index(drop=True)


def _minutos_desde_meianoite(t: time) -> int:
    return t.hour * 60 + t.minute


def _formatar_minutos_como_hora(minutos: float) -> str:
    """Converte um total de minutos (desde meia-noite) em texto 'HH:MM'."""
    minutos_int = int(round(minutos)) % (24 * 60)
    return f"{minutos_int // 60:02d}:{minutos_int % 60:02d}"


def _formatar_duracao(minutos: float) -> str:
    """
    Formata uma duração em minutos como texto legível (ex.: '32 min',
    '1h15min'). Valores negativos (iniciou antes da abertura da Janela)
    ganham o prefixo '-'.
    """
    sinal = "-" if minutos < 0 else ""
    minutos_abs = abs(int(round(minutos)))
    if minutos_abs < 60:
        return f"{sinal}{minutos_abs} min"
    horas, resto = divmod(minutos_abs, 60)
    return f"{sinal}{horas}h{resto:02d}min" if resto else f"{sinal}{horas}h"


def _horario_mais_frequente(minutos_lista: list, bin_minutos: int = 15) -> str | None:
    """
    Moda dos horários de Início, agrupados em blocos de `bin_minutos`
    (padrão 15 min) pra suavizar pequenas variações de segundo/minuto e
    achar o "horário de pico" real de início de atendimento.
    """
    if not minutos_lista:
        return None
    contagem: dict[int, int] = {}
    for m in minutos_lista:
        bucket = (m // bin_minutos) * bin_minutos
        contagem[bucket] = contagem.get(bucket, 0) + 1
    bucket_top = max(contagem, key=contagem.get)
    return _formatar_minutos_como_hora(bucket_top)


def _stats_tempo_inicio(sub: pd.DataFrame) -> dict:
    """
    Estatísticas de tempo de início para um recorte do dataframe já
    avaliável (Status Chegada em Dentro/Antes/Depois):
        - total: qtd de OS consideradas
        - tempo_medio_min: média de (Início - abertura da Janela) em
          minutos. Positivo = atraso médio; negativo = adiantamento médio.
        - horario_medio: média simples dos horários de Início (HH:MM)
        - horario_frequente: horário de início mais frequente (moda, em
          blocos de 15 min) — o "horário de pico" de início
    """
    minutos_inicio = []
    minutos_espera = []
    for janela, inicio in zip(sub[COL_JANELA], sub[COL_INICIO]):
        h_inicio = _parse_hora(inicio)
        janela_ini, _ = parse_janela(janela)
        if h_inicio is None or janela_ini is None:
            continue
        m_inicio = _minutos_desde_meianoite(h_inicio)
        minutos_inicio.append(m_inicio)
        minutos_espera.append(m_inicio - _minutos_desde_meianoite(janela_ini))

    total = len(minutos_inicio)
    if total == 0:
        return {"total": 0, "tempo_medio_min": None, "horario_medio": None, "horario_frequente": None}

    return {
        "total": total,
        "tempo_medio_min": sum(minutos_espera) / total,
        "horario_medio": _formatar_minutos_como_hora(sum(minutos_inicio) / total),
        "horario_frequente": _horario_mais_frequente(minutos_inicio),
    }


def resumo_tempo_inicio(df: pd.DataFrame) -> dict:
    """
    KPIs gerais sobre o tempo até o início do atendimento (independente da
    Janela): tempo médio até iniciar (relativo à abertura da Janela de cada
    OS), horário médio de início e horário de início mais frequente.
    """
    avaliavel = _base_avaliavel(df)
    stats = _stats_tempo_inicio(avaliavel)
    return {
        "total": stats["total"],
        "tempo_medio_min": stats["tempo_medio_min"],
        "tempo_medio_fmt": _formatar_duracao(stats["tempo_medio_min"]) if stats["total"] else "—",
        "horario_medio": stats["horario_medio"] or "—",
        "horario_frequente": stats["horario_frequente"] or "—",
    }


def tempo_inicio_por_janela(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mesmas métricas de `resumo_tempo_inicio`, quebradas por Janela de
    Serviço (ex.: '08:30 - 10:30'), ordenado cronologicamente pelo início
    de cada janela (não por valor).

    Inclui a coluna auxiliar "_tempo_medio_min" (numérica, para uso em
    gráfico) que não deve ser exibida diretamente numa tabela ao usuário.
    """
    colunas_saida = [
        "Janela", "Qtd", "Horário Médio", "Horário Mais Frequente",
        "Tempo Médio até Início", "_tempo_medio_min",
    ]
    if COL_JANELA not in df.columns:
        return pd.DataFrame(columns=colunas_saida)

    avaliavel = _base_avaliavel(df)
    if avaliavel.empty:
        return pd.DataFrame(columns=colunas_saida)

    linhas = []
    for janela, grupo in avaliavel.groupby(COL_JANELA):
        stats = _stats_tempo_inicio(grupo)
        if stats["total"] == 0:
            continue
        janela_ini, _ = parse_janela(janela)
        linhas.append({
            "Janela": janela,
            "Qtd": stats["total"],
            "Horário Médio": stats["horario_medio"],
            "Horário Mais Frequente": stats["horario_frequente"],
            "Tempo Médio até Início": _formatar_duracao(stats["tempo_medio_min"]),
            "_tempo_medio_min": round(stats["tempo_medio_min"], 1),
            "_ordem": _minutos_desde_meianoite(janela_ini) if janela_ini else 9999,
        })

    if not linhas:
        return pd.DataFrame(columns=colunas_saida)

    resultado = pd.DataFrame(linhas).sort_values("_ordem").drop(columns="_ordem").reset_index(drop=True)
    return resultado[colunas_saida]


def tabela_detalhada(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tabela linha a linha (nível técnico/OS) pronta pra exibição: Técnico,
    Cidade, Cluster, Supervisor, Janela, Início real e Status da Chegada.

    Exclui linhas "Sem Registro" (sem Início) e "Indefinido" (sem Janela de
    Serviço definida, ou Janela em formato que não dá pra interpretar) —
    essas OS não têm como ser comparadas e não devem entrar no indicador.
    """
    colunas_desejadas = [
        "Técnico",
        "Cidade",
        "Cluster",
        "Supervisor",
        "Coordenador",
        "Ordem de Serviço",
        COL_DATA,
        COL_JANELA,
        COL_INICIO,
        "Status Chegada",
    ]
    colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
    tabela = df[colunas_existentes].copy()
    tabela = tabela[~tabela["Status Chegada"].isin([STATUS_SEM_REGISTRO, STATUS_INDEFINIDO])]
    return tabela.rename(columns={COL_JANELA: "Janela de Serviço", COL_INICIO: "Início Real", COL_DATA: "Data"})


def mapa_tecnico_matricula(df: pd.DataFrame, coluna_tecnico: str = "Técnico",
                            coluna_matricula: str = "Login Técnico") -> dict:
    """
    Mapa Técnico -> matrícula (coluna "Login Técnico" da base), 1 valor por
    técnico. Usado pra ocultar o nome do técnico nas matrizes expansíveis,
    mostrando só a matrícula no lugar do nome.
    """
    if coluna_tecnico not in df.columns or coluna_matricula not in df.columns:
        return {}
    pares = (
        df[[coluna_tecnico, coluna_matricula]]
        .dropna(subset=[coluna_tecnico])
        .drop_duplicates(subset=[coluna_tecnico])
    )

    def _fmt(valor):
        if pd.isna(valor):
            return "—"
        try:
            return str(int(valor))
        except (TypeError, ValueError):
            return str(valor)

    return {str(tec): _fmt(mat) for tec, mat in zip(pares[coluna_tecnico], pares[coluna_matricula])}


def aplicar_matricula_nos_netos(dados_hierarquicos: list, mapa_matricula: dict) -> list:
    """
    Substitui o "nome" do último nível (netos — ex.: Técnico, numa matriz
    Coordenador -> Supervisor -> Técnico) pela matrícula correspondente,
    preservando as demais chaves (dentro/antes/depois/fora/total/pct).
    Não altera Coordenador/Supervisor, só o nível folha. Técnicos sem
    matrícula mapeada mantêm o próprio nome como fallback.
    """
    resultado = []
    for pai in dados_hierarquicos:
        novo_pai = dict(pai)
        novos_filhos = []
        for filho in pai.get("filhos", []):
            novo_filho = dict(filho)
            novo_filho["netos"] = [
                {**neto, "nome": mapa_matricula.get(neto["nome"], neto["nome"])}
                for neto in filho.get("netos", [])
            ]
            novos_filhos.append(novo_filho)
        novo_pai["filhos"] = novos_filhos
        resultado.append(novo_pai)
    return resultado