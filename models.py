from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Quarto(db.Model):
    __tablename__ = 'quartos'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Disponivel')
    preco_diaria = db.Column(db.Float, nullable=False)
    reservas = db.relationship('Reserva', backref='quarto', lazy=True, cascade='all, delete-orphan')

class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    quarto_id = db.Column(db.Integer, db.ForeignKey('quartos.id'), nullable=False)
    hospede_nome = db.Column(db.String(100), nullable=False)
    data_checkin = db.Column(db.DateTime, nullable=False)
    data_checkout = db.Column(db.DateTime, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Confirmada')

    def has_overlap(self, nova_checkin, nova_checkout):
        return (self.data_checkin < nova_checkout) and (self.data_checkout > nova_checkin)

# Novos Modelos Financeiros
class Ganho(db.Model):
    __tablename__ = 'ganhos'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)  # ex: 'Check-out Reserva #1'
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, default=datetime.now)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)  # Link opcional
    reserva = db.relationship('Reserva', backref='ganho', uselist=False)

class GastoMensal(db.Model):
    __tablename__ = 'gastos_mensais'
    id = db.Column(db.Integer, primary_key=True)
    mes_ano = db.Column(db.String(7), unique=True, nullable=False)  # ex: '2025-10'
    categoria = db.Column(db.String(50), nullable=False)  # ex: 'Aluguel', 'Salários'
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))

class GastoAvulso(db.Model):
    __tablename__ = 'gastos_avulsos'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)  # ex: 'Manutenção', 'Suprimentos', 'Outros'
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)