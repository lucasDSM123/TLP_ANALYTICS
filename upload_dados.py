"""
Upload da base tratada (PRODUCAO_TLP_TRATADA.xlsx) para o Neon.

MODOS
-----
(padrão)      INCREMENTAL — só envia/atualiza os dias da "janela" (por padrão
              ontem + hoje) e os dias que o Neon ainda não tem. Os dias mais
              antigos ficam guardados no Neon exatamente como estão e não são
              reenviados, comparados nem apagados.
--completo    Comportamento antigo: reenvia o arquivo inteiro e apaga do Neon
              o que não está mais nele. Use na 1ª carga, depois de adicionar
              coluna nova no Excel e, de preferência, 1x por dia (madrugada)
              como "faxina" que reconcilia tudo.
--verificar   Não grava nada. Compara os dias ANTIGOS (fora da janela) do
              arquivo com o Neon e lista as diferenças — serve para confirmar
              que "de anteontem para trás nada muda".

Uso:
    python upload_dados.py
    python upload_dados.py --janela 3
    python upload_dados.py --completo
    python upload_dados.py --verificar
"""
import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from services.database import (
    colunas_remotas,
    contagem_remota_por_data_status,
    enviar_dados_para_neon,
    listar_datas_remotas,
    remover_por_datas,
)
from services.historico_intradia import registrar_snapshot

CAMINHO_ARQUIVO = Path("data/PRODUCAO_TLP_TRATADA.xlsx")
NOME_TABELA = "producao_tlp_tratada"
COLUNA_CHAVE = "numero_atividade"
COLUNA_DATA = "Data"

JANELA_DIAS_PADRAO = 2  # hoje + ontem
FUSO = ZoneInfo("America/Sao_Paulo")


