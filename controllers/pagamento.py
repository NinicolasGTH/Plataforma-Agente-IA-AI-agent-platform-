from fastapi import APIRouter, Depends, HTTPException, Request, status
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

router = APIRouter(prefix="/pagamento", tags=["Pagamento"])

#Funções auxiliares para validação de configuração do Stripe e evitar processamento duplicado de eventos (útil para webhooks)
def validar_config_stripe(para_webhook: bool = False) -> None:
    """Valida se as variáveis de ambiente do Stripe estão configuradas corretamente. Se para_webhook for True, valida apenas as variáveis necessárias para o webhook."""
    faltando = []
    if not stripe.api_key:
        faltando.append("STRIPE_SECRET_KEY")
    if not FRONTEND_URL and not para_webhook:
        faltando.append("FRONTEND_URL")
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
    return db.query(StripeEventoProcessado).filter(StripeEventoProcessado.evento_id == event_id).first() is not None

# Modelo para armazenar eventos do Stripe já processados (para evitar processamento duplicado)
def marcar_evento_processado(db: Session, event_id: str, event_type: str) -> None:
    """Marca um evento do Stripe como processado para evitar processamento duplicado (útil para webhooks)"""
    db.add(StripeEventoProcessado(evento_id=event_id, tipo=event_type))
    # db.commit() não é necessário o db.commit() aqui, pois a função que chama marcar_evento_processado já deve estar dentro de uma transação que será comitada no final do processamento do webhook.
    
    # O importante é garantir que marcar_evento_processado seja chamada apenas uma vez por evento, e que o evento_ja_processado seja verificado no início do processamento do webhook para evitar processar o mesmo evento mais de uma vez.
    
def buscar_usuario_por_subscription(db: Session, subscription_id: str) -> Usuario:
    """Busca um usuário no banco de dados pelo ID da assinatura do Stripe (útil para webhooks)"""
    return db.query(Usuario).filter(Usuario.stripe_subscription_id == subscription_id).first()

# ─────────────────────────────────────────
# CRIAR SESSÃO DE CHECKOUT
# ─────────────────────────────────────────

@router.post("/criar-checkout")
async def criar_checkout(
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
        sessao = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/pagamento/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/planos",
            metadata={"usuario_id": str(usuario.id)},
            customer_email=usuario.email
        )
        return {"url": sessao.url}
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar sessão de pagamento: {str(e)}"
        )
        
# ─────────────────────────────────────────
# WEBHOOK — STRIPE NOTIFICA O BACKEND
# ─────────────────────────────────────────

# O Stripe enviará uma notificação para este endpoint sempre que houver uma mudança no status da assinatura do usuário (ex: pagamento aprovado, falhou, cancelado). O backend processará essa notificação e atualizará o plano do usuário conforme necessário.
@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    validar_config_stripe(para_webhook=True) # True pois neste endpoint precisamos validar apenas as variáveis de ambiente do Stripe necessárias para processar o webhook (STRIPE_SECRET_KEY e STRIPE_WEBHOOK_SECRET)
    """Recebe eventos do Stripe e atualiza  o plano do usuário conforme o status da assinatura (ENDPOINT: /pagamento/webhook)"""
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Payload inválido")
    
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Assinatura inválida")        
   
    event_id = evento.get("id")
    event_type = evento.get("type")
    data = evento.get("data", {}).get("object", {})
    
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Evento Stripe inválido: ID ou tipo ausente"
        )
    
    if evento_ja_processado(db, event_id):
        logger.info(f"Evento Stripe {event_id} do tipo {event_type} já foi processado. Ignorando.")
        return {"status": "ok", "duplicado": True}
    
    # Processar apenas eventos relacionados a assinaturas
    
    try:
        if event_type == "checkout.session.completed":
            usuario_id = data.get("metadata", {}).get("usuario_id")
            if usuario_id:
                usuario = db.query(Usuario).filter(Usuario.id == int(usuario_id)).first()
                if usuario:
                    usuario.plano = "Pro"
                    usuario.status = "Ativo"
                    usuario.stripe_customer_id = data.get("customer")
                    usuario.stripe_subscription_id = data.get("subscription")
        
        elif event_type == "invoice.payment_succeeded":
            subscription_id = data.get("subscription")
            usuario = buscar_usuario_por_subscription(db, subscription_id)
            if usuario:
                usuario.plano = "Pro"
                usuario.status = "Ativo"
                
        elif event_type == "invoice.payment_failed":
            subscription_id = data.get("subscription")
            usuario = buscar_usuario_por_subscription(db, subscription_id)
            if usuario:
                usuario.status = "Inadimplente"
        
        elif event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            subscription_status = data.get("status")
            usuario = buscar_usuario_por_subscription(db, subscription_id)
            
            if usuario:
                if subscription_status in ["active", "trialing", "past_due"]:
                    usuario.plano = "Pro"
                    if subscription_status in ["active", "trialing"]:
                        usuario.status = "Ativo"
                    else:
                        usuario.status = "Inadimplente"
                elif subscription_status in ["canceled", "unpaid", "incomplete_expired"]:
                    usuario.plano = "Gratuito"
                    usuario.status = "Inativo"
                    usuario.stripe_subscription_id = None
        
        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            usuario = buscar_usuario_por_subscription(db, subscription_id)
            if usuario:
                usuario.plano = "Gratuito"
                usuario.status = "Inativo"
                usuario.stripe_subscription_id = None

        marcar_evento_processado(db, event_id, event_type)
    try:
        db.commit()
        
        logger.info("Evento processado: %s (%s)", event_id, event_type)
        return {"status": "ok", "duplicado": False}
    
    except Exception as e:
        db.rollback()
        logger.exception("Erro ao processar evento Stripe %s (%s): %s", event_id, event_type, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar evento Stripe: {str(e)}"
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
        