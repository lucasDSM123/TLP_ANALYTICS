import pandas as pd
import config  # Importa o seu config.py com as cores e caminhos
from services.database import enviar_dados_para_neon

def fazer_upload_da_base():
    try:
        print(f"Lendo o arquivo local em: {config.DATA_PATH}")
        
        # Carrega a sua planilha Excel definida no config.py
        df_local = pd.read_excel(config.DATA_PATH)
        
        # Envia os dados para a tabela do Neon definida no config.py
        # DATABASE_TABLE está definido como "producao_tlp_tratada"
        enviar_dados_para_neon(df_local, config.DATABASE_TABLE)
        
        print("\n=== PROCESSO DE SINCRONIZAÇÃO CONCLUÍDO COM SUCESSO! ===")
    except Exception as e:
        print(f"\n[ERRO] Falha ao processar o upload: {e}")

if __name__ == "__main__":
    fazer_upload_da_base()