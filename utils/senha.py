from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def hash_senha(senha: str):
    """
    Transforma a senha em texto puro para hash irreversível usando bcrypt
    

    Args:
        senha: Senha em texto puro(ex:"marco123")

    Returns:
        Hash da senha (ex:"$2b$12$kX9ZvN...")
    """
    return pwd_context.hash(senha)

def verificar_senha(senha_texto:str, senha_hash:str) -> bool:
    """
    Verifica se a senha digitada corresponde ao hash salvo

    Args:
        senha_texto: Senha em texto puro (ex:"marco123")
        senha_hash: Hash da senha salva no banco (ex:"$2b$12$kX9ZvN...")

        Returns:
            True se a senha for correta, False caso contrário
    """
    return pwd_context.verify(senha_texto, senha_hash)
