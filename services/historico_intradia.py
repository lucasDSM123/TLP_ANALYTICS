"""
Histórico INTRADIÁRIO de PU / Eficácia — snapshot gravado a cada extração
(hoje de meia em meia hora), usado no gráfico "Evolução PU x Eficácia" do
Dashboard.

IMPORTANTE — por que isso precisa de uma tabela nova:
A base principal (`producao_tlp_tratada`) é sobrescrita/upsertada a cada
extração — ela sempre reflete o "agora", nunca guarda o que os indicadores
valiam 1h atrás. Pra desenhar uma evolução ao longo do dia, alguém precisa
"fotografar" PU e Eficácia em cada extração e guardar isso em algum lugar
que NÃO seja sobrescrito. É exatamente isso que estas tabelas fazem.

Quem grava: `registrar_snapshot()`, chamado pelo `upload_dados.py` logo
depois de cada envio bem-sucedido pro Neon (ou seja, a cada ~30 min, no
mesmo ritmo da extração real). A partir do dia em que isso entrar no ar,
o histórico intradiário começa a existir — dias ANTERIORES a essa data não
têm esse detalhe por hora, porque a informação simplesmente nunca foi
guardada antes.

POR QUE SÃO TRÊS TABELAS (e não uma só por Estado/Cluster/Cidade):
Concluído OK/NOK é um fato da OS (cada linha da base pertence a exatamente
um Cluster/Cidade), então é somável sem problema por esse recorte — fica
em `historico_indicadores_intradia`.

HC ATIVO já não é: é uma contagem de TÉCNICO ÚNICO, e um mesmo técnico
pode ter OS em mais de um Cluster/Cidade no mesmo dia. Se a gente conta
"técnico único" separadamente dentro de cada Cluster/Cidade e depois soma
esses totais, o mesmo técnico é contado uma vez por Cluster que ele tocou
— inflando o HC de qualquer leitura que junte mais de um grupo (e
consequentemente derrubando o PU, que é Concluído/HC). Por isso o HC vem
de outro lugar:
  - `historico_intradia_tecnico`: um roster com UMA linha por técnico TLP único
    por extração (independe de quantos Cluster/Cidade ele tocou) — é dessa
    tabela que sai a contagem MSK/BA/TT usada no cálculo de HC, sempre
    deduplicada corretamente.
  - `historico_intradia_tecnico_local`: tabela de junção, várias linhas por
    técnico por extração (uma por Cluster/Cidade que ele tocou naquela
    extração) — usada SÓ pra filtrar: "quais técnicos tocaram este
    Cluster/Cidade", nunca pra contar.
Na leitura, pra um filtro de Cluster/Cidade: primeiro acha o conjunto de
técnicos que tocaram aquele recorte (via tabela de junção), depois busca o
perfil desses técnicos no roster e SÓ ENTÃO conta/arredonda — preservando
a unicidade global do técnico não importa quantos grupos ele apareça.
"""

import math
import pandas as pd
from sqlalchemy import text

from services.database import obter_engine
from services.indicadores import Indicadores

NOME_TABELA = "historico_indicadores_intradia"
NOME_TABELA_TECNICO = "historico_intradia_tecnico"
NOME_TABELA_TECNICO_LOCAL = "historico_intradia_tecnico_local"

_COLUNAS_VAZIAS = ["Data", "HoraExtracao", "Hora", "PU", "Eficácia"]


