from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    nomeUsuario = Column(String, unique=True, index=True)
    senha_hashed = Column(String)
    data_criacao = Column(DateTime, default=datetime.now)
    email_confirmado = Column(Boolean, default=False)
    token_confirmacao = Column(String, nullable=True)
    token_redefinicao = Column(String, nullable=True)
    token_redefinicao_expira = Column(DateTime, nullable=True)
    email_confirmacao_enviado = Column(Boolean, default=False)
    status = Column(String, default="Pendente")  # "Pendente", "Ativo", "Inativo"

    conversas = relationship("Conversa", back_populates="usuario")