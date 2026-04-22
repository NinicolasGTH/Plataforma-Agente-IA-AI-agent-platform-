from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import event
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.stripe_evento import StripeEventoProcessado
from middleware.auth import obter_usuario_atual
import stripe
import os      
import logging


logger = logging.getLogger(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_ID = os.getenv("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")
FRONTEND_URL_MOBILE = os.getenv("FRONTEND_URL_MOBILE")

router = APIRouter(prefix="/pagamento", tags=["Pagamento"])

#Funções auxiliares para validação de configuração do Stripe e evitar processamento duplicado de eventos (útil para webhooks)
def validar_config_stripe(para_webhook: bool = False) -> None:
    """Valida se as variáveis de ambiente do Stripe estão configuradas corretamente. Se para_webhook for True, valida apenas as variáveis necessárias para o webhook."""
    faltando = []
    if not stripe.api_key:
        faltando.append("STRIPE_SECRET_KEY")
    if not FRONTEND_URL and not FRONTEND_URL_MOBILE and not para_webhook:
        faltando.append("FRONTEND_URL (ou FRONTEND_URL_MOBILE)")
    if not PRICE_ID and not para_webhook:
        faltando.append("STRIPE_PRICE_ID")
    if not WEBHOOK_SECRET and para_webhook:
        faltando.append("STRIPE_WEBHOOK_SECRET")
    if faltando:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuração do Stripe incompleta. Variáveis faltando: {', '.join(faltando)}"
        )
# Funções auxiliares para evitar processamento duplicado de eventos do Stripe (útil para webhooks)
def evento_ja_processado(db: Session, event_id: str) -> bool:
    """Verifica se um evento do stripe já foi processado para evitar processamento duplicado (útil para webhooks)"""
    # Aqui você pode implementar uma lógica para armazenar os IDs dos eventos processados, por exemplo, em um banco de dados ou cache. 
    return db.query(StripeEventoProcessado).filter(StripeEventoProcessado.event_id == event_id).first() is not None

# Modelo para armazenar eventos do Stripe já processados (para evitar processamento duplicado)
def marcar_evento_processado(db: Session, event_id: str, event_type: str) -> None:
    """Marca um evento do Stripe como processado para evitar processamento duplicado (útil para webhooks)"""
    db.add(StripeEventoProcessado(event_id=event_id, tipo=event_type))
    # db.commit() não é necessário o db.commit() aqui, pois a função que chama marcar_evento_processado já deve estar dentro de uma transação que será comitada no final do processamento do webhook.
    
    # O importante é garantir que marcar_evento_processado seja chamada apenas uma vez por evento, e que o evento_ja_processado seja verificado no início do processamento do webhook para evitar processar o mesmo evento mais de uma vez.
    
def buscar_usuario_por_subscription(db: Session, subscription_id: str) -> Usuario | None:
    """Busca um usuário no banco de dados pelo ID da assinatura do Stripe (útil para webhooks)"""
    return db.query(Usuario).filter(Usuario.stripe_subscription_id == subscription_id).first()


def obter_frontend_url(request: Request) -> str:
    """Escolhe a URL de frontend com base na origem da requisição, com fallback para variáveis de ambiente."""
    origin = (request.headers.get("origin") or "").rstrip("/")
    frontend_default = (FRONTEND_URL or "").rstrip("/")
    frontend_mobile = (FRONTEND_URL_MOBILE or "").rstrip("/")

    if origin and frontend_mobile and origin == frontend_mobile:
        return frontend_mobile
    if origin and frontend_default and origin == frontend_default:
        return frontend_default

    # Fallback útil para rede local quando o origin vem com IP privado.
    if origin.startswith("http://192.168.") and frontend_mobile:
        return frontend_mobile

    return frontend_default or frontend_mobile

# ─────────────────────────────────────────
# CRIAR SESSÃO DE CHECKOUT
# ─────────────────────────────────────────

