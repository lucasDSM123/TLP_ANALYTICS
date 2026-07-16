import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import streamlit as st  # <-- Adicionado

# Carrega as variáveis de ambiente do arquivo .env (rodando localmente)
load_dotenv()

def obter_engine():
    """Cria e retorna o motor de conexão do SQLAlchemy para o Neon."""
    # 1. Tenta pegar do .env (local). Se não achar, tenta pegar dos Secrets do Streamlit (nuvem).
    url_banco = os.getenv("DATABASE_URL") or st.secrets.get("DATABASE_URL")
    
    if not url_banco:
        raise ValueError("A variável DATABASE_URL não foi encontrada no arquivo .env local nem nos Secrets do Streamlit!")
    
    # Garante compatibilidade do SQLAlchemy com o prefixo 'postgresql://'
    if url_banco.startswith("postgres://"):
        url_banco = url_banco.replace("postgres://", "postgresql://", 1)
        
    return create_engine(url_banco)

def enviar_dados_para_neon(df, nome_tabela):
    """
    Salva um DataFrame do Pandas diretamente como uma tabela no Neon.
    Se a tabela já existir, ela será substituída (if_exists='replace').
    """
    try:
        engine = obter_engine()
        print(f"Enviando dados para a tabela '{nome_tabela}' nel Neon...")
        
        # Envia para o banco
        df.to_sql(
            name=nome_tabela,
            con=engine,
            if_exists="replace",  # 'replace' reconstrói a tabela, 'append' adiciona novas linhas
            index=False           # Não salva o índice do pandas como uma coluna no banco
        )
        print("Dados enviados com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar dados para o banco: {e}")

def ler_dados_do_neon(nome_tabela):
    """
    Lê uma tabela do Neon e retorna como um DataFrame do Pandas para usar no seu site.
    """
    try:
        engine = obter_engine()
        print(f"Buscando dados da tabela '{nome_tabela}' no Neon...")
        
        # Faz uma query simples no banco e lê direto no Pandas
        query = f"SELECT * FROM {nome_tabela}"
        df = pd.read_sql(query, con=engine)
        return df
    except Exception as e:
        print(f"Erro ao ler dados do banco: {e}")
        return None