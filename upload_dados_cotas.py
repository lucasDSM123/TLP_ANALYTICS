import glob
import os
import sys
import time
from pathlib import Path

import pandas as pd
from services.database import enviar_dados_para_neon

# Mesmo padrão de arquivo usado por services/cotas.py (COTAS_DATA_GLOB):
# Cota_Cidades.xlsx ou Cota_Cidades_DD-MM-AAAA.xlsx. Pega sempre o mais
# recente pela data de modificação, caso haja mais de um na pasta.
CAMINHO_GLOB = "data/Cota_Cidades*.xlsx"
NOME_ABA = "Cotas"
NOME_TABELA = "cotas_cidades"
COLUNA_CHAVE = "chave_cota"

# Colunas que, juntas, identificam uma linha única na base (não existe uma
# coluna de ID pronta como "numero_atividade" na base de produção — então
# montamos uma chave sintética a partir dessas colunas).
COLUNAS_CHAVE_COMPOSTA = [
    "Cluster",
    "Cidade",
    "Data",
    "Segmento",
    "Tipo de Serviço",
    "Atividade",
    "Horário",
]


def _localizar_arquivo() -> Path | None:
    arquivos = sorted(glob.glob(CAMINHO_GLOB), key=os.path.getmtime, reverse=True)
    return Path(arquivos[0]) if arquivos else None


def executar_upload() -> bool:
    """Executa o upload da base de Cota x Cidades (aba "Cotas") para o Neon.

    Retorna True em caso de sucesso e False em caso de falha, para que o
    código de saída do processo (sys.exit) reflita corretamente o resultado
    e o orquestrador consiga detectar falhas nesta etapa.
    """
    inicio_total = time.time()

    caminho_arquivo = _localizar_arquivo()
    if caminho_arquivo is None:
        print(f"[ERRO] Nenhum arquivo encontrado em: {CAMINHO_GLOB}")
        return False

    tamanho_mb = caminho_arquivo.stat().st_size / (1024 * 1024)
    print(f"📖 Lendo arquivo local: {caminho_arquivo} (aba '{NOME_ABA}', {tamanho_mb:.2f} MB)")

    inicio_leitura = time.time()
    try:
        df = pd.read_excel(caminho_arquivo, sheet_name=NOME_ABA, engine="calamine")
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo Excel (aba '{NOME_ABA}'): {e}")
        return False
    duracao_leitura = time.time() - inicio_leitura
    print(f"⏱️  Leitura do Excel: {duracao_leitura:.1f}s")

    if df.empty:
        print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
        return False

    colunas_faltando = [c for c in COLUNAS_CHAVE_COMPOSTA if c not in df.columns]
    if colunas_faltando:
        print(
            f"[ERRO] Coluna(s) esperada(s) não encontrada(s) no arquivo: {colunas_faltando}. "
            f"Colunas disponíveis: {list(df.columns)}"
        )
        return False

    print(f"📊 Dimensões do extrato: {len(df)} linhas x {len(df.columns)} colunas")

    # Monta a chave sintética (Cluster|Cidade|Data|Segmento|Tipo de Serviço|
    # Atividade|Horário) que identifica uma linha única — usada como Primary
    # Key no Neon para permitir o upsert/exclusão de órfãs.
    df[COLUNA_CHAVE] = (
        df[COLUNAS_CHAVE_COMPOSTA].astype(str).agg("|".join, axis=1)
    )

    # Remove linhas duplicadas pela chave, mantendo a última ocorrência
    total_antes = len(df)
    df = df.drop_duplicates(subset=[COLUNA_CHAVE], keep="last")
    total_depois = len(df)

    if total_antes != total_depois:
        print(f"🧹 Removidas {total_antes - total_depois} linhas duplicadas em '{COLUNA_CHAVE}'.")

    print(f"🚀 Enviando/Atualizando {len(df)} registros no Neon (tabela '{NOME_TABELA}')...")

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
