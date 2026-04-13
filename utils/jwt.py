from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Configurando JWT 

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY não configurada no ambiente")
ALGORITHM = "HS256"
ACESS_TOKEN_EXPIRE_MINUTES = 60*24*7 # 7 dias ao total.

def criar_acesso_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Cria token JWT com os dados do usuário

    Args: 
        data: Dados para incluir no token (ex: {"sub": "usuario@gmail.com"})
        expires_delta: Tempo de expiração customizado (opcional)

    Returns:
        Token JWT como string   
    """

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta

    else:
        expire = datetime.utcnow() + timedelta(minutes=ACESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def decodificar_token(token: str):
    """
    Decodifica e valida token JWT

    Args:
        token: Token JWT em string

    Returns:
        Dados contidos no token ou None se inválido
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None