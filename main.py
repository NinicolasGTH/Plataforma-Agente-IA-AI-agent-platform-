from fastapi import FastAPI
from dotenv import load_dotenv
from database import Base, engine
from controllers.auth import router as auth_router
from controllers.chat import router as chat_router
from controllers.conversas import router as conversas_router
from controllers.pagamento import router as pagamento_router
from fastapi.middleware.cors import CORSMiddleware
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# A chave da api vem do arquivo .env

# Aplicativo FastAPI
app = FastAPI(title="Meu Projeto com Strands e Groq", version="1.0.0")


origens_permitidas = os.getenv("ORIGENS_PERMITIDAS", "*").split(",")  # Permitir origens definidas no .env ou todas as origens

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    allow_credentials=True, # Permitir envio de cookies e credenciais
    allow_methods=["*"],  # Permitir todos os métodos HTTP
    allow_headers=["*"],  # Permitir todos os headers
    # Alterar a permissão quando em produção para restringir as origens, métodos e headers conforme necessário
)

@app.on_event("startup")
def criar_tabelas():
    """
    Cria as tabelas no banco de dados ao iniciar o aplicativo
    """
    Base.metadata.create_all(bind=engine)
print("\n API rodando em http://localhost:8000 e documentação em http://localhost:8000/docs. Banco de dados iniciado com sucesso. \n")

# incluir rotas

app.include_router(auth_router) # é auth_router por conta de "router = APIRouter(prefix="/auth", tags=["Auth"])" no arquivo controllers/auth.py
app.include_router(chat_router) # é chat_router por conta de "router = APIRouter(prefix="/chat", tags=["Chat"])" no arquivo controllers/chat.py
app.include_router(conversas_router) # é conversas_router por conta de "router = APIRouter(prefix="/conversas", tags=["Conversas"])" no arquivo controllers/conversas.py
app.include_router(pagamento_router) # é pagamento_router por conta de "router = APIRouter(prefix="/pagamento", tags=["Pagamento"])" no arquivo controllers/pagamento.py

# Router é uma função que vem do FASTAPI e permite a organização do projeto em módulos, cada módulo tem suas próprias rotas e funcionalidades. O router é criado em cada arquivo de controller (ex: auth.py, chat.py, conversas.py, pagamento.py) e depois incluído no arquivo principal (main.py) para que as rotas fiquem disponíveis na aplicação.









    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





    


    