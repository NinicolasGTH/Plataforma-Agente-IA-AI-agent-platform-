from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    nomeUsuario: str
    senha: str


class Token(BaseModel):
    acesso_token: str
    token_tipo: str = "bearer"
    
class RecuperarSenhaRequest(BaseModel):
    email: str

class RedefinirSenhaRequest(BaseModel):
    email: str
    token: str
    nova_senha: str = Field(..., min_length=6)
