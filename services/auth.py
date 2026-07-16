"""
Serviço de autenticação. Guarda usuários no Neon (Postgres) com senha
sempre hasheada (bcrypt) — nunca em texto puro.
"""
import bcrypt
from sqlalchemy import text
from services.database import obter_engine


def criar_tabela_usuarios():
    """Cria a tabela 'usuarios' no Neon, caso ainda não exista. Rode uma vez."""
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                login VARCHAR(50) UNIQUE NOT NULL,
                nome VARCHAR(120) NOT NULL,
                senha_hash TEXT NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))


def criar_usuario(login: str, nome: str, senha: str) -> bool:
    """
    Cria um novo usuário com a senha já hasheada.
    Retorna True se criou, False se o login já existir.
    """
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    engine = obter_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO usuarios (login, nome, senha_hash)
                    VALUES (:login, :nome, :senha_hash)
                """),
                {"login": login.strip().lower(), "nome": nome.strip(), "senha_hash": senha_hash},
            )
        return True
    except Exception as e:
        # Provável violação de UNIQUE (login já existe)
        print(f"Erro ao criar usuário: {e}")
        return False


def verificar_login(login: str, senha: str) -> dict | None:
    """
    Confere login/senha contra o banco.
    Retorna um dict com os dados do usuário se for válido, ou None se inválido.
    """
    engine = obter_engine()
    with engine.connect() as conn:
        resultado = conn.execute(
            text("""
                SELECT id, login, nome, senha_hash
                FROM usuarios
                WHERE login = :login AND ativo = TRUE
            """),
            {"login": login.strip().lower()},
        ).fetchone()

    if resultado is None:
        return None

    usuario_id, login_db, nome, senha_hash = resultado

    if bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8")):
        return {"id": usuario_id, "login": login_db, "nome": nome}

    return None


def alterar_senha(login: str, nova_senha: str) -> bool:
    """Atualiza a senha (já hasheada) de um usuário existente."""
    senha_hash = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    engine = obter_engine()
    with engine.begin() as conn:
        resultado = conn.execute(
            text("UPDATE usuarios SET senha_hash = :senha_hash WHERE login = :login"),
            {"senha_hash": senha_hash, "login": login.strip().lower()},
        )
    return resultado.rowcount > 0
