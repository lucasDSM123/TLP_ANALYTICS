"""
Diagnóstico de divergência Site (Neon) vs Power BI (arquivo local).

Compara o conjunto de `numero_atividade` que está no Neon com o conjunto
que está no arquivo local PRODUCAO_TLP_TRATADA.xlsx (a mesma base que o
Power BI usa). Qualquer numero_atividade que está no Neon mas NÃO está
mais no arquivo local é uma linha "fantasma": ficou órfã porque o
upload atual só faz INSERT/UPDATE (upsert), nunca DELETE.

Rode com: python diagnostico_divergencia.py
"""
import pandas as pd
from services.database import ler_dados_do_neon
import config

CAMINHO_LOCAL = "data/PRODUCAO_TLP_TRATADA.xlsx"
COLUNA_CHAVE = "numero_atividade"


def main():
    print("📖 Lendo base local (a mesma que o Power BI usa)...")
    df_local = pd.read_excel(CAMINHO_LOCAL)
    chaves_local = set(df_local[COLUNA_CHAVE].tolist())
    print(f"   -> {len(df_local)} linhas / {len(chaves_local)} chaves únicas")

    print("🌐 Lendo base do Neon (a que o site usa)...")
    df_neon = ler_dados_do_neon(config.DATABASE_TABLE)
    chaves_neon = set(df_neon[COLUNA_CHAVE].tolist())
    print(f"   -> {len(df_neon)} linhas / {len(chaves_neon)} chaves únicas")

    orfas = chaves_neon - chaves_local
    novas = chaves_local - chaves_neon

    print("\n================ RESULTADO ================")
    print(f"Linhas no Neon que NÃO existem mais no arquivo local (órfãs/fantasma): {len(orfas)}")
    print(f"Linhas no arquivo local que ainda não foram enviadas ao Neon: {len(novas)}")

    if orfas:
        df_orfas = df_neon[df_neon[COLUNA_CHAVE].isin(orfas)]
        print("\nAmostra das linhas órfãs (as que estão inflando os indicadores do site):")
        cols_mostrar = [c for c in ["numero_atividade", "Data", "Estado", "Cluster", "Lado", "Status", "Contratada"] if c in df_orfas.columns]
        print(df_orfas[cols_mostrar].head(20).to_string(index=False))

        print("\nDistribuição das órfãs por Data:")
        if "Data" in df_orfas.columns:
            print(df_orfas["Data"].value_counts().sort_index())

        print("\nDistribuição das órfãs por Estado:")
        if "Estado" in df_orfas.columns:
            print(df_orfas["Estado"].value_counts())

    print("\n✅ Se 'orfas' > 0, é essa a causa da divergência entre o site e o Power BI.")


if __name__ == "__main__":
    main()
