"""
Coleta o relatório de BD da Vivo (site interno) e grava no Neon, alimentando
a aba "Backlog Reparo" do TLP Analytics.

⚠️ Precisa rodar numa máquina com acesso à rede corporativa (o site da Vivo é
um IP interno) — o Streamlit Cloud não enxerga esse endereço. O site do
TLP Analytics só lê o que este script já gravou no Neon.

Uso:
    python upload_backlog_reparo.py                       # GPON / TLP (padrão)
    python upload_backlog_reparo.py --backfill            # + 30 dias do gráfico (rode 1x no começo)
    python upload_backlog_reparo.py --tecnologia GPON UGR --empreiteira TLP
    python upload_backlog_reparo.py --dry-run             # não grava no Neon; gera um Excel p/ conferir

Agendamento: o relatório da Vivo só atualiza em alguns horários do dia;
rodar a cada 20 minutos (Agendador de Tarefas do Windows) é mais que suficiente.

Tabelas (ver sql/backlog_reparo.sql):
    backlog_reparo_atual      -> foto atual, sobrescrita a cada coleta
    backlog_reparo_historico  -> um registro por cluster/dia, acumulado para sempre
"""
import argparse
import itertools
import sys
import time
from pathlib import Path

import pandas as pd

from services.backlog_vivo import BASE_PADRAO, coletar

TABELA_ATUAL = "backlog_reparo_atual"
TABELA_HISTORICO = "backlog_reparo_historico"
ARQUIVO_DRY_RUN = Path("data") / "backlog_reparo_dry_run.xlsx"


def _gravar_no_neon(atual: pd.DataFrame, hist: pd.DataFrame) -> None:
    # Import tardio: o --dry-run não precisa de banco/.env configurado.
    from criar_tabela_backlog_reparo import criar_tabelas
    from services.database import enviar_dados_para_neon

    criar_tabelas()  # idempotente — garante tabelas e índices antes do upsert

    # sincronizar_exclusoes=False: NÃO apaga o que não veio nesta coleta.
    #   • histórico precisa acumular (o site só mostra 8 dias);
    #   • a foto atual é de várias tecnologias/empreiteiras — uma coleta de
    #     GPON/TLP não pode apagar as linhas de UGR/TLP.
    # (a página lê só a coleta mais recente de cada combinação)
    enviar_dados_para_neon(atual, TABELA_ATUAL, coluna_chave="chave", sincronizar_exclusoes=False)
    enviar_dados_para_neon(hist, TABELA_HISTORICO, coluna_chave="chave", sincronizar_exclusoes=False)


def executar_upload(tecnologias: list[str], empreiteiras: list[str], backfill: bool,
                    dry_run: bool, base: str) -> bool:
    inicio = time.time()
    atuais, historicos = [], []

    for tec, emp in itertools.product(tecnologias, empreiteiras):
        print(f"🌐 Coletando {tec} / {emp} em {base} ...")
        try:
            atual, hist = coletar(tec, emp, backfill=backfill, base=base)
        except Exception as e:  # noqa: BLE001 — qualquer falha de rede/layout encerra com mensagem clara
            print(f"[ERRO] Falha ao coletar {tec}/{emp}: {e!r}")
            return False
        n_clusters = int((~atual["eh_total"]).sum())
        print(f"   ✔ {n_clusters} clusters + total | histórico: {len(hist)} registros "
              f"({hist['data'].min()} → {hist['data'].max()})")
        atuais.append(atual)
        historicos.append(hist)

    atual = pd.concat(atuais, ignore_index=True)
    hist = pd.concat(historicos, ignore_index=True)

    if dry_run:
        ARQUIVO_DRY_RUN.parent.mkdir(exist_ok=True)
        with pd.ExcelWriter(ARQUIVO_DRY_RUN) as xw:
            atual.to_excel(xw, sheet_name="atual", index=False)
            hist.to_excel(xw, sheet_name="historico", index=False)
        print(f"🧪 Dry-run: nada foi enviado ao Neon. Conferência salva em {ARQUIVO_DRY_RUN}")
        return True

    print(f"🚀 Enviando ao Neon: {len(atual)} linhas em '{TABELA_ATUAL}' e {len(hist)} em '{TABELA_HISTORICO}'...")
    try:
        _gravar_no_neon(atual, hist)
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao enviar dados para o Neon: {e!r}")
        return False

    print(f"✅ Upload concluído em {time.time() - inicio:.1f}s.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Coleta o Backlog de Reparo (BD) da Vivo e grava no Neon.")
    ap.add_argument("--tecnologia", nargs="+", default=["GPON"], help="UGR, GPON, METALICO (padrão: GPON)")
    ap.add_argument("--empreiteira", nargs="+", default=["TLP"], help="RS, TLP, VIVO, TLSV, NOEMP (padrão: TLP)")
    ap.add_argument("--backfill", action="store_true", help="também baixa os 30 dias do gráfico (total + clusters)")
    ap.add_argument("--dry-run", action="store_true", help="não grava no Neon; só gera um Excel de conferência")
    ap.add_argument("--base", default=BASE_PADRAO, help="URL base do relatório (padrão: BACKLOG_VIVO_BASE ou o IP interno)")
    args = ap.parse_args()

    ok = executar_upload(args.tecnologia, args.empreiteira, args.backfill, args.dry_run, args.base)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
