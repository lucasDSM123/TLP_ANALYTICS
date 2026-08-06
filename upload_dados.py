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
    inicio_total = time.time()

    if not CAMINHO_ARQUIVO.exists():
        print(f"[ERRO] Arquivo não encontrado: {CAMINHO_ARQUIVO.resolve()}")
        return False

    tamanho_mb = CAMINHO_ARQUIVO.stat().st_size / (1024 * 1024)
    print(f"📖 Lendo arquivo local: {CAMINHO_ARQUIVO} ({tamanho_mb:.2f} MB)")

    inicio_leitura = time.time()
    try:
        df = pd.read_excel(CAMINHO_ARQUIVO, engine="calamine")
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo Excel: {e}")
        return False
    duracao_leitura = time.time() - inicio_leitura
    print(f"⏱️  Leitura do Excel: {duracao_leitura:.1f}s")

    if df.empty:
        print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
        return False

    if COLUNA_CHAVE not in df.columns:
        print(
            f"[ERRO] Coluna chave '{COLUNA_CHAVE}' não encontrada no arquivo. "
            f"Colunas disponíveis: {list(df.columns)}"
        )
        return False

    print(f"📊 Dimensões do extrato: {len(df)} linhas x {len(df.columns)} colunas")

    # Remove linhas duplicadas pela coluna chave, mantendo a última ocorrência
    total_antes = len(df)
    df = df.drop_duplicates(subset=[COLUNA_CHAVE], keep="last")
    total_depois = len(df)

    if total_antes != total_depois:
        print(f"🧹 Removidas {total_antes - total_depois} linhas duplicadas em '{COLUNA_CHAVE}'.")

    print(f"🚀 Enviando/Atualizando {len(df)} registros no Neon...")

    inicio_envio = time.time()
    try:
        enviar_dados_para_neon(
            df=df,
            nome_tabela=NOME_TABELA,
            coluna_chave=COLUNA_CHAVE,
        )
    except Exception as e:
        print(f"[ERRO] Falha ao enviar dados para o Neon: {e}")
        return False
    duracao_envio = time.time() - inicio_envio
    print(f"⏱️  Comunicação com o Neon (staging + upsert + delete órfãs): {duracao_envio:.1f}s")

    duracao_total = time.time() - inicio_total
    print(f"✅ Upload concluído em {duracao_total:.1f}s no total ({len(df)} registros).")
    print(
        f"   Detalhamento: leitura local {duracao_leitura:.1f}s "
        f"| Neon {duracao_envio:.1f}s"
    )
    return True


if __name__ == "__main__":
    sucesso = executar_upload()
    sys.exit(0 if sucesso else 1)