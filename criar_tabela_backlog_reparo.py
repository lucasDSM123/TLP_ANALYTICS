"""
Rode este script UMA VEZ para criar as tabelas 'backlog_reparo_atual' e
'backlog_reparo_historico' no Neon (a definição está em sql/backlog_reparo.sql).

Também dá para colar o conteúdo desse .sql direto no "SQL Editor" do console
do Neon — o resultado é o mesmo. É seguro rodar mais de uma vez.

Uso:
    python criar_tabela_backlog_reparo.py
"""
from pathlib import Path

from sqlalchemy import text

from services.database import obter_engine

ARQUIVO_SQL = Path(__file__).parent / "sql" / "backlog_reparo.sql"


def _comandos(sql: str) -> list[str]:
    """Divide o arquivo em comandos (separados por ';'), ignorando comentários."""
    linhas = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    return [c.strip() for c in "\n".join(linhas).split(";") if c.strip()]


def criar_tabelas() -> None:
    comandos = _comandos(ARQUIVO_SQL.read_text(encoding="utf-8"))
    engine = obter_engine()
    with engine.begin() as conn:
        for comando in comandos:
            conn.execute(text(comando))
    print(f"✅ {len(comandos)} comandos executados (tabelas e índices garantidos).")


if __name__ == "__main__":
    print("Criando tabelas do Backlog Reparo no Neon (se não existirem)...")
    criar_tabelas()
    print("Pronto! Agora rode: python upload_backlog_reparo.py")
