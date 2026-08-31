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


def criar_tabela_historico_acessos():
    """Cria a tabela 'historico_acessos' no Neon, caso ainda não exista. Rode uma vez.

    Cada login bem-sucedido gera uma linha aqui, permitindo consultar depois
    quem acessa o site e com que frequência (não é sobrescrito — é um histórico).
    """
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS historico_acessos (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                login VARCHAR(50) NOT NULL,
                acessado_em TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_historico_acessos_usuario_id
                ON historico_acessos (usuario_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_historico_acessos_acessado_em
                ON historico_acessos (acessado_em);
        """))


def registrar_acesso(usuario_id: int, login: str):
    """Grava uma linha no histórico de acessos. Chamado a cada login bem-sucedido."""
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO historico_acessos (usuario_id, login)
                VALUES (:usuario_id, :login)
            """),
            {"usuario_id": usuario_id, "login": login},
        )


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
        try:
            registrar_acesso(usuario_id, login_db)
        except Exception as e:
            # Nunca deixa uma falha no registro de acesso impedir o login em si
            print(f"Aviso: não foi possível registrar o acesso: {e}")
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