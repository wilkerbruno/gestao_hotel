from flask import Flask
from models import db, User
from werkzeug.security import generate_password_hash
import os

# Configuração temporária para o script
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_mude_isso'
DB_URL = 'mysql+pymysql://root:eTuaKzBPnRjjNMxHBYkFEiYkMWTgFRfA@yamanote.proxy.rlwy.net:30781/railway'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL', DB_URL)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db.init_app(app)

def init_database():
    with app.app_context():
        print("Conectando ao banco MySQL no Railway...")
        try:
            db.create_all()  # Cria tabelas se não existirem (users, quartos, reservas)
            print("Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            return

        # Insere usuário admin se não existir
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('123456')
            admin = User(username='admin', password=hashed_pw)
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado (username: admin, password: 123456)")
        else:
            print("Usuário admin já existe.")





from app import app, db
from models import User, Quarto, Reserva, Ganho, GastoMensal, GastoAvulso
from werkzeug.security import generate_password_hash
from datetime import datetime, date

with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Usuário admin
    user = User(username='admin', password=generate_password_hash('admin123'))
    db.session.add(user)
    
    # Quartos exemplo
    q1 = Quarto(numero='101', tipo='Single', preco_diaria=150.0, status='Disponivel')
    q2 = Quarto(numero='102', tipo='Duplo', preco_diaria=250.0, status='Disponivel')
    db.session.add_all([q1, q2])
    db.session.commit()
    
    # Reserva exemplo (para ganho auto)
    r1 = Reserva(quarto_id=1, hospede_nome='João Silva', data_checkin=datetime(2025, 10, 10), data_checkout=datetime(2025, 10, 12), total=300.0, status='Check-out')
    db.session.add(r1)
    db.session.commit()
    
    # Ganho auto da reserva
    g1 = Ganho(descricao='Check-out Reserva #1 - João Silva', valor=300.0, data=datetime.now(), reserva_id=1)
    db.session.add(g1)
    
    # Gastos exemplo
    gm1 = GastoMensal(mes_ano='2025-10', categoria='Aluguel', valor=2000.0, descricao='Aluguel do imóvel')
    ga1 = GastoAvulso(descricao='Manutenção ar-condicionado', categoria='Manutenção', valor=500.0, data=date(2025, 10, 5))
    ga2 = GastoAvulso(descricao='Suprimentos limpeza', categoria='Suprimentos', valor=200.0, data=date(2025, 10, 15))
    db

if __name__ == '__main__':
    init_database()
    print("Inicialização do banco concluída! Agora rode 'python app.py' para iniciar o sistema.")