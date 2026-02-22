from database import SessionLocal
from models.usuario import Usuario
from models.conversa import Conversa  # Importar para resolver relacionamentos
from models.mensagem import Mensagem  # Importar para resolver relacionamentos

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.nomeUsuario == 'venom').first()

if user:
    print(f'Nome: {user.nomeUsuario}')
    print(f'Email: {user.email}')
    print(f'Email confirmado ANTES: {user.email_confirmado}')
    
    user.email_confirmado = True
    user.token_confirmacao = None
    db.commit()
    
    print(f'Email confirmado DEPOIS: {user.email_confirmado}')
    print('\n✓ Pronto! Agora pode fazer login.')
else:
    print('Usuario nao encontrado')

db.close()
