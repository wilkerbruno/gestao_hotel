print("Iniciando imports...")

from app import app
from models import db, User
from werkzeug.security import generate_password_hash

print("Imports concluídos.")

with app.app_context():
    try:
        # Cria o usuário admin
        user = User(username='user', password_hash=generate_password_hash('user123'))

        db.session.add(user)
        db.session.commit()
        print("Usuário 'admin' criado com sucesso!")

    except Exception as e:
        print(f"Erro na conexão DB ou ao criar usuário: {e}")
