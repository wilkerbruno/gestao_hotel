from flask import Flask
from models import db, Quarto, Reserva
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_mude_isso'
DB_URL = 'mysql+pymysql://root:eTuaKzBPnRjjNMxHBYkFEiYkMWTgFRfA@yamanote.proxy.rlwy.net:30781/railway'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL', DB_URL)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db.init_app(app)

def migrate_quarto_status():
    with app.app_context():
        hoje = datetime.now()
        for quarto in Quarto.query.all():
            # Se status 'Ocupado', checa se há reserva ativa hoje
            if quarto.status == 'Ocupado':
                tem_ativo = db.session.query(Reserva).filter(
                    Reserva.quarto_id == quarto.id,
                    Reserva.data_checkin <= hoje,
                    Reserva.data_checkout > hoje,
                    Reserva.status == 'Check-in'
                ).first()
                if not tem_ativo:
                    quarto.status = 'Disponivel'
                    print(f"Quarto {quarto.numero} ajustado para 'Disponivel'.")
        db.session.commit()
        print("Migração concluída!")

if __name__ == '__main__':
    migrate_quarto_status()