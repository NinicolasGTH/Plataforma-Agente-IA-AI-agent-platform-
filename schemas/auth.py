from pydantic import BaseModel


class LoginRequest(BaseModel):
    nomeUsuario: str
    senha: str


class Token(BaseModel):
    acesso_token: str
    token_tipo: str = "bearer"