@router.post("/criar-checkout")
async def criar_checkout(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Cria uma sessão de checkout do Stripe para o usuário autenticado (ENDPOINT: /pagamento/criar-checkout)"""
    validar_config_stripe(para_webhook=False) # False pois neste endpoint precisamos validar todas as variáveis de ambiente do Stripe, incluindo aquelas necessárias para criar a sessão de checkout (STRIPE_SECRET_KEY, STRIPE_PRICE_ID, FRONTEND_URL)
    if usuario.plano == "Pro":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já possui o plano Pro"
        )
    try:
        frontend_url = obter_frontend_url(request)
        sessao = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            success_url=f"{frontend_url}/pagamento/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/planos",
            metadata={"usuario_id": str(usuario.id)},
            customer_email=usuario.email
        )
        return {"url": sessao.url}
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar sessão de checkout"
        )
        
# ... (suas importações continuam iguais)

# ─────────────────────────────────────────
# WEBHOOK — STRIPE NOTIFICA O BACKEND
# ─────────────────────────────────────────

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    validar_config_stripe(para_webhook=True)
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cabeçalho de assinatura Stripe ausente"
        )
    
    try:
        evento = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assinatura inválida")        
   
    # --- CORREÇÃO 1: ACESSO POR ATRIBUTO (FIM DO ERRO ATTRIBUTERROR) ---
    event_id = evento.id
    event_type = evento.type
    data = evento.data.object  # No objeto Stripe, os dados ficam em .data.object
    
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Evento Stripe inválido: ID ou tipo ausente"
        )
    
    # --- CORREÇÃO 2: IDEMPOTÊNCIA (USANDO event_id QUE VOCÊ MUDOU NO MODEL) ---
    if evento_ja_processado(db, event_id):
        logger.info(f"Evento Stripe {event_id} já foi processado. Ignorando.")
        return {"status": "ok", "duplicado": True}
    
    try:
        if event_type == "checkout.session.completed":
            # Nota: 'data' (evento.data.object) funciona como dicionário, então .get() aqui está OK!
            usuario_id = data.get("metadata", {}).get("usuario_id")
            if usuario_id and str(usuario_id).isdigit():
                usuario = db.query(Usuario).filter(Usuario.id == int(usuario_id)).first()
                if usuario:
                    usuario.plano = "Pro"
                    usuario.status = "Ativo"
                    usuario.stripe_customer_id = data.get("customer")
                    usuario.stripe_subscription_id = data.get("subscription")
        
        elif event_type == "invoice.payment_succeeded":
            subscription_id = data.get("subscription")
            if subscription_id:
                usuario = buscar_usuario_por_subscription(db, subscription_id)
                if usuario:
                    usuario.plano = "Pro"
                    usuario.status = "Ativo"
                
        elif event_type == "invoice.payment_failed":
            subscription_id = data.get("subscription")
            if subscription_id:
                usuario = buscar_usuario_por_subscription(db, subscription_id)
                if usuario:
                    usuario.status = "Inadimplente"
        
        elif event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            subscription_status = data.get("status")
            if subscription_id:
                usuario = buscar_usuario_por_subscription(db, subscription_id)
            
                if usuario:
                    if subscription_status in ["active", "trialing", "past_due"]:
                        usuario.plano = "Pro"
                        usuario.status = "Ativo" if subscription_status in ["active", "trialing"] else "Inadimplente"
                    elif subscription_status in ["canceled", "unpaid", "incomplete_expired"]:
                        usuario.plano = "Gratuito"
                        usuario.status = "Inativo"
                        usuario.stripe_subscription_id = None
        
        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            if subscription_id:
                usuario = buscar_usuario_por_subscription(db, subscription_id)
                if usuario:
                    usuario.plano = "Gratuito"
                    usuario.status = "Inativo"
                    usuario.stripe_subscription_id = None

        # --- CORREÇÃO 3: SALVAR O SUCESSO ---
        marcar_evento_processado(db, event_id, event_type)
        db.commit()
        
        logger.info("Evento processado com sucesso: %s (%s)", event_id, event_type)
        return {"status": "ok", "duplicado": False}
    
    except Exception as e:
        db.rollback()
        logger.exception("Erro ao processar evento Stripe %s: %s", event_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar o evento."
        )  
# ─────────────────────────────────────────
# STATUS DO PLANO
# ─────────────────────────────────────────
    
@router.get("/status")
async def status_plano(usuario: Usuario= Depends(obter_usuario_atual)):
    """Retorna o plano atual do usuário"""
    return{
        "plano": usuario.plano,
        "mensagens_hoje": usuario.mensagens_hoje if usuario.plano == "Gratuito" else None,
        "limite_diario": 20 if usuario.plano == "Gratuito" else None,
    }
        