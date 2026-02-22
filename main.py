from fastapi import FastAPI
from dotenv import load_dotenv
from database import Base, engine
from controllers.auth import router as auth_router
from controllers.chat import router as chat_router
from controllers.conversas import router as conversas_router
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# A chave da api vem do arquivo .env

# Aplicativo FastAPI
app = FastAPI(title="Meu Projeto com Strands e Groq", version="1.0.0")

@app.on_event("startup")
def criar_tabelas():
    """
    Cria as tabelas no banco de dados ao iniciar o aplicativo
    """
    Base.metadata.create_all(bind=engine)

# incluir rotas

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversas_router)








    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



    


    