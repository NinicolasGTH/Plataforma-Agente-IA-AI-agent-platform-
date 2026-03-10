import secrets
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configurações de email
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@example.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def gerar_token_confirmacao() -> str:
    """Gera um token seguro para confirmação de email"""
    return secrets.token_urlsafe(32)


async def enviar_email_confirmacao(destinatario: str, token: str) -> bool:
    """
    Envia email de confirmação para o novo usuário.
    
    Por enquanto apenas retorna True (mock).
    Quando tiver RESEND_API_KEY configurado, descomentar o código real.
    """
    link_confirmacao = f"{FRONTEND_URL}/confirmar-email?token={token}"
    
    # Mock - sempre retorna sucesso
    print(f"[EMAIL MOCK] Link de confirmação: {link_confirmacao}")
    return True

async def enviar_email_recuperacao(destinatario: str, token: str) -> bool:
    """
    Envia email de recuperação de senha para o usuário.
    Por enquanto apenas retorna True (mock).
    Quando tiver RESEND_API_KEY configurado, descomentar o código real. 
    """
    link_recuperacao = f"{FRONTEND_URL}/redefinir-senha?token={token}&email={destinatario}"
    
    # Mock - sempre retorna sucesso
    print(f"[EMAIL MOCK] Link de recuperação: {link_recuperacao}")
    return True

   
   
   
   
   
   
   
   
   
    # Código real do Resend (descomentar quando configurar):
    # import resend
    # resend.api_key = os.getenv("RESEND_API_KEY")
    # try:
    #     resend.Emails.send({
    #         "from": EMAIL_FROM,
    #         "to": [destinatario],
    #         "subject": "Confirme seu email",
    #         "html": f'<a href="{link_confirmacao}">Confirmar Email</a>'
    #     })
    #     return True
    # except Exception as e:
    #     print(f"Erro ao enviar email: {e}")
    #     return False
