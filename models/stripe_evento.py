from sqlalchemy import Column, DateTime, Integer, String, func
from database import Base

class StripeEventoProcessado(Base):
    __tablename__ = "stripe_eventos_processados"
    
    id = Column(Integer, primary_key=True, index=True)
    evento_id = Column(String(255), unique=True, nullable=False, index=True)
    tipo = Column(String(120), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    