from pydantic import BaseModel
from datetime import datetime


class CriarConversa(BaseModel):
    titulo: str = "Nova Conversa"


class ConversaResponse(BaseModel):
    id: int
    usuario_id: int
    titulo: str
    data_criacao: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class ConversaDB(BaseModel):
    id: int
    usuario_id: int
    titulo: str
    data_criacao: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True