def criar_tabela_historico_intradia():
    """
    Cria as 3 tabelas no Neon, caso ainda não existam. Idempotente — pode
    chamar sempre.

    Também migra instalações de versões anteriores: adiciona
    cluster/cidade em `historico_indicadores_intradia` (nullable), afrouxa hc_ativo/pu/
    eficacia pra nullable nela (esses três campos não são mais gravados
    ali — o HC agora vem das tabelas de técnico, ver docstring do módulo)
    e recria a UNIQUE constraint incluindo cluster/cidade.

    IMPORTANTE: snapshots gravados ANTES de uma dada migração não têm a
    granularidade que ela introduziu — pra esses períodos, o filtro
    correspondente (Cluster/Cidade, ou o próprio HC do roster de técnico)
    não vai encontrar dado.
    """
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {NOME_TABELA} (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                hora_extracao TIMESTAMP NOT NULL,
                estado VARCHAR(10) NOT NULL,
                cluster VARCHAR(100),
                cidade VARCHAR(100),
                concluido_ok BIGINT NOT NULL,
                concluido_nok BIGINT NOT NULL,
                hc_ativo BIGINT,
                msk_tlp INTEGER,
                ba_tlp INTEGER,
                tt_tlp INTEGER,
                pu DOUBLE PRECISION,
                eficacia DOUBLE PRECISION,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        # Migração de tabelas antigas (idempotente).
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ADD COLUMN IF NOT EXISTS cluster VARCHAR(100);"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ADD COLUMN IF NOT EXISTS msk_tlp INTEGER;"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ADD COLUMN IF NOT EXISTS ba_tlp INTEGER;"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ADD COLUMN IF NOT EXISTS tt_tlp INTEGER;"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ALTER COLUMN hc_ativo DROP NOT NULL;"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ALTER COLUMN pu DROP NOT NULL;"))
        conn.execute(text(f"ALTER TABLE {NOME_TABELA} ALTER COLUMN eficacia DROP NOT NULL;"))
        conn.execute(text(
            f"ALTER TABLE {NOME_TABELA} "
            f"DROP CONSTRAINT IF EXISTS {NOME_TABELA}_data_hora_extracao_estado_key;"
        ))
        conn.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{NOME_TABELA}_unico'
                ) THEN
                    ALTER TABLE {NOME_TABELA}
                        ADD CONSTRAINT {NOME_TABELA}_unico
                        UNIQUE (data, hora_extracao, estado, cluster, cidade);
                END IF;
            END $$;
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{NOME_TABELA}_data ON {NOME_TABELA} (data);"))

        # Roster: 1 linha por técnico TLP único por extração — nunca mais
        # de uma, não importa quantos Cluster/Cidade ele tenha tocado.
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {NOME_TABELA_TECNICO} (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                hora_extracao TIMESTAMP NOT NULL,
                estado VARCHAR(10) NOT NULL,
                tecnico VARCHAR(200) NOT NULL,
                perfil_tecnico VARCHAR(20) NOT NULL,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (data, hora_extracao, tecnico)
            );
        """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{NOME_TABELA_TECNICO}_data ON {NOME_TABELA_TECNICO} (data);"))

        # Junção: 1 linha por (técnico, Cluster, Cidade) tocados na
        # extração — só serve pra filtrar, nunca pra contar.
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {NOME_TABELA_TECNICO_LOCAL} (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                hora_extracao TIMESTAMP NOT NULL,
                tecnico VARCHAR(200) NOT NULL,
                cluster VARCHAR(100),
                cidade VARCHAR(100),
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (data, hora_extracao, tecnico, cluster, cidade)
            );
        """))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS idx_{NOME_TABELA_TECNICO_LOCAL}_data "
            f"ON {NOME_TABELA_TECNICO_LOCAL} (data);"
        ))


