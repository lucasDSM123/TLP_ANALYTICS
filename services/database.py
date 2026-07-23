import io
import re

from sqlalchemy import create_engine, text
import pandas as pd
import config


def obter_engine():
    """
    Retorna a instância do engine do SQLAlchemy configurada com a URL do banco.
    """
    return create_engine(config.DATABASE_URL)


def _validar_identificador(nome: str) -> str:
    """
    Garante que um identificador SQL (nome de tabela/coluna controlado pelo
    próprio código, não vindo do Excel) só contém caracteres seguros, evitando
    qualquer risco de injeção ao usá-lo em SQL bruto via f-string.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome):
        raise ValueError(f"Identificador inválido/inseguro para uso em SQL: {nome!r}")
    return nome


def _quotar_coluna(nome: str) -> str:
    """Coloca um nome de coluna entre aspas duplas, escapando aspas internas.
    Colunas vindas do Excel podem ter espaços/acentos/caracteres especiais,
    então aqui não validamos formato — só escapamos e citamos com segurança."""
    return '"' + nome.replace('"', '""') + '"'


def ler_dados_do_neon(nome_tabela_ou_query: str) -> pd.DataFrame:
    """
    Lê dados do banco Neon/PostgreSQL e retorna em um DataFrame do Pandas.
    Aceita o nome de uma tabela (ex: 'atividades') ou uma query SQL (ex: 'SELECT * FROM ...').
    """
    engine = obter_engine()

    # Se a string começar com SELECT ou WITH, trata como query SQL; senão, trata como nome de tabela
    if nome_tabela_ou_query.strip().upper().startswith(("SELECT", "WITH")):
        query = nome_tabela_ou_query
    else:
        query = f'SELECT * FROM "{nome_tabela_ou_query}"'

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    return df


def enviar_dados_para_neon(df: pd.DataFrame, nome_tabela: str, coluna_chave: str = "numero_atividade",
                            sincronizar_exclusoes: bool = True):
    """
    Envia ou atualiza registros no Neon utilizando uma TEMP TABLE nativa + MERGE/UPSERT.
    Trata colunas com espaços, caracteres especiais e acentos sem erros de parâmetros do SQLAlchemy.

    IMPORTANTE (correção da divergência site x Power BI):
    O arquivo local (PRODUCAO_TLP_TRATADA.xlsx) é um extrato histórico
    COMPLETO, recriado do zero a cada execução — não é incremental.
    Como o upsert por si só só faz INSERT/UPDATE, uma atividade que saiu
    do extrato (foi cancelada/mesclada/removida na fonte) nunca era
    removida do Neon, ficando "órfã" para sempre e inflando os
    indicadores do site (HC, Caixa, Bucket, Esteira etc.) em relação ao
    Power BI, que sempre lê o extrato mais recente do zero.

    Com `sincronizar_exclusoes=True` (padrão), depois do upsert o
    método remove do Neon qualquer linha cuja chave não esteja mais
    presente no `df` local recém-enviado, mantendo o Neon como espelho
    fiel do arquivo local/Power BI.

    OTIMIZAÇÕES:
    - A tabela de staging agora é uma TEMP TABLE nativa do Postgres
      (ON COMMIT DROP), o que evita gerar WAL/History desnecessário e
      remove a necessidade de DROP manual.
    - O UPSERT só efetivamente grava (e gera WAL) nas linhas cujo
      conteúdo realmente mudou — linhas idênticas às já existentes são
      ignoradas via cláusula WHERE ... IS DISTINCT FROM, economizando
      compute e armazenamento de histórico a cada execução.
    - A carga da staging usa COPY nativo do Postgres (via psycopg2) em vez
      de INSERT em lote — dramaticamente mais rápido para volumes grandes
      (dezenas de milhares de linhas), reduzindo o tempo total de execução
      e o tempo de CU consumido.
    """
    if df.empty:
        print("⚠️ Nenhum dado para enviar.")
        return

    # Valida se a coluna chave está no DataFrame
    if coluna_chave not in df.columns:
        raise ValueError(f"A coluna chave '{coluna_chave}' não foi encontrada no DataFrame.")

    # Valida identificadores controlados pelo código (não vêm do Excel)
    nome_tabela = _validar_identificador(nome_tabela)
    coluna_chave = _validar_identificador(coluna_chave)
    tabela_temp = _validar_identificador(f"temp_{nome_tabela}")

    # Remove duplicadas de segurança na chave primária
    df = df.drop_duplicates(subset=[coluna_chave], keep="last")

    engine = obter_engine()

    # Colunas formatadas com aspas duplas (suporta espaços/acentos/caracteres especiais)
    colunas_formatadas = [_quotar_coluna(col) for col in df.columns]
    colunas_str = ", ".join(colunas_formatadas)
    colunas_sem_chave = [_quotar_coluna(col) for col in df.columns if col != coluna_chave]

    with engine.begin() as conn:
        # 1. Garante que a tabela final exista (não mexe nela se já existir)
        df.head(0).to_sql(nome_tabela, conn, if_exists="append", index=False)

        # 2. Garante a criação da Primary Key na coluna chave (checando a coluna certa)
        sql_pk = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = '{nome_tabela}'
                  AND tc.constraint_type = 'PRIMARY KEY'
                  AND kcu.column_name = '{coluna_chave}'
            ) THEN
                EXECUTE 'ALTER TABLE "{nome_tabela}" ADD PRIMARY KEY ("{coluna_chave}")';
            END IF;
        END $$;
        """
        conn.execute(text(sql_pk))

        # 3. Cria a TEMP TABLE nativa (estrutura igual à tabela final, sem constraints),
        #    liberada automaticamente ao fim da transação (ON COMMIT DROP) — não gera
        #    WAL/History persistente como uma tabela normal geraria.
        conn.execute(text(
            f'CREATE TEMP TABLE "{tabela_temp}" '
            f'(LIKE "{nome_tabela}" INCLUDING DEFAULTS) ON COMMIT DROP;'
        ))

        # 4. Carrega os dados na staging via COPY nativo do Postgres — muito mais
        #    rápido que INSERT em lote (10-50x, tipicamente) para volumes grandes,
        #    pois usa um protocolo de streaming em vez de montar/parsear SQL.
        buffer_csv = io.StringIO()
        df.to_csv(buffer_csv, index=False, header=False, na_rep="")
        buffer_csv.seek(0)

        raw_conn = conn.connection  # conexão DBAPI (psycopg2) da MESMA transação
        with raw_conn.cursor() as cur:
            cur.copy_expert(
                f'COPY "{tabela_temp}" ({colunas_str}) FROM STDIN '
                f"WITH (FORMAT csv, NULL '')",
                buffer_csv,
            )

        # 5. UPSERT: só grava (INSERT/UPDATE) as linhas novas ou que realmente mudaram.
        #    A cláusula WHERE compara a linha atual (t) com a nova (EXCLUDED) e pula
        #    silenciosamente qualquer linha idêntica — evitando reescrever no banco
        #    (e no WAL/History) dados que já estavam corretos.
        if colunas_sem_chave:
            updates_str = ", ".join(f"{c} = EXCLUDED.{c}" for c in colunas_sem_chave)
            comparacao_atual = ", ".join(f"t.{c}" for c in colunas_sem_chave)
            comparacao_novo = ", ".join(f"EXCLUDED.{c}" for c in colunas_sem_chave)
            clausula_conflito = (
                f"DO UPDATE SET {updates_str} "
                f"WHERE ({comparacao_atual}) IS DISTINCT FROM ({comparacao_novo})"
            )
        else:
            clausula_conflito = "DO NOTHING"

        sql_upsert = f"""
            INSERT INTO "{nome_tabela}" AS t ({colunas_str})
            SELECT {colunas_str} FROM "{tabela_temp}"
            ON CONFLICT ("{coluna_chave}")
            {clausula_conflito};
        """
        resultado_upsert = conn.execute(text(sql_upsert))
        linhas_gravadas = resultado_upsert.rowcount if resultado_upsert.rowcount is not None else 0
        linhas_ignoradas = len(df) - linhas_gravadas
        print(
            f"✅ {len(df)} registros processados: {linhas_gravadas} gravados "
            f"(novos ou alterados) e {linhas_ignoradas} sem alteração (ignorados)."
        )

        # 6. Remove da tabela oficial qualquer linha cuja chave não existe
        # mais no extrato local atual (linha "órfã" — cancelada/removida na
        # fonte). Isso é o que mantém o Neon (site) igual ao Power BI.
        if sincronizar_exclusoes:
            sql_delete_orfas = f"""
                DELETE FROM "{nome_tabela}"
                WHERE "{coluna_chave}" NOT IN (
                    SELECT "{coluna_chave}" FROM "{tabela_temp}"
                );
            """
            resultado_delete = conn.execute(text(sql_delete_orfas))
            removidas = resultado_delete.rowcount if resultado_delete.rowcount is not None else 0
            if removidas > 0:
                print(f"🗑️ Removidas {removidas} linhas órfãs do Neon (não existem mais no extrato local).")

        # Não é preciso DROP manual: a TEMP TABLE some sozinha ao fim da transação (ON COMMIT DROP)


def obter_chaves_e_hashes_remotos(nome_tabela: str, coluna_chave: str = "numero_atividade"):
    """
    Função mantida para compatibilidade com scripts antigos.
    A verificação de alterações agora é feita nativamente pelo PostgreSQL via UPSERT.
    """
    return {}