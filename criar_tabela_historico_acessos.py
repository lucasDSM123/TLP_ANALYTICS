"""
Rode este script UMA VEZ (local ou no ambiente do deploy) para criar a
tabela 'historico_acessos' no Neon. Depois disso, todo login bem-sucedido
passa a gravar uma linha nessa tabela automaticamente (ver services/auth.py).

Uso:
    python criar_tabela_historico_acessos.py
"""
from services.auth import criar_tabela_historico_acessos

if __name__ == "__main__":
    print("Criando tabela 'historico_acessos' no Neon (se não existir)...")
    criar_tabela_historico_acessos()
    print("Pronto! A partir de agora, cada login bem-sucedido será registrado.")
