"""
Congela o fechamento DIÁRIO de um mês fechado (por Estado, Cluster e
Supervisor) em services/historico_diario/AAAA-MM.json — é esse arquivo que a
aba "Acumulado Mês" lê para mostrar o mesmo dia do mês anterior ao lado do
dia atual, mesmo depois que o mês anterior sai do Neon.

Também imprime o bloco de totais por Supervisor (para colar em
services/historico_mensal.py, como foi feito com Setembro/2026).

Uso (na pasta do projeto):
    python congelar_mes.py caminho/da/base.xlsx 2026 9

A base precisa ter o mês inteiro (coluna Data no formato dd/mm/aa).
Linhas de outros meses presentes no arquivo são ignoradas.
"""
import json
import sys
from pathlib import Path

import pandas as pd

from services.grupos import serie_diaria_por_grupo, resumo_mes_por_grupo

PASTA_SAIDA = Path(__file__).parent / "services" / "historico_diario"
DIMENSOES = ("Estado", "Cluster", "Supervisor")


def _filtrar_mes(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    datas = pd.to_datetime(df["Data"], format="%d/%m/%y", errors="coerce")
    return df[(datas.dt.year == ano) & (datas.dt.month == mes)]


def _diario_para_dict(diario: pd.DataFrame, coluna: str) -> dict:
    saida = {}
    for grupo, sub in diario.groupby(coluna):
        saida[str(grupo)] = {
            str(linha["Data"].day): {
                "concluida": int(linha["Concluída"]),
                "improdutiva": int(linha["Improdutiva"]),
                "tecnicos": int(linha["Técnicos"]),
                "caixa_total": round(float(linha["Caixa Total"]), 2),
                "atribuicao": round(float(linha["Atribuição"]), 4),
                "pu": round(float(linha["PU"]), 4),
                "eficacia": round(float(linha["Eficácia"]), 6),
            }
            for _, linha in sub.iterrows()
        }
    return saida


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    caminho, ano, mes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

    base = pd.read_excel(caminho)
    mes_df = _filtrar_mes(base, ano, mes)
    if mes_df.empty:
        sys.exit(f"Nenhuma linha de {mes:02d}/{ano} encontrada em {caminho}.")

    resultado = {}
    for coluna in DIMENSOES:
        if coluna not in mes_df.columns:
            continue
        diario = serie_diaria_por_grupo(mes_df, coluna)
        if not diario.empty:
            resultado[coluna] = _diario_para_dict(diario, coluna)

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    destino = PASTA_SAIDA / f"{ano}-{mes:02d}.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    dias = sorted({int(d) for g in resultado.get("Estado", {}).values() for d in g})
    print(f"OK: {destino} — {len(mes_df)} linhas, dias {dias[0]}–{dias[-1]}, "
          f"{ {c: len(v) for c, v in resultado.items()} } grupos")

    # Bloco de totais por Supervisor (para colar em historico_mensal.py)
    resumo = resumo_mes_por_grupo(mes_df, "Supervisor")
    if not resumo.empty:
        print(f"\n_{['', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'][mes]}"
              f"_{ano}_SUPERVISOR = {{")
        for _, r in resumo.iterrows():
            if r["Supervisor"] == "Total":
                continue
            print(f'    "{r["Supervisor"]}": dict(eficacia={round(float(r["Eficácia"]), 4)}, '
                  f'concluida={int(r["Concluída"])}, improdutiva={int(r["Improdutiva"])}, '
                  f'tecnicos={int(r["Técnicos"])}, atribuicao={round(float(r["Atribuição"]), 2):.2f}, '
                  f'pu={round(float(r["PU"]), 2):.2f}),')
        print("}")


if __name__ == "__main__":
    main()
