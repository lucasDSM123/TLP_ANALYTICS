"""
Rode este script UMA VEZ para:
1. Criar a tabela 'usuarios' no Neon (se ainda não existir)
2. Cadastrar seu primeiro usuário (admin)

Depois disso, se quiser criar mais usuários, pode rodar de novo
(a criação da tabela é segura de repetir) ou fazer uma tela de
cadastro dentro do próprio app — me avisa se quiser isso.
"""
import getpass
from services.auth import criar_tabela_usuarios, criar_usuario

if __name__ == "__main__":
    print("Criando tabela 'usuarios' no Neon (se não existir)...")
    criar_tabela_usuarios()
    print("Tabela pronta.\n")

    login = input("Login (ex: lucas): ").strip()
    nome = input("Nome completo: ").strip()
    senha = getpass.getpass("Senha: ")
    senha_confirma = getpass.getpass("Confirme a senha: ")

    if senha != senha_confirma:
        print("\n[ERRO] As senhas não coincidem. Rode o script de novo.")
    elif len(senha) < 6:
        print("\n[ERRO] Use uma senha com pelo menos 6 caracteres.")
    else:
        sucesso = criar_usuario(login, nome, senha)
        if sucesso:
            print(f"\nUsuário '{login}' criado com sucesso!")
        else:
            print(f"\n[ERRO] Não foi possível criar o usuário (login '{login}' já existe?).")
