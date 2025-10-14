from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Parametro(db.Model):
    """Tabela de parâmetros de preços (mantida para referência, mas preços agora em Refeição)"""
    id = db.Column(db.Integer, primary_key=True)
    preco_adulto = db.Column(db.Float, nullable=False, default=150.0)
    preco_crianca = db.Column(db.Float, nullable=False, default=80.0)

class Refeicao(db.Model):
    """Tabela de tipos de refeição com seus preços"""
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), unique=True, nullable=False)  # 'cafe', 'almoco', 'janta'
    preco = db.Column(db.Float, nullable=False)  # Preço por pessoa por dia
    descricao = db.Column(db.String(255), nullable=True)

class Reserva(db.Model):
    """Reserva sem relação com quartos - apenas hóspedes, datas e refeições"""
    id = db.Column(db.Integer, primary_key=True)
    hospede_nome = db.Column(db.String(100), nullable=False)
    num_pessoas = db.Column(db.Integer, nullable=False)  # Total de pessoas (adultos + crianças)
    num_criancas = db.Column(db.Integer, nullable=False, default=0)
    data_checkin = db.Column(db.Date, nullable=False)
    data_checkout = db.Column(db.Date, nullable=False)
    refeicoes = db.Column(db.Text, nullable=True)  # JSON string com tipos de refeição selecionadas
    total = db.Column(db.Float, nullable=False)  # Total calculado
    status = db.Column(db.String(50), default='Confirmada')  # Confirmada, Check-in, Check-out
    data_reserva = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com ganhos
    ganho = db.relationship('Ganho', back_populates='reserva', uselist=False, cascade='all, delete-orphan')

    def calcular_total(self, preco_adulto=150.0, preco_crianca=80.0, precos_refeicoes=None):
        """
        Calcula o total da reserva baseado em:
        - Número de dias (checkout - checkin)
        - Número de adultos (pessoas - crianças) e crianças
        - Refeições selecionadas
        """
        if precos_refeicoes is None:
            precos_refeicoes = {'cafe': 20.0, 'almoco': 30.0, 'janta': 25.0}
        
        dias = (self.data_checkout - self.data_checkin).days or 1
        adultos = self.num_pessoas - self.num_criancas
        
        # Hospedagem base
        total_base = dias * (adultos * preco_adulto + self.num_criancas * preco_crianca)
        
        # Refeições
        total_refeicoes = 0.0
        if self.refeicoes:
            import json
            refeicoes_list = json.loads(self.refeicoes)
            custo_refeicoes_por_dia = sum(precos_refeicoes.get(r, 0) for r in refeicoes_list)
            total_refeicoes = dias * custo_refeicoes_por_dia * self.num_pessoas
        
        self.total = total_base + total_refeicoes
        return self.total


class Ganho(db.Model):
    """Registro de ganhos/receitas"""
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable=True)
    
    # Relacionamento com reserva
    reserva = db.relationship('Reserva', back_populates='ganho')


class GastoMensal(db.Model):
    """Gastos recorrentes mensais por categoria"""
    id = db.Column(db.Integer, primary_key=True)
    mes_ano = db.Column(db.String(7), nullable=False)  # YYYY-MM
    categoria = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)


class GastoAvulso(db.Model):
    """Gastos pontuais não recorrentes"""
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)