# ---------------------------------------------------------------------------
# Utilidades de data
# ---------------------------------------------------------------------------
def _datas(serie: pd.Series) -> pd.Series:
    """Coluna Data (texto dd/mm/aa ou datetime) -> datetime; inválidas viram NaT."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    datas = pd.to_datetime(serie, format="%d/%m/%y", errors="coerce")
    if datas.isna().all():
        datas = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return datas


def _corte(janela_dias: int) -> pd.Timestamp:
    """Primeiro dia da janela (data de hoje no fuso de Brasília - (janela-1))."""
    hoje = datetime.now(FUSO).date()
    return pd.Timestamp(hoje - timedelta(days=max(janela_dias, 1) - 1))


def planejar_incremental(df: pd.DataFrame, datas_remotas: list, janela_dias: int) -> dict:
    """Decide o que enviar e o que limpar no Neon. Não toca no banco.

    Retorna:
      df_envio       linhas do arquivo a enviar (janela + dias que o Neon não tem)
      datas_escopo   datas (texto) onde "órfãs" podem ser apagadas (só a janela)
      datas_purgar   datas (texto) de meses anteriores ao do arquivo (virada de
                     mês: já congeladas, saem do Neon como antes)
      dias_faltantes datas do arquivo que o Neon ainda não tinha (fora da janela)
      dias_sumidos   datas da janela que existem no Neon mas NÃO vieram no arquivo
                     (extração suspeita — o upload aborta em vez de apagá-las)
      corte          primeiro dia da janela
    """
    corte = _corte(janela_dias)
    dt_arq = _datas(df[COLUNA_DATA])

    remotas = pd.Series(datas_remotas, dtype="object")
    dt_rem = _datas(remotas) if len(remotas) else pd.Series([], dtype="datetime64[ns]")

    na_janela = dt_arq >= corte
    conhecidas = set(dt_rem.dropna())
    faltante = dt_arq.notna() & ~dt_arq.isin(conhecidas) & ~na_janela

    df_envio = df[na_janela | faltante]

    datas_janela_remota = set(remotas[dt_rem >= corte]) if len(remotas) else set()
    datas_escopo = sorted(set(df.loc[na_janela, COLUNA_DATA]) | datas_janela_remota)

    # Virada de mês: o arquivo só tem o mês corrente. Meses anteriores que
    # ainda estão no Neon (já congelados por congelar_virada) são removidos,
    # como o delete de órfãs fazia antes. Nunca remove nada que o arquivo tenha.
    inicio_mes = pd.Timestamp(corte.year, corte.month, 1)
    primeiro_do_arquivo = dt_arq.min()
    limite = min(inicio_mes, primeiro_do_arquivo) if pd.notna(primeiro_do_arquivo) else inicio_mes
    datas_purgar = sorted(remotas[dt_rem < limite]) if len(remotas) else []

    return {
        "df_envio": df_envio,
        "datas_escopo": datas_escopo,
        "datas_purgar": datas_purgar,
        "dias_faltantes": sorted(set(df.loc[faltante, COLUNA_DATA])),
        "dias_sumidos": sorted(datas_janela_remota - set(df.loc[na_janela, COLUNA_DATA])),
        "corte": corte,
    }


# ---------------------------------------------------------------------------
# Leitura do arquivo
# ---------------------------------------------------------------------------
def _ler_arquivo() -> pd.DataFrame | None:
    if not CAMINHO_ARQUIVO.exists():
        print(f"[ERRO] Arquivo não encontrado: {CAMINHO_ARQUIVO.resolve()}")
        return None

    tamanho_mb = CAMINHO_ARQUIVO.stat().st_size / (1024 * 1024)
    print(f"📖 Lendo arquivo local: {CAMINHO_ARQUIVO} ({tamanho_mb:.2f} MB)")

    inicio = time.time()
    try:
        df = pd.read_excel(CAMINHO_ARQUIVO, engine="calamine")
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo Excel: {e}")
        return None
    print(f"⏱️  Leitura do Excel: {time.time() - inicio:.1f}s")

    if df.empty:
        print("⚠️ O arquivo local está vazio. Nenhum dado enviado.")
        return None

    for coluna in (COLUNA_CHAVE, COLUNA_DATA):
        if coluna not in df.columns:
            print(f"[ERRO] Coluna '{coluna}' não encontrada no arquivo. "
                  f"Colunas disponíveis: {list(df.columns)}")
            return None

    print(f"📊 Dimensões do extrato: {len(df)} linhas x {len(df.columns)} colunas")

    total_antes = len(df)
    df = df.drop_duplicates(subset=[COLUNA_CHAVE], keep="last")
    if total_antes != len(df):
        print(f"🧹 Removidas {total_antes - len(df)} linhas duplicadas em '{COLUNA_CHAVE}'.")
    return df


# ---------------------------------------------------------------------------
# --verificar
# ---------------------------------------------------------------------------
def verificar_historico(janela_dias: int) -> bool:
    """Compara dias ANTIGOS (fora da janela) do arquivo x Neon, por (data, status)."""
    df = _ler_arquivo()
    if df is None:
        return False
    corte = _corte(janela_dias)

    try:
        remoto = contagem_remota_por_data_status(NOME_TABELA)
    except Exception as e:
        print(f"[ERRO] Não foi possível ler o Neon: {e}")
        return False

    df = df.assign(_dt=_datas(df[COLUNA_DATA]), _st=df["Status"].fillna("(vazio)"))
    local = (df[df["_dt"] < corte].groupby([COLUNA_DATA, "_st"]).size()
             .rename("local").reset_index().rename(columns={COLUNA_DATA: "data", "_st": "status"}))

    remoto["status"] = remoto["status"].fillna("(vazio)")
    remoto["_dt"] = _datas(remoto["data"])
    remoto = remoto[remoto["_dt"] < corte].rename(columns={"n": "neon"}).drop(columns="_dt")

    cmp = local.merge(remoto, on=["data", "status"], how="outer").fillna({"local": 0, "neon": 0})
    cmp["dif"] = cmp["neon"].astype(int) - cmp["local"].astype(int)
    dif = cmp[cmp["dif"] != 0].copy()

    print(f"\n🔎 Dias anteriores a {corte:%d/%m/%y} (fora da janela de {janela_dias} dia(s)):")
    if dif.empty:
        print("✅ Nenhuma diferença: o histórico do Neon é igual ao do arquivo.")
        return True

    dif["_o"] = _datas(dif["data"])
    dif = dif.sort_values(["_o", "status"]).drop(columns="_o")
    print(f"⚠️ {len(dif)} combinações (data, status) divergentes "
          f"(dif = Neon − arquivo):\n{dif.to_string(index=False)}")
    print("\n➡️ Rode `python upload_dados.py --completo` para reconciliar. "
          "Se isso aparecer com frequência, aumente a janela (--janela N).")
    return False


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
def executar_upload(completo: bool = False, janela_dias: int = JANELA_DIAS_PADRAO) -> bool:
    """Retorna True em caso de sucesso e False em caso de falha, para que o
    código de saída do processo (sys.exit) reflita corretamente o resultado."""
    inicio_total = time.time()

    df = _ler_arquivo()
    if df is None:
        return False

    # Virada de mês: congela o mês anterior (ainda no Neon) ANTES de qualquer
    # remoção. Usa o arquivo COMPLETO. Falha aqui NUNCA bloqueia o upload.
    try:
        from services.congelamento_automatico import congelar_virada
        congelados = congelar_virada(df)
        if congelados:
            print(f"❄️  Meses congelados automaticamente: "
                  f"{', '.join(f'{m:02d}/{a}' for a, m in congelados)}")
    except Exception as e:
        print(f"⚠️ Congelamento automático do mês anterior não executado ({e}). "
              f"O upload segue normalmente.")

    # ---- decide o modo ----------------------------------------------------
    plano = None
    if not completo:
        try:
            datas_remotas = listar_datas_remotas(NOME_TABELA)
            colunas_neon = colunas_remotas(NOME_TABELA)
        except Exception as e:
            print(f"ℹ️ Tabela ainda não existe/legível no Neon ({e}) — usando modo COMPLETO.")
            datas_remotas, colunas_neon = [], set()

        novas = [c for c in df.columns if c not in colunas_neon]
        if not datas_remotas:
            print("ℹ️ Neon sem dados na tabela — modo COMPLETO (carga inicial).")
        elif novas:
            print(f"ℹ️ Colunas novas no arquivo {novas} — modo COMPLETO para preenchê-las nos dias antigos.")
        else:
            plano = planejar_incremental(df, datas_remotas, janela_dias)
            if not (_datas(df[COLUNA_DATA]) >= plano["corte"]).any():
                print(f"[ERRO] O arquivo não tem nenhuma linha a partir de {plano['corte']:%d/%m/%y}. "
                      f"Extração suspeita — nada foi alterado no Neon. "
                      f"(Se for intencional, rode com --completo.)")
                return False
            if plano["dias_sumidos"]:
                print(f"[ERRO] O Neon tem dados de {', '.join(plano['dias_sumidos'])} mas o arquivo não tem "
                      f"nenhuma linha desse(s) dia(s). Extração suspeita — nada foi alterado no Neon. "
                      f"(Se for intencional, rode com --completo.)")
                return False

    inicio_envio = time.time()
    try:
        if plano is None:
            print(f"🚀 [COMPLETO] Enviando/Atualizando {len(df)} registros no Neon...")
            enviar_dados_para_neon(df=df, nome_tabela=NOME_TABELA, coluna_chave=COLUNA_CHAVE)
            enviados = len(df)
        else:
            df_envio = plano["df_envio"]
            print(f"🚀 [INCREMENTAL] Janela: {plano['corte']:%d/%m/%y} → hoje "
                  f"({len(df_envio)} de {len(df)} linhas serão enviadas).")
            if plano["dias_faltantes"]:
                print(f"   ➕ Dias que o Neon não tinha e foram incluídos: {', '.join(plano['dias_faltantes'])}")
            enviar_dados_para_neon(
                df=df_envio,
                nome_tabela=NOME_TABELA,
                coluna_chave=COLUNA_CHAVE,
                datas_escopo_exclusao=plano["datas_escopo"],
                coluna_data=COLUNA_DATA,
            )
            enviados = len(df_envio)
            if plano["datas_purgar"]:
                apagadas = remover_por_datas(NOME_TABELA, plano["datas_purgar"], COLUNA_DATA)
                print(f"🗑️ Mês(es) anterior(es) removido(s) do Neon após o congelamento: "
                      f"{apagadas} linhas ({len(plano['datas_purgar'])} dias).")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar dados para o Neon: {e}")
        return False
    duracao_envio = time.time() - inicio_envio
    print(f"⏱️  Comunicação com o Neon: {duracao_envio:.1f}s")

    # Snapshot intradiário: sempre com o arquivo COMPLETO (mesmo comportamento
    # de antes). Nunca derruba o upload principal se falhar.
    if registrar_snapshot(df):
        print("📸 Snapshot intradiário (PU/Eficácia) registrado.")
    else:
        print("⚠️ Snapshot intradiário não registrado (ver aviso acima, se houver).")

    print(f"✅ Upload concluído em {time.time() - inicio_total:.1f}s "
          f"({enviados} registros enviados de {len(df)} no arquivo).")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Upload da base tratada para o Neon.")
    ap.add_argument("--completo", action="store_true",
                    help="reenvia o arquivo inteiro e apaga órfãs (comportamento antigo)")
    ap.add_argument("--verificar", action="store_true",
                    help="só compara os dias antigos do arquivo com o Neon (não grava)")
    ap.add_argument("--janela", type=int, default=JANELA_DIAS_PADRAO,
                    help=f"quantos dias (contando hoje) reenviar; padrão {JANELA_DIAS_PADRAO}")
    args = ap.parse_args()

    if args.verificar:
        sucesso = verificar_historico(args.janela)
    else:
        sucesso = executar_upload(completo=args.completo, janela_dias=args.janela)
    sys.exit(0 if sucesso else 1)
