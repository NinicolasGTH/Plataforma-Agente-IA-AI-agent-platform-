from fastapi import APIRouter, Depends, HTTPException, status
from schemas.conversa import ConversaResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from models.usuario import Usuario
from models.conversa import Conversa
from models.mensagem import Mensagem
from middleware.auth import obter_usuario_atual
from schemas.conversa import ConversaResponse
from pydantic import BaseModel




router = APIRouter(prefix="/conversas", tags=["Conversas"])

# Schemas para respostas detalhadas

class MensagemDetalhes(BaseModel):
    id: int
    papel: str
    conteudo: str
    criado_em: datetime

    class Config:
        from_attributes = True # Permite a conversão de Model -> Schema

class ConversaDetalhada(BaseModel):
    id: int
    titulo: str
    data_criacao: datetime
    atualizado_em: datetime
    mensagens: List[MensagemDetalhes]

    class Config:
        from_attributes = True # Permite a conversão de Model -> Schema²


@router.get("/", response_model=List[ConversaResponse]) # Listagem de conversas
async def listar_conversas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """
   lista todas as conversas do usuário autenticado ordenadas por data de criação (mais recentes primeiro)
    """

    conversas = db.query(Conversa).filter(Conversa.usuario_id == usuario.id).order_by(Conversa.atualizado_em.desc()).all()

    return conversas

@router.get("/{conversa_id}", response_model=ConversaDetalhada) # Detalhes de uma conversa específica
async def buscar_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
    ):
    """
    Busca os detalhes de uma conversa específica, incluindo todas as mensagens associadas e verifica se a conversa pertence ao usuário autenticado
    """

    conversa = db.query(Conversa).filter(Conversa.id == conversa_id, Conversa.usuario_id == usuario.id).first() # Garante que é do usuário, a função first retorna o primeiro resultado ou None se não encontrar
    if not conversa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")

    # Buscar mensagens ordenadas por data de criação                   

    mensagens = db.query(Mensagem).filter(Mensagem.id_conversa == conversa_id).order_by(Mensagem.criado_em.asc()).all()

    # Montar resposta

    return ConversaDetalhada(
        id = conversa.id,
        titulo = conversa.titulo,
        data_criacao = conversa.data_criacao,
        atualizado_em = conversa.atualizado_em,
        mensagens=mensagens
    )

router.delete("/{conversa_id}", status_code=status.HTTP_204_NO_CONTENT) # rota de deleção de conversa
async def deletar_conversa(
    conversa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """
    Deleta uma conversa específica e todas as mensagens associadas. Verifica se a conversa pertence ao usuario autenticado.
    """ 
    conversa = db.query(Conversa).filter(Conversa.id == conversa_id, Conversa.usuario_id == usuario.id).first()
    if not conversa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não econtrada")
    
    # Deletar todas as mensagens primeiro

    db.query(Mensagem).filter(Mensagem.id_conversa == conversa_id).delete()

    db.delete(conversa) # Deleta a conversa no banco de dados
    db.commit() # Confirma a deleção no banco de dados

    return None # Retorna resposta vazia com status 204 No Content