import glob
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from services.database import enviar_dados_para_neon

# Mesmo arquivo da base de Cotas por Atividade (upload_dados_cotas.py), só
# que lendo a outra aba: "Todas_Cidades", que traz a mesma capacidade só
# que em MINUTOS em vez de em número de atividades.
CAMINHO_GLOB = "data/Cota_Cidades*.xlsx"
NOME_ABA = "Todas_Cidades"
NOME_TABELA = "cotas_cidades_minutos"
COLUNA_CHAVE = "chave_cota_minutos"

# A aba vem em formato de árvore "achatada": pra cada Cluster/Cidade/Data,
# uma linha de Time Slot (ex.: "08:30-10:30", já um TOTAL agregado) seguida
# das linhas de Atividade daquele slot (Instalação, Reparo...), cujos
# valores somados batem exatamente com a linha do slot acima. Como a linha
# de slot é só a soma das linhas de atividade, subimos apenas o nível de
# Atividade — dá pra recalcular qualquer total agrupando por Cluster/Cidade/
# Horário, exatamente como já é feito com a base de Cotas por Atividade.
PADRAO_SLOT = re.compile(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}$")

COLUNAS_CHAVE_COMPOSTA = ["Cluster", "Cidade", "Data", "Horário", "Atividade"]


def _localizar_arquivo() -> Path | None:
    arquivos = sorted(glob.glob(CAMINHO_GLOB), key=os.path.getmtime, reverse=True)
    return Path(arquivos[0]) if arquivos else None


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Achata a árvore Time Slot > Atividade da aba "Todas_Cidades" em linhas
    (Cluster, Cidade, Data, Horário, Atividade, Cota, Real, GAP) — mesmo
    formato da aba "Cotas" (só que os três últimos campos em MINUTOS em vez
    de em número de atividades), pra reaproveitar as mesmas funções de
    agregação/exibição já existentes em services/cotas.py.
    """
    df = df.rename(columns=lambda c: c.strip())

    col_descricao = "Time slots/Categorias da capacidade"
    df[col_descricao] = df[col_descricao].astype(str).str.strip()
    eh_slot = df[col_descricao].str.match(PADRAO_SLOT)

    # A linha de slot marca o início de um novo grupo — propaga o horário
    # pra baixo, pras linhas de atividade que vêm logo em seguida.
    df["Horário"] = df[col_descricao].where(eh_slot).ffill()
    df["Atividade"] = df[col_descricao].where(~eh_slot)

    # Fica só com as linhas de Atividade (o nível de detalhe); as linhas de
    # slot são puro agregado e não entram na tabela — ver docstring acima.
    df = df[~eh_slot].copy()

    df = df.rename(columns={"Cota": "Cota", "Usado(a)": "Real"})
    df["Cota"] = pd.to_numeric(df["Cota"], errors="coerce")
    df["Real"] = pd.to_numeric(df["Real"], errors="coerce")

    # Categoria que nem chegou a ter cota aberta nesse slot (linha 100% NaN)
    # não representa capacidade nenhuma — descarta.
    df = df.dropna(subset=["Cota"])
    df["Real"] = df["Real"].fillna(0)
    df["GAP"] = df["Real"] - df["Cota"]

    for col in ("Cota", "Real", "GAP"):
        df[col] = df[col].astype(int)

    return df[["Cluster", "Cidade", "Data", "Horário", "Atividade", "Cota", "Real", "GAP"]]


def executar_upload() -> bool:
    """Executa o upload da base de Cota x Cidades EM MINUTOS (aba
    "Todas_Cidades") para o Neon.

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
        df_bruto = pd.read_excel(caminho_arquivo, sheet_name=NOME_ABA, engine="calamine")
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo Excel (aba '{NOME_ABA}'): {e}")
        return False
    duracao_leitura = time.time() - inicio_leitura
    print(f"⏱️  Leitura do Excel: {duracao_leitura:.1f}s")

    if df_bruto.empty:
        print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
        return False

    if "Time slots/Categorias da capacidade" not in [c.strip() for c in df_bruto.columns]:
        print(
            "[ERRO] Coluna 'Time slots/Categorias da capacidade' não encontrada no arquivo. "
            f"Colunas disponíveis: {list(df_bruto.columns)}"
        )
        return False

    print(f"📊 Dimensões do extrato bruto: {len(df_bruto)} linhas x {len(df_bruto.columns)} colunas")

    try:
        df = _normalizar(df_bruto)
    except Exception as e:
        print(f"[ERRO] Falha ao normalizar a árvore Time Slot > Atividade: {e}")
        return False

    if df.empty:
        print("⚠️ Nenhuma linha de Atividade com Cota aberta encontrada. Nenhum dado enviado.")
        return False

    print(f"📐 Linhas normalizadas (nível Atividade): {len(df)}")

    # Monta a chave sintética (Cluster|Cidade|Data|Horário|Atividade) que
    # identifica uma linha única — usada como Primary Key no Neon pra
    # permitir o upsert/exclusão de órfãs.
    df[COLUNA_CHAVE] = df[COLUNAS_CHAVE_COMPOSTA].astype(str).agg("|".join, axis=1)

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
    print(f"   Detalhamento: leitura local {duracao_leitura:.1f}s | Neon {duracao_envio:.1f}s")
    return True


if __name__ == "__main__":
    sucesso = executar_upload()
    sys.exit(0 if sucesso else 1)
