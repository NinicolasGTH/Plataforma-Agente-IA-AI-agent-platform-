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

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
import os
import requests
import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application


# ─────────────────────────────────────────
# FERRAMENTAS
# ─────────────────────────────────────────

@tool
def calculator(expression: str) -> str:
    """
    Resolve expressões matemáticas e equações algébricas.
    Exemplos: '2 + 2', '3*x + 5 = 7', 'x**2 - 4 = 0', 'sqrt(16)', 'sin(pi/2)'
    """
    try:
        expression = expression.strip()

        if "=" in expression:
            lhs, rhs = expression.split("=", 1)
            lhs_expr = parse_expr(lhs.strip(), transformations=(standard_transformations + (implicit_multiplication_application,)))
            rhs_expr = parse_expr(rhs.strip(), transformations=(standard_transformations + (implicit_multiplication_application,)))
            equation = sympy.Eq(lhs_expr, rhs_expr)
            variaveis = list(equation.free_symbols)
            if not variaveis:
                return "Equação sem variáveis."
            solucoes = sympy.solve(equation, variaveis[0])
            return f"{variaveis[0]} = {solucoes}"

        transformations = standard_transformations + (implicit_multiplication_application,)
        expr = parse_expr(expression, transformations=transformations)
        resultado = sympy.simplify(expr)
        return str(resultado)

    except Exception as e:
        return f"Erro ao calcular: {e}"


@tool
def get_weather(city: str) -> str:
    """
    Retorna a previsão do tempo atual para uma cidade.
    Exemplo: 'São Paulo', 'London', 'New York'
    """
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return "Chave da API de clima não configurada."

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=pt_br"
        res = requests.get(url, timeout=5)
        data = res.json()

        if res.status_code != 200:
            return f"Cidade '{city}' não encontrada."

        descricao = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        sensacao = data["main"]["feels_like"]
        umidade = data["main"]["humidity"]
        vento = data["wind"]["speed"]

        return (
            f"Clima em {data['name']}, {data['sys']['country']}:\n"
            f"🌡️ Temperatura: {temp}°C (sensação térmica: {sensacao}°C)\n"
            f"🌤️ Condição: {descricao}\n"
            f"💧 Umidade: {umidade}%\n"
            f"💨 Vento: {vento} m/s"
        )
    except Exception as e:
        return f"Erro ao buscar clima: {e}"


@tool
def get_current_datetime(timezone: str = "America/Sao_Paulo") -> str:
    """
    Retorna a data e hora atual.
    Parâmetro timezone opcional, ex: 'America/Sao_Paulo', 'Europe/London', 'UTC'
    """
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        agora = datetime.now(tz)
        return agora.strftime(f"📅 %d/%m/%Y  🕐 %H:%M:%S ({timezone})")
    except Exception as e:
        return f"Erro ao obter data/hora: {e}"


# ─────────────────────────────────────────
# CONFIGURAÇÃO DO AGENTE
# ─────────────────────────────────────────

SYSTEM_PROMPT = SystemMessage(content="""Você é um assistente útil e inteligente. Responda sempre em português.

Você tem acesso APENAS às seguintes ferramentas:
- calculator: para cálculos matemáticos e equações algébricas
- get_weather: para consultar o clima atual de uma cidade
- get_current_datetime: para obter a data e hora atual

Regras importantes:
- Use SOMENTE as ferramentas listadas acima
- NUNCA tente usar brave_search, web_search ou qualquer outra ferramenta não listada
- Se não puder responder com as ferramentas disponíveis, diga isso claramente ao usuário
- Para perguntas sobre notícias ou eventos recentes, informe que não tem acesso a essa informação
""")

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
tools = [calculator, get_weather, get_current_datetime]
tools_map = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ─────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────

class MensagemRequest(BaseModel):
    mensagem: str
    id_conversa: Optional[int] = None


class MensagemResponse(BaseModel):
    id_conversa: int
    resposta: str
    ferramentas_usadas: Optional[List[str]] = None


# ─────────────────────────────────────────
# ROTA
# ─────────────────────────────────────────
# ROTA
# ─────────────────────────────────────────

@router.post("/enviar", response_model=MensagemResponse)
async def enviar_mensagem(
    request: MensagemRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    # Criar ou buscar conversa
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
        conversa = db.query(Conversa).filter(
            Conversa.id == request.id_conversa,
            Conversa.usuario_id == usuario.id
        ).first()
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

    try:
        print(f"[DEBUG] Chamando Groq com mensagem: {request.mensagem[:100]}...")
        response = llm_with_tools.invoke([SYSTEM_PROMPT, HumanMessage(content=request.mensagem)])
        print(f"[DEBUG] Resposta do Groq recebida. Tool calls: {bool(response.tool_calls)}")

        ferramentas_usadas = []
        messages = [SYSTEM_PROMPT, HumanMessage(content=request.mensagem), response]

        # Executar todas as ferramentas chamadas
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                print(f"[DEBUG] Tool call detectado: {tool_name}")

                tool_fn = tools_map.get(tool_name)
                if tool_fn:
                    tool_resultado = tool_fn.invoke(tool_call["args"])
                    ferramentas_usadas.append(tool_name)
                    print(f"[DEBUG] Resultado de {tool_name}: {str(tool_resultado)[:200]}")
                    messages.append(HumanMessage(content=f"Resultado de {tool_name}: {tool_resultado}"))
                else:
                    print(f"[DEBUG] Ferramenta desconhecida ignorada: {tool_name}")

            # Pedir resposta final ao agente com os resultados
            final_response = llm_with_tools.invoke(messages)
            resposta_final = final_response.content
            print(f"[DEBUG] Resposta final gerada: {resposta_final[:100]}...")
        else:
            resposta_final = response.content
            print(f"[DEBUG] Resposta direta (sem ferramentas): {resposta_final[:100]}...")

        # Salvar resposta do agente
        mensagem_agente = Mensagem(
            id_conversa=conversa.id,
            papel="assistant",
            conteudo=resposta_final,
            ferramentas=ferramentas_usadas if ferramentas_usadas else None
        )
        db.add(mensagem_agente)
        conversa.atualizado_em = datetime.now()
        db.commit()
        db.refresh(mensagem_agente)

        return MensagemResponse(
            id_conversa=conversa.id,
            resposta=resposta_final,
            ferramentas_usadas=ferramentas_usadas if ferramentas_usadas else None
        )

    except Exception as e:
        db.rollback()
        print(f"[ERRO] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

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