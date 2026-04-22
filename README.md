# Agente IA - Backend

API backend em FastAPI para autenticação, chat, conversas e assinatura Stripe.

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL (Neon)
- JWT (python-jose)
- Stripe (checkout + webhook)
- Rate limit com slowapi

## Funcionalidades

- Cadastro e login com JWT
- Confirmação de e-mail
- Recuperação e redefinição de senha
- Chat com histórico de conversas
- Plano Gratuito/Pro com Stripe
- Webhook Stripe com proteção de idempotência

## Executar localmente (sem Docker)

1. Criar e ativar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependências

```powershell
pip install -r requirements.txt
```

3. Criar `.env` com base no `.env.example`

4. Subir API

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

## Executar com Docker

```powershell
docker compose up -d --build
docker compose logs -f api
```

## Variáveis de ambiente

Use o arquivo `.env.example` como referência.

Principais variáveis:

- `DATABASE_URL`
- `SECRET_KEY`
- `ORIGENS_PERMITIDAS`
- `FRONTEND_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`
- `GROQ_API_KEY`

## Deploy (produção)

1. Fazer deploy do backend (Render/Railway)
2. Configurar variáveis de ambiente na plataforma
3. Fazer deploy do frontend (Vercel)
4. Ajustar `ORIGENS_PERMITIDAS` para domínio real do frontend
5. Configurar webhook Stripe apontando para:

```text
https://SEU_BACKEND/pagamento/webhook
```

## Go-live Stripe (ordem recomendada)

1. Subir produção com Stripe em modo teste
2. Validar fluxo completo em produção
3. Trocar para chaves live
4. Configurar webhook live
5. Fazer um smoke test de cobrança real

