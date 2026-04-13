import os
import secrets
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def gerar_token_confirmacao() -> str:
    """Gera um token seguro para confirmação e redefinição de senha"""
    return secrets.token_urlsafe(32)


def _carregar_template(nome_template: str, dados: dict) -> str:
    caminho = os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        nome_template
    )
    with open(caminho, "r", encoding="utf-8") as f:
        html = f.read()
    for chave, valor in dados.items():
        html = html.replace(f"{{{{{chave}}}}}", str(valor))
    return html


def _enviar(destinatario: str, assunto: str, html: str):
    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "sender": {"name": "Agente IA", "email": EMAIL_REMETENTE},
            "to": [{"email": destinatario}],
            "subject": assunto,
            "htmlContent": html,
        },
        timeout=10,
    )
    if response.status_code not in (200, 201, 202):
        raise Exception(f"Brevo erro {response.status_code}: {response.text}")


async def enviar_email_confirmacao(destinatario: str, token: str, nome: str = None) -> bool:
    """Envia email de confirmação de cadastro via Brevo"""
    try:
        link = f"{FRONTEND_URL}/confirmar-email?token={token}"
        html = _carregar_template("email_verificacao.html", {
            "nome": nome or destinatario,
            "link_verificacao": link
        })
        _enviar(destinatario, "Confirme seu e-mail — Agente IA", html)
        return True
    except Exception as e:
        print(f"[EMAIL] Erro ao enviar confirmação para {destinatario}: {e}")
        return False


async def enviar_email_recuperacao(destinatario: str, token: str, nome: str = None) -> bool:
    """Envia email de redefinição de senha via Brevo"""
    try:
        link = f"{FRONTEND_URL}/redefinir-senha?token={token}"
        html = _carregar_template("redefinicao_senha.html", {
            "nome": nome or destinatario,
            "link_redefinicao": link
        })
        _enviar(destinatario, "Redefinição de senha — Agente IA", html)
        return True
    except Exception as e:
        print(f"[EMAIL] Erro ao enviar redefinição para {destinatario}: {e}")
        return False