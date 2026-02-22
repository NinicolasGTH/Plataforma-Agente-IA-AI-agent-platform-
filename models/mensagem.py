from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Mensagem(Base):
    __tablename__ = "mensagens"
    
    id = Column(Integer, primary_key=True, index=True)
    id_conversa = Column(Integer, ForeignKey("conversas.id"))
    papel = Column(String)
    conteudo = Column(String)
    ferramentas = Column(JSON, nullable=True)
    criado_em = Column(DateTime, default=datetime.now)
    
    conversa = relationship("Conversa", back_populates="mensagens")
