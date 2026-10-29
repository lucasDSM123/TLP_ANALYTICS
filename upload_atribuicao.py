"""
Envia para o Neon as atividades de hoje (D0) e dos próximos dias (D+1, D+2) que o
`atribuição.py` baixa do OFSC — alimenta a aba "Atribuição" do TLP Analytics
(quantos técnicos/HC são necessários para atender a demanda).

Fluxo diário:
    1) python atribuição.py          # baixa os 3 arquivos para D:\\planejamento\\ZEUS D+3
    2) python upload_atribuicao.py   # lê os arquivos, cruza com data/Mapeamento_Atribuicao.xlsx e grava no Neon

Uso:
    python upload_atribuicao.py                      # pasta padrão
    python upload_atribuicao.py --pasta "D:\\outra"  # outra pasta
    python upload_atribuicao.py --dry-run            # não grava no Neon; gera Excel p/ conferir

Mapeamento (data/Mapeamento_Atribuicao.xlsx) — mesmas tabelas da aba PROCV da planilha:
    Cidades  (CIDADE, CLUSTER, BUCKET)   Janelas (JANELA, TIME)   Recursos (RECURSO, CONTAR)
Técnico novo / cidade nova? Basta incluir a linha no Excel e rodar de novo — não precisa
mexer no site. O resumo no fim do upload (e a aba) avisam quem ficou sem cadastro.
"""
import argparse
import glob
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from services.atribuicao import (
    MAPEAMENTO_PADRAO, REGRAS, TABELA, calcular_quadro, carregar_mapeamento,
    hoje_local, preparar_atividades, recursos_sem_cadastro,
)

PASTA_PADRAO = os.environ.get("ATRIBUICAO_PASTA", r"D:\Base Zeus\ZEUS D+3")
ARQUIVO_DRY_RUN = Path("data") / "atribuicao_dry_run.xlsx"


def _ler_arquivos(pasta: str, mapa: dict) -> pd.DataFrame:
    arquivos = sorted(glob.glob(os.path.join(pasta, "*.xlsx")), key=os.path.getmtime)
    if not arquivos:
        raise FileNotFoundError(f"Nenhum .xlsx em {pasta}. Rode o atribuição.py antes.")

    por_dia: dict = {}  # dia -> (mtime, DataFrame); se dois arquivos trazem o mesmo dia, vence o mais novo
    for caminho in arquivos:
        mtime = os.path.getmtime(caminho)
        print(f"📖 Lendo {os.path.basename(caminho)} ...")
        raw = pd.read_excel(caminho, engine="calamine")
        at = preparar_atividades(raw, mapa)
        at["gerado_em"] = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
        for dia, g in at.groupby("dia"):
            if dia not in por_dia or mtime >= por_dia[dia][0]:
                por_dia[dia] = (mtime, g)

    hoje = hoje_local()
    dias = sorted(d for d in por_dia if d >= hoje)  # D0 em diante (dias passados não interessam)
    if not dias:
        raise RuntimeError(
            f"Os arquivos são antigos (último dia: {max(por_dia)}; hoje: {hoje}). Rode o atribuição.py de novo."
        )
    df = pd.concat([por_dia[d][1] for d in dias], ignore_index=True)
    df["dia"] = df["dia"].astype(str)
    df["chave"] = df["dia"] + "|" + df.groupby("dia").cumcount().astype(str)
    return df


def _resumo(df: pd.DataFrame) -> None:
    print("\n📊 Resumo (demanda / HC necessário):")
    for dia, g in df.groupby("dia"):
        partes = []
        for uf in REGRAS:
            t = calcular_quadro(g, uf).iloc[-1]
            partes.append(f"{uf}: {t['TOTAL']} atividades → {t['HC_NEC']} HC (hoje {t['HC']})")
        print(f"   {dia}  " + "  |  ".join(partes))
    if "lado" not in df.columns or not df["lado"].isin(["BA", "TT"]).any():
        print("\n⚠️ Nenhuma atividade com lado BA/TT: o relatório do OFSC não trouxe a coluna \"Tipo de Atividade\".")
    else:
        print("\n📊 Atividades por lado: " + "  ".join(f"{k}={v}" for k, v in df["lado"].value_counts().items()))
    sem = recursos_sem_cadastro(df)
    if not sem.empty:
        print(f"\n⚠️ {len(sem)} técnico(s) SEM cadastro em Recursos (a atividade não entra na conta):")
        print(sem.to_string(index=False))


def executar_upload(pasta: str, dry_run: bool) -> bool:
    inicio = time.time()
    try:
        mapa = carregar_mapeamento(MAPEAMENTO_PADRAO)
        df = _ler_arquivos(pasta, mapa)
    except Exception as e:
        print(f"[ERRO] {e}")
        return False

    print(f"✅ {len(df)} atividades em {df['dia'].nunique()} dia(s).")
    _resumo(df)

    if dry_run:
        ARQUIVO_DRY_RUN.parent.mkdir(exist_ok=True)
        df.drop(columns=["chave"]).to_excel(ARQUIVO_DRY_RUN, index=False)
        print(f"\n🧪 --dry-run: nada foi gravado no Neon. Conferência em {ARQUIVO_DRY_RUN}")
        return True

    from services.database import enviar_dados_para_neon  # import tardio: dry-run não precisa de .env

    # sincronizar_exclusoes=True: a tabela é sempre o espelho dos arquivos mais recentes
    # (o dia que saiu da janela D0..D+2 sai também do Neon).
    enviar_dados_para_neon(df, TABELA, coluna_chave="chave", sincronizar_exclusoes=True)
    print(f"\n🚀 Atribuição enviada ao Neon em {time.time() - inicio:.1f}s")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Envia as atividades D0..D+2 do OFSC para a aba Atribuição.")
    ap.add_argument("--pasta", default=PASTA_PADRAO)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(0 if executar_upload(args.pasta, args.dry_run) else 1)
