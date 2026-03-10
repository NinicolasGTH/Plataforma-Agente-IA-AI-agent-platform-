from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from schemas.usuario import CriarUser, RespostaUsuario
from schemas.auth import LoginRequest, RedefinirSenhaRequest,RecuperarSenhaRequest,Token
from utils.senha import hash_senha, verificar_senha
from utils.jwt import criar_acesso_token
from utils.email import gerar_token_confirmacao, enviar_email_confirmacao, enviar_email_recuperacao
from middleware.auth import obter_usuario_atual

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/register", response_model=RespostaUsuario, status_code=status.HTTP_201_CREATED)
async def registar(user_data: CriarUser, db: Session = Depends(get_db)):
    """
    Registra um novo usuario e envia email de confirmação (ENDPOINT: /auth/register)

    Args:
        user_data: Dados do usuário para registro (email, nomeUsuario, senha)
        db: Sessão do banco de dados
    Returns:
        RespostaUsuario: Dados do usuario registrado (id, email, nomeUsuario)

    """

# Verifica se o email já existe
    usuario_existente = db.query(Usuario).filter(Usuario.email == user_data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )

    # Verifica se o nome de usuário já existe
    usuario_existe = db.query(Usuario).filter(Usuario.nomeUsuario == user_data.nomeUsuario).first()
    if usuario_existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nome de usuário já registrado"
        )

    # Criação do usuário com senha hasheada e token de confirmação

    senha_hashed = hash_senha(user_data.senha)

    # Gera token de confirmação

    token_confirmacao = gerar_token_confirmacao()

    # Criação de usuário

    novo_usuario = Usuario(
        email=user_data.email,
        nomeUsuario=user_data.nomeUsuario,
        senha_hashed=senha_hashed,
        email_confirmado=False,
        token_confirmacao=token_confirmacao
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

# Enviar email de confirmação

    await enviar_email_confirmacao(
        destinatario=novo_usuario.email,
        token=token_confirmacao
    )   
    return novo_usuario

@router.get("/confirmar-email")
async def confirmar_email(token: str, db: Session = Depends(get_db)):
    """
    Confirma email do usuário através do Token
    Args:
        token: Token de confirmação recebido no email
        db: Sessão do banco de dados

    Returns:
        Mensagem de sucesso ou erro
    """

# Buscar usuário pelo token

    usuario = db.query(Usuario).filter(Usuario.token_confirmacao == token).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido"
    )

# Confirma email

    usuario.email_confirmado = True
    usuario.token_confirmacao = None
    db.commit()

    return {"message": "Email confirmado com sucesso! Agora você pode fazer login."}

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Realiza o login do usuário
    
    Args:
        login_data: Dados do usuário para login (email, senha)
        db: Sessão do banco de dados
    
    Returns:
        RespostaUsuario com dados do usuário criado
    """
    # Verifica se o email existe
    
    usuario = db.query(Usuario).filter(Usuario.nomeUsuario == login_data.nomeUsuario).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário não registrado"
        )

    # Verifica se a senha está correta
    if not verificar_senha(login_data.senha, usuario.senha_hashed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha incorreta"
        )

    # Verifica se o email foi confirmado
    if not usuario.email_confirmado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email não confirmado"
        )

    # Cria token de acesso
    token_acesso = criar_acesso_token({"sub": usuario.nomeUsuario})

    return {"acesso_token": token_acesso, "token_tipo": "bearer"}


# Rota para enviar email de recuperação de senha
@router.post("/recuperar-senha")
async def recuperar_senha(dados: RecuperarSenhaRequest, db: Session = Depends(get_db)):
    """
    Envia um email para o usuário com um link para redefinir a senha
    Args:
        dados: Dados do usuário para recuperação de senha (email)
        db: Sessão do banco de dados
    Returns:
        Mensagem de sucesso ou erro
    """
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario:
        return {"message": "Se o email estiver registrado, um email de recuperação de senha será enviado!"}
    # Gera token de recuperação de senha
    token_recuperacao = gerar_token_confirmacao()
    usuario.token_confirmacao = token_recuperacao
    db.commit()
    # Envia email de recuperação de senha
    await enviar_email_recuperacao(
        destinatario=usuario.email,
        token=token_recuperacao
    )
    return {"message": "Email de recuperação de senha enviado! Verifique sua caixa de entrada."}

# Rota para realmente redefinir a senha usando o token
@router.post("/redefinir-senha")
async def redefinir_senha(redefinir_data: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    """
    Redefine a senha do usuário usando o token de recuperação
    Args:
        redefinir_data: Dados para redefinir a senha (email, token, nova_senha)
        db: Sessão do banco de dados
    Returns:
        Mensagem de sucesso ou erro
    """
    
    usuario = db.query(Usuario).filter(Usuario.email == redefinir_data.email).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email não registrado"
        )

    if usuario.token_confirmacao != redefinir_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido"
        )

    # Redefine a senha
    usuario.senha_hashed = hash_senha(redefinir_data.nova_senha)
    usuario.token_confirmacao = None  # Invalida o token após uso
    db.commit()

    return {"message": "Senha redefinida com sucesso! Agora você pode fazer login com a nova senha."}
        
    
    
    