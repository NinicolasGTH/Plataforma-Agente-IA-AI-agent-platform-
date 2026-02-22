from pydantic import BaseModel, EmailStr
from datetime import datetime


class CriarUser(BaseModel):
    email: EmailStr
    nomeUsuario: str
    senha: str


class RespostaUsuario(BaseModel):
    id: int
    email: str
    nomeUsuario: str
    data_criacao: datetime

    class Config:
        from_attributes = True


class UsuarioDB(BaseModel):
    id: int
    email: str
    nomeUsuario: str
    senha_hashed: str
    data_criacao: datetime

    class Config:
        from_attributes = True