def registrar_snapshot(df: pd.DataFrame) -> bool:
    """
    Snapshot do dia mais recente presente em `df` nesta extração. Grava:
      1. Concluído OK/NOK por (Estado, Cluster, Cidade) — aditivo.
      2. Roster de técnicos TLP únicos por Estado (perfil MSK/BA/TT) — a
         fonte de verdade do HC, sempre deduplicada.
      3. Junção técnico -> (Cluster, Cidade) tocados nesta extração — só
         pra permitir filtrar por Cluster/Cidade na leitura sem duplicar
         o técnico.

    Chamado pelo `upload_dados.py` depois de cada envio bem-sucedido.
    Retorna True se gravou algo, False se não havia como — nunca levanta
    exceção, pra um problema aqui nunca derrubar o upload principal.
    """
    try:
        colunas_necessarias = {"Data", "Data Extração", "Estado", "Status", "Lado", "Contratada", "Perfil Técnico", "Técnico"}
        if df.empty or not colunas_necessarias.issubset(df.columns):
            return False

        extracao_validas = pd.to_datetime(df["Data Extração"], errors="coerce").dropna()
        if extracao_validas.empty:
            return False
        hora_extracao = extracao_validas.max()

        # O dia "de hoje" é o dia cuja(s) linha(s) têm a coluna de extração
        # preenchida (é assim que a base sinaliza qual dia é o mais recente/
        # em andamento — ver comentário no topo do app.py).
        df_hoje = df.loc[df["Data Extração"].notna()].copy()
        if df_hoje.empty:
            return False

        datas_hoje = pd.to_datetime(df_hoje["Data"], errors="coerce", dayfirst=True).dropna()
        if datas_hoje.empty:
            return False
        data_ref = datas_hoje.max().date()

        criar_tabela_historico_intradia()

        tem_cluster_cidade = [c for c in ("Cluster", "Cidade") if c in df_hoje.columns]

        # 1) Concluído OK/NOK por Estado/Cluster/Cidade — fato da OS, é
        #    aditivo, sem problema de dupla contagem.
        colunas_grupo = ["Estado"] + tem_cluster_cidade
        linhas_concluido = []
        for chave, df_grupo in df_hoje.groupby(colunas_grupo, dropna=False):
            chave = chave if isinstance(chave, tuple) else (chave,)
            valores = dict(zip(colunas_grupo, chave))
            estado = valores.get("Estado")
            if not estado or pd.isna(estado):
                continue
            concluido = Indicadores(df_grupo).concluido()
            cluster_val = valores.get("Cluster")
            cidade_val = valores.get("Cidade")
            linhas_concluido.append({
                "data": data_ref, "hora_extracao": hora_extracao, "estado": str(estado),
                "cluster": None if pd.isna(cluster_val) else str(cluster_val),
                "cidade": None if pd.isna(cidade_val) else str(cidade_val),
                "concluido_ok": concluido["OK"], "concluido_nok": concluido["NOK"],
            })

        # 2) Roster de técnico único TLP por Estado (nunca duplicado, não
        #    importa quantos Cluster/Cidade o técnico tocou) + 3) junção
        #    técnico -> Cluster/Cidade (pra filtro).
        linhas_tecnico = []
        linhas_local = []
        df_tlp = df_hoje[df_hoje["Contratada"] == "TLP"]
        for (estado, tecnico), df_t in df_tlp.groupby(["Estado", "Técnico"], dropna=False):
            if not estado or pd.isna(estado) or not tecnico or pd.isna(tecnico):
                continue
            perfis = df_t["Perfil Técnico"].dropna()
            if perfis.empty:
                continue
            perfil = perfis.mode().iloc[0]
            if perfil not in ("MSK", "BA", "TT"):
                continue
            linhas_tecnico.append({
                "data": data_ref, "hora_extracao": hora_extracao, "estado": str(estado),
                "tecnico": str(tecnico), "perfil_tecnico": str(perfil),
            })
            if tem_cluster_cidade:
                combos = df_t[tem_cluster_cidade].drop_duplicates()
                for _, row in combos.iterrows():
                    cl = row.get("Cluster") if "Cluster" in tem_cluster_cidade else None
                    ci = row.get("Cidade") if "Cidade" in tem_cluster_cidade else None
                    linhas_local.append({
                        "data": data_ref, "hora_extracao": hora_extracao, "tecnico": str(tecnico),
                        "cluster": None if pd.isna(cl) else str(cl),
                        "cidade": None if pd.isna(ci) else str(ci),
                    })

        if not linhas_concluido and not linhas_tecnico:
            return False

        engine = obter_engine()
        with engine.begin() as conn:
            for linha in linhas_concluido:
                conn.execute(text(f"""
                    INSERT INTO {NOME_TABELA}
                        (data, hora_extracao, estado, cluster, cidade, concluido_ok, concluido_nok)
                    VALUES
                        (:data, :hora_extracao, :estado, :cluster, :cidade, :concluido_ok, :concluido_nok)
                    ON CONFLICT ON CONSTRAINT {NOME_TABELA}_unico DO NOTHING
                """), linha)
            for linha in linhas_tecnico:
                conn.execute(text(f"""
                    INSERT INTO {NOME_TABELA_TECNICO}
                        (data, hora_extracao, estado, tecnico, perfil_tecnico)
                    VALUES
                        (:data, :hora_extracao, :estado, :tecnico, :perfil_tecnico)
                    ON CONFLICT (data, hora_extracao, tecnico) DO NOTHING
                """), linha)
            for linha in linhas_local:
                conn.execute(text(f"""
                    INSERT INTO {NOME_TABELA_TECNICO_LOCAL}
                        (data, hora_extracao, tecnico, cluster, cidade)
                    VALUES
                        (:data, :hora_extracao, :tecnico, :cluster, :cidade)
                    ON CONFLICT (data, hora_extracao, tecnico, cluster, cidade) DO NOTHING
                """), linha)
        return True
    except Exception as e:
        print(f"[AVISO] Não foi possível registrar o snapshot intradiário: {e}")
        return False


