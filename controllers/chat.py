from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.usuario import Usuario
from models.conversa import Conversa
from models.mensagem import Mensagem
from middleware.auth import obter_usuario_atual

# importar o agente do main.py (vamos mover posteriormente para um módulo separado)

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
import os

# Configurar agent

@tool
def calculator(expression: str) -> str:
    """calculadora para expressões matemáticas"""
    try:
        return str(eval(expression))
    except Exception as e:
        return f'erro: {e}'
    
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
tools = [calculator]
llm_with_tools = llm.bind_tools(tools)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Schemas
class MensagemRequest(BaseModel):
    mensagem: str
    id_conversa: Optional[int] = None # para criar nova conversa se não for fornecido

class MensagemResponse(BaseModel):
    id_conversa: int
    resposta: str
    ferramentas_usadas: Optional[List[str]] = None # para indicar quais ferramentas foram usadas na resposta

@router.post("/enviar", response_model=MensagemResponse)
async def enviar_mensagem(
    request: MensagemRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """
    Envia uma mensagem para o agente e retorna a resposta.
    Args:
        request: Mensagem do usuario e id_conversa (opcional)
        db: Sessão do banco de dados
        usuario: Usuario autenticado (via JWT)
    Returns:
        Resposta do agente com ferramentas utilizadas (se houver)
    
    
    
    
    """

    # Se não existir conversa

    if not request.id_conversa:
        nova_conversa = Conversa(
            usuario_id=usuario.id,
            titulo=request.mensagem[:50]
        )

        db.add(nova_conversa)
        db.commit()
        db.refresh(nova_conversa)
        conversa = nova_conversa
    else:
        # Buscar conversa que já existe e verificar se pertence ao usuário
        conversa = db.query(Conversa).filter(Conversa.id == request.id_conversa, Conversa.usuario_id == usuario.id).first() # Garante que é do usuário
        if not conversa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
    # Salvar mensagem do usuário

    mensagem_user = Mensagem(
        id_conversa=conversa.id,
        papel="user",
        conteudo=request.mensagem
    )
    db.add(mensagem_user)
    db.commit()

    # chamar o agente com a mensagem

    try:
        print(f"[DEBUG] Chamando Groq com mensagem: {request.mensagem[:100]}...")
        response = llm_with_tools.invoke([HumanMessage(content=request.mensagem)])
        print(f"[DEBUG] Resposta do Groq recebida. Tool calls: {bool(response.tool_calls)}")

        ferramentas_usadas = []
        resposta_final = ""

        #verifica se usou ferramentas

        if response.tool_calls:
            print(f"[DEBUG] Tool call detectado: {response.tool_calls[0]['name']}")
            # Executar a ferramenta

            tool_chamada = response.tool_calls[0] # Considerando apenas a primeira chamada de ferramenta
            tool_resultado = calculator.invoke(tool_chamada['args'])
            ferramentas_usadas.append("calculator")
            print(f"[DEBUG] Resultado da ferramenta: {tool_resultado}")

            # pedir pro agente gerar a resposta

            final_response = llm_with_tools.invoke([
                HumanMessage(content=request.mensagem),
                response,
                HumanMessage(content=f"Resultado: {tool_resultado}")
            ])

            resposta_final = final_response.content
            print(f"[DEBUG] Resposta final gerada: {resposta_final[:100]}...")

        else:
            # Resposta direta sem usar qualquer ferramenta

            resposta_final = response.content
            print(f"[DEBUG] Resposta direta (sem ferramentas): {resposta_final[:100]}...")

        # Salvar resposta do agente no banco

        mensagem_agente = Mensagem(
            id_conversa=conversa.id,
            papel="assistant",
            conteudo=resposta_final,
            ferramentas=ferramentas_usadas if ferramentas_usadas else None
        )
        db.add(mensagem_agente)


        conversa.atualizado_em=datetime.now() # Atualiza timestamp da conversa
        
        db.commit()
        db.refresh(mensagem_agente)

        return MensagemResponse(
            id_conversa=conversa.id,
            resposta=resposta_final,
            ferramentas_usadas=ferramentas_usadas if ferramentas_usadas else None
        )
    
    except Exception as e:
        db.rollback()
        print(f"[ERRO] Erro ao processar mensagem: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Tratamento específico para rate limit do Groq
        error_message = str(e).lower()
        if "rate limit" in error_message or "429" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Limite de requisições do Groq atingido. Aguarde alguns minutos e tente novamente."
            )
        elif "timeout" in error_message:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timeout ao chamar a API do Groq. Tente novamente."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )
