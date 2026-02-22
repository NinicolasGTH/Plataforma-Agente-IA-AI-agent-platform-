from database import SessionLocal
from models.usuario import Usuario
from models.conversa import Conversa
from models.mensagem import Mensagem

db = SessionLocal()
users = db.query(Usuario).all()

print(f'\n=== Total de usuários no banco: {len(users)} ===\n')

for user in users:
    print(f'ID: {user.id}')
    print(f'Nome de usuário: {user.nomeUsuario}')
    print(f'Email: {user.email}')
    print(f'Email confirmado: {user.email_confirmado}')
    print(f'Token confirmação: {user.token_confirmacao[:20] if user.token_confirmacao else None}...')
    print('-' * 50)

db.close()