def carregar_historico_intradia(dias, estados=None, clusters=None, cidades=None) -> pd.DataFrame:
    """
    Lê o histórico intradiário já agregado por horário de extração, para
    o(s) dia(s)/Estado(s)/Cluster(s)/Cidade(s) pedidos.

    `dias`: lista de `date` (ou string 'YYYY-MM-DD'). `estados`/`clusters`/
    `cidades`: listas de valores ou None/[] para não restringir aquele
    recorte (soma tudo).

    Concluído OK/NOK vem somado direto de `{NOME_TABELA}` (aditivo por
    Cluster/Cidade). HC vem do roster de técnico único (`{NOME_TABELA_TECNICO}`),
    filtrado — quando há Cluster/Cidade selecionado — pelo conjunto de
    técnicos que tocaram aquele recorte na tabela de junção; a contagem
    MSK/BA/TT nunca soma "técnico único por subgrupo", sempre deduplica
    globalmente antes de arredondar o HC (ver docstring do módulo).

    Retorna DataFrame com colunas: Data, HoraExtracao (datetime), Hora
    ("HH:MM"), PU, Eficácia — uma linha por extração, ordenado
    cronologicamente. Vazio se as tabelas não existirem ainda ou não
    houver snapshot pro recorte pedido.
    """
    if not dias:
        return pd.DataFrame(columns=_COLUNAS_VAZIAS)

    engine = obter_engine()
    try:
        with engine.connect() as conn:
            existe = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"
            ), {"t": NOME_TABELA}).scalar()
            if not existe:
                return pd.DataFrame(columns=_COLUNAS_VAZIAS)

            # 1) Concluído OK/NOK, agregado por extração.
            query_ok = f"""
                SELECT data, hora_extracao,
                       SUM(concluido_ok) AS concluido_ok,
                       SUM(concluido_nok) AS concluido_nok,
                       SUM(hc_ativo) AS hc_ativo_legado
                FROM {NOME_TABELA}
                WHERE data = ANY(:dias)
            """
            params = {"dias": list(dias)}
            if estados:
                query_ok += " AND estado = ANY(:estados)"
                params["estados"] = list(estados)
            if clusters:
                query_ok += " AND cluster = ANY(:clusters)"
                params["clusters"] = list(clusters)
            if cidades:
                query_ok += " AND cidade = ANY(:cidades)"
                params["cidades"] = list(cidades)
            query_ok += " GROUP BY data, hora_extracao"
            df_ok = pd.read_sql(text(query_ok), conn, params=params)

            # 2) HC — roster de técnico único, opcionalmente restrito pela
            #    junção técnico -> Cluster/Cidade (nunca soma nunique por
            #    subgrupo).
            params_hc = {"dias": list(dias)}
            query_hc = f"""
                SELECT data, hora_extracao, perfil_tecnico, COUNT(*) AS qtd
                FROM {NOME_TABELA_TECNICO}
                WHERE data = ANY(:dias)
            """
            if estados:
                query_hc += " AND estado = ANY(:estados)"
                params_hc["estados"] = list(estados)
            if clusters or cidades:
                sub = f"SELECT data, hora_extracao, tecnico FROM {NOME_TABELA_TECNICO_LOCAL} WHERE 1=1"
                if clusters:
                    sub += " AND cluster = ANY(:clusters)"
                    params_hc["clusters"] = list(clusters)
                if cidades:
                    sub += " AND cidade = ANY(:cidades)"
                    params_hc["cidades"] = list(cidades)
                query_hc += f" AND (data, hora_extracao, tecnico) IN ({sub})"
            query_hc += " GROUP BY data, hora_extracao, perfil_tecnico"
            df_hc = pd.read_sql(text(query_hc), conn, params=params_hc)
    except Exception as e:
        print(f"[AVISO] Não foi possível ler o histórico intradiário: {e}")
        return pd.DataFrame(columns=_COLUNAS_VAZIAS)

    if df_ok.empty:
        return pd.DataFrame(columns=_COLUNAS_VAZIAS)

    if not df_hc.empty:
        pivot_hc = df_hc.pivot_table(
            index=["data", "hora_extracao"], columns="perfil_tecnico", values="qtd", aggfunc="sum", fill_value=0
        )
        for col in ("MSK", "BA", "TT"):
            if col not in pivot_hc.columns:
                pivot_hc[col] = 0
        pivot_hc = pivot_hc.reset_index()[["data", "hora_extracao", "MSK", "BA", "TT"]]
    else:
        pivot_hc = pd.DataFrame(columns=["data", "hora_extracao", "MSK", "BA", "TT"])

    agrupado = df_ok.merge(pivot_hc, on=["data", "hora_extracao"], how="left", indicator=True)
    agrupado["tem_roster"] = agrupado["_merge"] == "both"
    for col in ("MSK", "BA", "TT"):
        agrupado[col] = agrupado[col].fillna(0)

    def _hc_ativo(r):
        if r["tem_roster"]:
            return math.floor(r["MSK"] / 2 + r["BA"]) + math.ceil(r["MSK"] / 2 + r["TT"])
        # Extração anterior à existência do roster de técnico — cai de
        # volta pro hc_ativo legado gravado na época (só existe quando a
        # instalação já vinha de uma versão anterior desta correção).
        return r["hc_ativo_legado"] if pd.notna(r["hc_ativo_legado"]) else 0

    agrupado["hc_ativo"] = agrupado.apply(_hc_ativo, axis=1)
    agrupado["PU"] = agrupado.apply(lambda r: 0.0 if r["hc_ativo"] == 0 else r["concluido_ok"] / r["hc_ativo"], axis=1)
    agrupado["Eficácia"] = agrupado.apply(
        lambda r: 1.0 if (r["concluido_ok"] + r["concluido_nok"]) == 0 else r["concluido_ok"] / (r["concluido_ok"] + r["concluido_nok"]),
        axis=1,
    )
    agrupado = agrupado.sort_values("hora_extracao")
    agrupado["Hora"] = pd.to_datetime(agrupado["hora_extracao"]).dt.strftime("%H:%M")

    return agrupado.rename(columns={"data": "Data", "hora_extracao": "HoraExtracao"})[_COLUNAS_VAZIAS]
