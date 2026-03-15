import bcrypt


def hash_senha(senha: str) -> str:
    """
    Transforma a senha em texto puro para hash irreversível usando bcrypt

    Args:
        senha: Senha em texto puro (ex: "marco123")

    Returns:
        Hash da senha (ex: "$2b$12$kX9ZvN...")
    """
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    """
    Verifica se a senha digitada corresponde ao hash salvo

    Args:
        senha_texto: Senha em texto puro (ex: "marco123")
        senha_hash: Hash da senha salva no banco (ex: "$2b$12$kX9ZvN...")

    Returns:
        True se a senha for correta, False caso contrário
    """
    return bcrypt.checkpw(senha_texto.encode("utf-8"), senha_hash.encode("utf-8"))