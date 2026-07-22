import sys
import time
from pathlib import Path

import pandas as pd
from services.database import enviar_dados_para_neon

CAMINHO_ARQUIVO = Path("data/PRODUCAO_TLP_TRATADA.xlsx")
NOME_TABELA = "producao_tlp_tratada"
COLUNA_CHAVE = "numero_atividade"


def executar_upload() -> bool:
    """Executa o upload dos dados tratados para o Neon.

    Retorna True em caso de sucesso e False em caso de falha, para que o
    código de saída do processo (sys.exit) reflita corretamente o resultado
    e o orquestrador consiga detectar falhas nesta etapa.
    """
    inicio = time.time()

    if not CAMINHO_ARQUIVO.exists():
        print(f"[ERRO] Arquivo não encontrado: {CAMINHO_ARQUIVO.resolve()}")
        return False

    print(f"📖 Lendo arquivo local: {CAMINHO_ARQUIVO}")
    try:
        df = pd.read_excel(CAMINHO_ARQUIVO)
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo Excel: {e}")
        return False

    if df.empty:
        print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
        return False

    if COLUNA_CHAVE not in df.columns:
        print(
            f"[ERRO] Coluna chave '{COLUNA_CHAVE}' não encontrada no arquivo. "
            f"Colunas disponíveis: {list(df.columns)}"
        )
        return False

    # Remove linhas duplicadas pela coluna chave, mantendo a última ocorrência
    total_antes = len(df)
    df = df.drop_duplicates(subset=[COLUNA_CHAVE], keep="last")
    total_depois = len(df)

    if total_antes != total_depois:
        print(f"🧹 Removidas {total_antes - total_depois} linhas duplicadas em '{COLUNA_CHAVE}'.")

    print(f"🚀 Enviando/Atualizando {len(df)} registros no Neon...")

    try:
        enviar_dados_para_neon(
            df=df,
            nome_tabela=NOME_TABELA,
            coluna_chave=COLUNA_CHAVE,
        )
    except Exception as e:
        print(f"[ERRO] Falha ao enviar dados para o Neon: {e}")
        return False

    duracao = time.time() - inicio
    print(f"✅ Upload concluído em {duracao:.1f}s ({len(df)} registros).")
    return True


if __name__ == "__main__":
    sucesso = executar_upload()
    sys.exit(0 if sucesso else 1)