from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from utils.jwt import decodificar_token


seguranca = HTTPBearer()


async def obter_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(seguranca),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Middleware que valida o JWT e retorna o usuário logado.
    
    Args:
        credentials: Credenciais Bearer extraídas do header Authorization
        db: Sessão do banco de dados
        
    Returns:
        Usuario: objeto do usuário autenticado
        
    Raises:
        HTTPException: se o token for inválido ou o usuário não existir
    """
    # Extrair token das credenciais
    token = credentials.credentials
    
    # Decodificar token
    payload = decodificar_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extrair nome de usuário do payload
    nomeUsuario = payload.get("sub")
    if not nomeUsuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Buscar usuário no banco
    usuario = db.query(Usuario).filter(Usuario.nomeUsuario == nomeUsuario).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )
    
    # Verificar se email foi confirmado
    if not usuario.email_confirmado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email não confirmado. Verifique seu email."
        )
    
    return usuario
