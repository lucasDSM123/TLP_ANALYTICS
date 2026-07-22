import pandas as pd
from services.database import enviar_dados_para_neon

def executar_upload():
    caminho_arquivo = "data/PRODUCAO_TLP_TRATADA.xlsx"
    nome_tabela = "producao_tlp_tratada"
    coluna_chave = "numero_atividade"

    try:
        print(f"📖 Lendo arquivo local: {caminho_arquivo}")
        df = pd.read_excel(caminho_arquivo)

        if df.empty:
            print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
            return

        # REMOVE LINHAS DUPLICADAS PELA COLUNA CHAVE
        total_antes = len(df)
        df = df.drop_duplicates(subset=[coluna_chave], keep="last")
        total_depois = len(df)

        if total_antes != total_depois:
            print(f"🧹 Removidas {total_antes - total_depois} linhas duplicadas em '{coluna_chave}'.")

        print(f"🚀 Enviando/Atualizando {len(df)} registros no Neon...")
        
        enviar_dados_para_neon(
            df=df, 
            nome_tabela=nome_tabela, 
            coluna_chave=coluna_chave
        )

    except Exception as e:
        print(f"\n[ERRO] Falha ao processar o upload: {e}")

if __name__ == "__main__":
    executar_upload()