from flask import Flask
from models import db, User, Reserva, Ganho, Refeicao, GastoMensal, GastoAvulso
from werkzeug.security import generate_password_hash
import os
from datetime import datetime, date
import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_mude_isso'
DB_URL = 'mysql://mysql:f16a8df513be1a4e1b52@easypanel.pontocomdesconto.com.br:33065/divisions_hotel?charset=utf8mb4'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL', DB_URL)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        print("Conectando ao banco MySQL no EasyPanel...")
        try:
            # Dropar todas as tabelas e recriar (CUIDADO: isso apaga todos os dados!)
            db.drop_all()
            db.create_all()
            print("Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            exit()
        
        # ========== INSERIR USUÁRIOS ==========
        print("\nInserindo usuários...")
        user_admin = User(username='admin', password_hash=generate_password_hash('admin123'))
        user_user = User(username='user', password_hash=generate_password_hash('user123'))
        db.session.add_all([user_admin, user_user])
        db.session.commit()
        print("✓ Usuários criados: admin/admin123, user/user123")
        
        # ========== INSERIR REFEIÇÕES ==========
        print("\nInserindo tipos de refeição...")
        refeicoes = [
            Refeicao(tipo='cafe', preco=20.0, descricao='Café da Manhã'),
            Refeicao(tipo='almoco', preco=30.0, descricao='Almoço'),
            Refeicao(tipo='janta', preco=25.0, descricao='Janta')
        ]
        db.session.add_all(refeicoes)
        db.session.commit()
        print("✓ Refeições inseridas: Café (R$20), Almoço (R$30), Janta (R$25)")
        
        # ========== INSERIR RESERVAS DE EXEMPLO ==========
        print("\nInserindo reservas de exemplo...")
        import json
        
        # Reserva 1: João Silva - 4 pessoas, 1 criança, café
        r1 = Reserva(
            hospede_nome='João Silva',
            num_pessoas=4,
            num_criancas=1,
            refeicoes=json.dumps(['cafe']),
            data_checkin=date(2025, 10, 20),
            data_checkout=date(2025, 10, 22),
            total=750.0,
            status='Confirmada'
        )
        
        # Reserva 2: Maria Oliveira - 2 pessoas, 0 crianças, almoço + janta
        r2 = Reserva(
            hospede_nome='Maria Oliveira',
            num_pessoas=2,
            num_criancas=0,
            refeicoes=json.dumps(['almoco', 'janta']),
            data_checkin=date(2025, 10, 25),
            data_checkout=date(2025, 10, 27),
            total=600.0,
            status='Check-in'
        )
        
        # Reserva 3: Carlos Santos - 3 pessoas, 0 crianças, sem refeições
        r3 = Reserva(
            hospede_nome='Carlos Santos',
            num_pessoas=3,
            num_criancas=0,
            refeicoes=None,
            data_checkin=date(2025, 11, 1),
            data_checkout=date(2025, 11, 3),
            total=900.0,
            status='Confirmada'
        )
        
        db.session.add_all([r1, r2, r3])
        db.session.commit()
        print("✓ 3 reservas de exemplo inseridas")
        
        # ========== INSERIR GANHOS ==========
        print("\nInserindo ganhos de exemplo...")
        
        g1 = Ganho(
            descricao='Check-out Reserva #2 - Maria Oliveira (2 pessoas)',
            valor=600.0,
            data=datetime.now(),
            reserva_id=2
        )
        
        g2 = Ganho(
            descricao='Ganho manual - Outros serviços',
            valor=150.0,
            data=datetime.now(),
            reserva_id=None
        )
        
        db.session.add_all([g1, g2])
        db.session.commit()
        print("✓ Ganhos inseridos")
        
        # ========== INSERIR GASTOS MENSAIS ==========
        print("\nInserindo gastos mensais de exemplo...")
        
        gm1 = GastoMensal(
            mes_ano='2025-10',
            categoria='Salários',
            valor=3000.0,
            descricao='Folha de pagamento'
        )
        
        gm2 = GastoMensal(
            mes_ano='2025-10',
            categoria='Aluguel',
            valor=2000.0,
            descricao='Aluguel do imóvel'
        )
        
        db.session.add_all([gm1, gm2])
        db.session.commit()
        print("✓ Gastos mensais inseridos")
        
        # ========== INSERIR GASTOS AVULSOS ==========
        print("\nInserindo gastos avulsos de exemplo...")
        
        ga1 = GastoAvulso(
            descricao='Compra de suprimentos de limpeza',
            categoria='Suprimentos',
            valor=250.0,
            data=date(2025, 10, 15)
        )
        
        ga2 = GastoAvulso(
            descricao='Reparo no chuveiro do banheiro',
            categoria='Manutenção',
            valor=350.0,
            data=date(2025, 10, 18)
        )
        
        db.session.add_all([ga1, ga2])
        db.session.commit()
        print("✓ Gastos avulsos inseridos")
        
        print("\n" + "="*50)
        print("✅ BANCO DE DADOS INICIALIZADO COM SUCESSO!")
        print("="*50)
        print("\nCom dados de exemplo:")
        print("  - 2 Usuários (admin, user)")
        print("  - 3 Tipos de Refeição")
        print("  - 3 Reservas de exemplo")
        print("  - 2 Ganhos")
        print("  - 2 Gastos mensais")
        print("  - 2 Gastos avulsos")
        print("\nAgora você pode executar: python app.py")