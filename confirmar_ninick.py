import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# Atualizar usuario ninick
cursor.execute('UPDATE usuarios SET email_confirmado = 1, token_confirmacao = NULL WHERE nomeUsuario = ?', ('ninick',))
conn.commit()

# Verificar
cursor.execute('SELECT nomeUsuario, email, email_confirmado FROM usuarios WHERE nomeUsuario = ?', ('ninick',))
user = cursor.fetchone()

if user:
    print(f'\n✓ Email confirmado com sucesso!\n')
    print(f'Usuario: {user[0]}')
    print(f'Email: {user[1]}')
    print(f'Email confirmado: {"SIM" if user[2] == 1 else "NAO"}')
    print(f'\nAgora voce pode fazer login no Swagger UI!')
else:
    print('Usuario nao encontrado')

conn.close()
