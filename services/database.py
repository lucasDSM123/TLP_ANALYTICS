from sqlalchemy import create_engine, text
import pandas as pd
import config

def obter_engine():
    """
    Retorna a instância do engine do SQLAlchemy configurada com a URL do banco.
    """
    return create_engine(config.DATABASE_URL)

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

def enviar_dados_para_neon(df: pd.DataFrame, nome_tabela: str, coluna_chave: str = "numero_atividade"):
    """
    Envia ou atualiza registros no Neon utilizando uma tabela temporária (STAGING) + MERGE/UPSERT.
    Trata colunas com espaços, caracteres especiais e acentos sem erros de parâmetros do SQLAlchemy.
    """
    if df.empty:
        print("⚠️ Nenhum dado para enviar.")
        return

    # Valida se a coluna chave está no DataFrame
    if coluna_chave not in df.columns:
        raise ValueError(f"A coluna chave '{coluna_chave}' não foi encontrada no DataFrame.")

    # Remove duplicadas de segurança na chave primária
    df = df.drop_duplicates(subset=[coluna_chave], keep="last")

    engine = obter_engine()
    tabela_temp = f"temp_{nome_tabela}"

    with engine.begin() as conn:
        # 1. Envia os dados para a tabela temporária
        df.to_sql(tabela_temp, conn, if_exists="replace", index=False)

        # 2. Garante que a tabela final exista
        df.head(0).to_sql(nome_tabela, conn, if_exists="append", index=False)

        # 3. Garante a criação da Primary Key / Índice Único na coluna chave
        sql_pk = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 
                FROM information_schema.table_constraints 
                WHERE table_name = '{nome_tabela}' 
                  AND constraint_type = 'PRIMARY KEY'
            ) THEN
                EXECUTE 'ALTER TABLE "' || '{nome_tabela}' || '" ADD PRIMARY KEY ("' || '{coluna_chave}' || '")';
            END IF;
        END $$;
        """
        conn.execute(text(sql_pk))

        # 4. Prepara a lista de colunas formatadas entre aspas
        colunas_formatadas = [f'"{col}"' for col in df.columns]
        colunas_str = ", ".join(colunas_formatadas)

        # 5. Prepara a cláusula de UPDATE do ON CONFLICT
        updates = [f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col != coluna_chave]
        
        if updates:
            updates_str = ", ".join(updates)
            clausula_conflito = f"DO UPDATE SET {updates_str}"
        else:
            clausula_conflito = "DO NOTHING"

        # 6. Executa o UPSERT (Copia da tabela temp para a tabela oficial)
        sql_upsert = f"""
            INSERT INTO "{nome_tabela}" ({colunas_str})
            SELECT {colunas_str} FROM "{tabela_temp}"
            ON CONFLICT ("{coluna_chave}")
            {clausula_conflito};
        """
        conn.execute(text(sql_upsert))

        # 7. Remove a tabela temporária
        conn.execute(text(f'DROP TABLE IF EXISTS "{tabela_temp}";'))

        print(f"✅ {len(df)} registros processados e atualizados com sucesso na tabela '{nome_tabela}'.")

def obter_chaves_e_hashes_remotos(nome_tabela: str, coluna_chave: str = "numero_atividade"):
    """
    Função mantida para compatibilidade com scripts antigos.
    A verificação de alterações agora é feita nativamente pelo PostgreSQL via UPSERT.
    """
    return {}