import os
print("Iniciando imports...")  # Debug: Confirma execução
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Reserva, Ganho, GastoMensal, GastoAvulso
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, and_
import json  # Para refeições JSON na rota /reservas
from dotenv import load_dotenv
# Driver MySQL para Railway (instale via pip install PyMySQL)
import pymysql
pymysql.install_as_MySQLdb()
load_dotenv()

print("Imports concluídos.")  # Debug

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_mude_isso'  # Mude para produção

# Conexão MySQL EasyPanel (nova URL fornecida)
DB_URL = 'mysql://mysql:f16a8df513be1a4e1b52@easypanel.pontocomdesconto.com.br:33065/divisions_hotel?charset=utf8mb4'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mysql:f16a8df513be1a4e1b52@easypanel.pontocomdesconto.com.br:33065/divisions_hotel'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}  # Evita timeouts em remoto

# Inicialização do DB (fora do try para sempre executar)
db.init_app(app)

# Filtro customizado para JSON no Jinja2
@app.template_filter('from_json')
def from_json_filter(value):
    """Converte string JSON para objeto Python"""
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []

# Contexto para templates: Verifica se usuário está logado (False no login)
@app.context_processor
def inject_is_logged_in():
    return dict(is_logged_in='user_id' in session)

# Teste de conexão será feito no startup dentro do app_context


# Categorias e preços fixos
CATEGORIAS_GASTOS = ['Manutenção', 'Suprimentos', 'Salários', 'Aluguel', 'Outros']
PRECO_ADULTO = 150.0
PRECO_CRIANCA = 80.0
PRECOS_REFEICOES = {'cafe': 20.0, 'almoco': 30.0, 'janta': 25.0}

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para acessar esta página.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Credenciais fixas (exemplo; substitua por DB se quiser)
        if username == 'admin' and password == 'admin123':
            session['user_id'] = 1  # Define session só após sucesso
            session['username'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas!', 'error')
    
    # GET: Limpa session para garantir is_logged_in=False (sem menu)
    session.clear()  # Força logout se acessou diretamente
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('Logout realizado.')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    hoje = datetime.now()
    
    # Contagem de reservas ativas (estabelecimento ocupado se houver reservas ativas)
    reservas_ativas = db.session.query(Reserva).filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status.in_(['Confirmada', 'Check-in'])
    ).count()
    
    # Status do estabelecimento (ocupado ou disponível)
    ocupado = 1 if reservas_ativas > 0 else 0
    disponivel = 0 if reservas_ativas > 0 else 1
    
    # Resumo Financeiro (MySQL date_format)
    mes_atual = hoje.strftime('%Y-%m')
    try:
        ganhos_mes = db.session.query(func.sum(Ganho.valor)).filter(
            func.date_format(Ganho.data, '%Y-%m') == mes_atual
        ).scalar() or 0
        gastos_mes = db.session.query(func.sum(GastoAvulso.valor)).filter(
            func.date_format(GastoAvulso.data, '%Y-%m') == mes_atual
        ).scalar() or 0
        gasto_mensal = db.session.query(func.sum(GastoMensal.valor)).filter(
            GastoMensal.mes_ano == mes_atual
        ).scalar() or 0
        total_gastos = gastos_mes + gasto_mensal
        lucro_mes = ganhos_mes - total_gastos
    except Exception as e:
        print(f"Debug Dashboard: {e}")  # Log sem flash para não poluir
        ganhos_mes, total_gastos, lucro_mes = 0, 0, 0
    
    return render_template('dashboard.html', 
                           total=1,  # Estabelecimento inteiro = 1 unidade
                           disp=disponivel, 
                           occ=ocupado, 
                           res=reservas_ativas,
                           ganhos_mes=ganhos_mes, 
                           total_gastos=total_gastos, 
                           lucro_mes=lucro_mes)

@app.route('/reservas', methods=['GET', 'POST'])
@login_required
def reservas():
    data_hoje = datetime.now().date()  # Data de hoje para minDate no calendário
    
    if request.method == 'POST':
        if 'hospede' in request.form:  # Nova reserva
            hospede_nome = request.form.get('hospede')
            num_pessoas = int(request.form.get('num_pessoas', 0))
            num_criancas = int(request.form.get('num_criancas', 0))
            refeicoes_str = request.form.get('refeicoes')  # JSON string do JS
            data_checkin = datetime.strptime(request.form.get('data_checkin'), '%Y-%m-%d').date()
            data_checkout = datetime.strptime(request.form.get('data_checkout'), '%Y-%m-%d').date()
            
            if not all([hospede_nome, num_pessoas > 0, data_checkin, data_checkout]):
                flash('Preencha todos os campos obrigatórios (pessoas > 0)!', 'error')
                return redirect(url_for('reservas'))
            
            if num_criancas > num_pessoas:
                flash('Número de crianças não pode exceder total de pessoas!', 'error')
                return redirect(url_for('reservas'))
            
            if data_checkin >= data_checkout:
                flash('Data de check-out deve ser posterior ao check-in!', 'error')
                return redirect(url_for('reservas'))
            
            # Verificar overlap geral (estabelecimento inteiro reservado)
            overlap = db.session.query(Reserva).filter(
                Reserva.status.in_(['Confirmada', 'Check-in']),
                Reserva.data_checkin < data_checkout,
                Reserva.data_checkout > data_checkin
            ).first()
            if overlap:
                flash('Datas conflitam com reserva existente no estabelecimento!', 'error')
                return redirect(url_for('reservas'))
            
            # Calcular total
            diarias = (data_checkout - data_checkin).days
            adultos = num_pessoas - num_criancas
            total_base = diarias * (adultos * PRECO_ADULTO + num_criancas * PRECO_CRIANCA)
            
            # Refeições: Parse JSON string e somar
            total_refeicoes = 0.0
            if refeicoes_str:
                refeicoes_list = json.loads(refeicoes_str)
                custo_refeicoes_por_dia = sum(PRECOS_REFEICOES.get(r, 0) for r in refeicoes_list)
                total_refeicoes = diarias * custo_refeicoes_por_dia * num_pessoas
            
            total = total_base + total_refeicoes
            
            # Salvar (refeicoes como string JSON)
            nova_reserva = Reserva(
                hospede_nome=hospede_nome,
                num_pessoas=num_pessoas,
                num_criancas=num_criancas,
                refeicoes=refeicoes_str,
                data_checkin=data_checkin,
                data_checkout=data_checkout,
                total=total,
                status='Confirmada'
            )
            db.session.add(nova_reserva)
            db.session.commit()
            flash('Reserva confirmada com sucesso!')
            return redirect(url_for('reservas'))
        
        # Check-in
        elif 'checkin' in request.form:
            reserva_id = request.form.get('id')
            if not reserva_id:
                flash('ID da reserva inválido!', 'error')
                return redirect(url_for('reservas'))
            reserva = Reserva.query.get_or_404(int(reserva_id))
            if reserva.status != 'Confirmada':
                flash('Apenas reservas confirmadas podem fazer check-in!', 'error')
                return redirect(url_for('reservas'))
            reserva.status = 'Check-in'
            db.session.commit()
            flash('Check-in realizado!')
            return redirect(url_for('reservas'))
        
        # Check-out
        elif 'checkout' in request.form:
            reserva_id = request.form.get('id')
            if not reserva_id:
                flash('ID da reserva inválido!', 'error')
                return redirect(url_for('reservas'))
            reserva = Reserva.query.get_or_404(int(reserva_id))
            reserva.status = 'Check-out'
            
            # Inserção automática de ganho no financeiro
            if not reserva.ganho:
                novo_ganho = Ganho(
                    descricao=f'Check-out Reserva #{reserva.id} - {reserva.hospede_nome} ({reserva.num_pessoas} pessoas)',
                    valor=reserva.total,
                    data=datetime.now(),
                    reserva_id=reserva.id
                )
                db.session.add(novo_ganho)
                print(f"Debug: Ganho automático adicionado para reserva #{reserva.id} - Valor: R$ {reserva.total}")
            
            db.session.commit()
            flash('Check-out realizado! Ganho registrado no financeiro.')
            return redirect(url_for('reservas'))
        
        # Excluir
        elif 'excluir' in request.form:
            reserva_id = request.form.get('id')
            if not reserva_id:
                flash('ID da reserva inválido!', 'error')
                return redirect(url_for('reservas'))
            reserva = Reserva.query.get_or_404(int(reserva_id))
            if reserva.ganho:
                db.session.delete(reserva.ganho)
            db.session.delete(reserva)
            db.session.commit()
            flash('Reserva excluída com sucesso!')
            return redirect(url_for('reservas'))
    
    # GET: Lista reservas
    reservas_lista = Reserva.query.order_by(Reserva.data_checkin.desc()).all()
    
    # Preparar datas reservadas para calendário JS (geral)
    datas_reservadas = []
    for res in reservas_lista:
        if res.status in ['Confirmada', 'Check-in']:
            datas_reservadas.append({
                'checkin': res.data_checkin.strftime('%Y-%m-%d'),
                'checkout': res.data_checkout.strftime('%Y-%m-%d')
            })
    
    return render_template('reservas.html', 
                           reservas=reservas_lista, 
                           data_hoje=data_hoje,
                           datas_reservadas=datas_reservadas, 
                           precos_refeicoes=PRECOS_REFEICOES)

@app.route('/financeiro', methods=['GET', 'POST'])
@login_required
def financeiro():
    if request.method == 'POST':
        try:
            tipo = request.form.get('tipo')
            if tipo == 'ganho':
                desc = request.form.get('descricao')
                valor = float(request.form.get('valor'))
                data_str = request.form.get('data')
                data = datetime.strptime(data_str, '%Y-%m-%d') if data_str else datetime.now()
                reserva_id = int(request.form.get('reserva_id')) if request.form.get('reserva_id') else None
                if Ganho.query.filter_by(descricao=desc).first():
                    flash('Ganho com esta descrição já existe!')
                    return redirect(url_for('financeiro'))
                novo = Ganho(descricao=desc, valor=valor, data=data, reserva_id=reserva_id)
                db.session.add(novo)
                flash('Ganho cadastrado!')
            
            elif tipo == 'gasto_mensal':
                mes_ano = request.form.get('mes_ano')
                categoria = request.form.get('categoria')
                valor = float(request.form.get('valor'))
                desc = request.form.get('descricao')
                if GastoMensal.query.filter_by(mes_ano=mes_ano, categoria=categoria).first():
                    flash('Gasto mensal para este mês/categoria já existe!')
                    return redirect(url_for('financeiro'))
                novo = GastoMensal(mes_ano=mes_ano, categoria=categoria, valor=valor, descricao=desc)
                db.session.add(novo)
                flash('Gasto mensal cadastrado!')
            
            elif tipo == 'gasto_avulso':
                desc = request.form.get('descricao')
                categoria = request.form.get('categoria')
                valor = float(request.form.get('valor'))
                data_str = request.form.get('data')
                data = datetime.strptime(data_str, '%Y-%m-%d').date()
                novo = GastoAvulso(descricao=desc, categoria=categoria, valor=valor, data=data)
                db.session.add(novo)
                flash('Gasto avulso cadastrado!')
            
            # Excluir
            if 'excluir' in request.form:
                id = int(request.form.get('id'))
                tipo_ex = request.form.get('tipo_excluir')
                if tipo_ex == 'ganho':
                    db.session.delete(Ganho.query.get(id))
                elif tipo_ex == 'gasto_mensal':
                    db.session.delete(GastoMensal.query.get(id))
                elif tipo_ex == 'gasto_avulso':
                    db.session.delete(GastoAvulso.query.get(id))
                db.session.commit()
                flash('Item excluído!')
            
            db.session.commit()
        except ValueError:
            flash('Dados inválidos!')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}')
        return redirect(url_for('financeiro'))
    
    ganhos = Ganho.query.order_by(Ganho.data.desc()).all()
    gastos_mensais = GastoMensal.query.order_by(GastoMensal.mes_ano.desc()).all()
    gastos_avulsos = GastoAvulso.query.order_by(GastoAvulso.data.desc()).all()
    reservas = Reserva.query.all()
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    return render_template('financeiro.html', ganhos=ganhos, gastos_mensais=gastos_mensais, gastos_avulsos=gastos_avulsos,
                           reservas=reservas, categorias=CATEGORIAS_GASTOS, data_hoje=data_hoje)

@app.route('/relatorios/financeiro')
@login_required
def relatorios_financeiro():
    hoje = datetime.now()
    data_inicio = hoje - timedelta(days=365)
    
    try:
        ganhos_por_mes = db.session.query(
            func.date_format(Ganho.data, '%Y-%m').label('mes'),
            func.sum(Ganho.valor).label('total')
        ).filter(Ganho.data >= data_inicio).group_by('mes').order_by('mes').all()
        
        # Gastos avulsos por mês
        gastos_avulsos_por_mes = db.session.query(
            func.date_format(GastoAvulso.data, '%Y-%m').label('mes'),
            func.sum(GastoAvulso.valor).label('total')
        ).filter(GastoAvulso.data >= data_inicio.date()).group_by('mes').order_by('mes').all()
        
        # Gastos mensais por mês
        gastos_mensais_por_mes = db.session.query(
            GastoMensal.mes_ano.label('mes'),
            func.sum(GastoMensal.valor).label('total')
        ).filter(GastoMensal.mes_ano >= data_inicio.strftime('%Y-%m')).group_by('mes').order_by('mes').all()
        
        # Merge gastos por mês
        meses = set([g[0] for g in ganhos_por_mes] + [g[0] for g in gastos_avulsos_por_mes] + [g[0] for g in gastos_mensais_por_mes])
        dados_ganhos = {m: next((g[1] for g in ganhos_por_mes if g[0] == m), 0) for m in meses}
        dados_gastos_avulsos = {m: next((g[1] for g in gastos_avulsos_por_mes if g[0] == m), 0) for m in meses}
        dados_gastos_mensais = {m: next((g[1] for g in gastos_mensais_por_mes if g[0] == m), 0) for m in meses}
        dados_gastos = {m: dados_gastos_avulsos.get(m, 0) + dados_gastos_mensais.get(m, 0) for m in meses}
        
        # Lucros por mês
        dados_lucros = {m: dados_ganhos.get(m, 0) - dados_gastos.get(m, 0) for m in meses}
        
        # Gastos por categoria (avulsos + mensais)
        gastos_por_categoria = db.session.query(
            GastoAvulso.categoria,
            func.sum(GastoAvulso.valor)
        ).filter(GastoAvulso.data >= data_inicio.date()).group_by(GastoAvulso.categoria).all()
        
        gastos_mensais_por_cat = db.session.query(
            GastoMensal.categoria,
            func.sum(GastoMensal.valor)
        ).filter(GastoMensal.mes_ano >= data_inicio.strftime('%Y-%m')).group_by(GastoMensal.categoria).all()
        
        # Merge categorias
        cat_dict = {}
        for cat, val in gastos_por_categoria:
            cat_dict[cat] = cat_dict.get(cat, 0) + val
        for cat, val in gastos_mensais_por_cat:
            cat_dict[cat] = cat_dict.get(cat, 0) + val
        dados_categorias = {cat: val for cat, val in cat_dict.items() if val > 0}
        
        # Serializa listas para Chart.js
        meses_list = sorted(list(meses))
        ganhos_list = [dados_ganhos.get(m, 0) for m in meses_list]
        gastos_list = [dados_gastos.get(m, 0) for m in meses_list]
        lucros_list = [dados_lucros.get(m, 0) for m in meses_list]
        categorias_list = list(dados_categorias.keys())
        valores_categorias = list(dados_categorias.values())
        
    except Exception as e:
        print(f"Debug Relatórios Financeiro: {e}")  # Log para debug
        meses_list, ganhos_list, gastos_list, lucros_list = [], [], [], []
        categorias_list, valores_categorias = [], []
    
    return render_template('relatorios_financeiro.html',
                           meses=meses_list, ganhos=ganhos_list, gastos=gastos_list, lucros=lucros_list,
                           categorias=categorias_list, valores_categorias=valores_categorias)

@app.route('/relatorios')
@login_required
def relatorios():
    hoje = datetime.now()
    
    # Hóspedes atuais (reservas ativas)
    hospedes_atuais = Reserva.query.filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status.in_(['Confirmada', 'Check-in'])
    ).all()
    
    # Histórico recente
    historico = Reserva.query.order_by(Reserva.data_checkin.desc()).limit(10).all()
    
    # Taxa de ocupação (estabelecimento inteiro = 1 unidade)
    total = 1
    ocupados = 1 if len(hospedes_atuais) > 0 else 0
    taxa_ocupacao = (ocupados / total * 100) if total > 0 else 0
    
    # Resumo Financeiro (MySQL date_format)
    mes_atual = hoje.strftime('%Y-%m')
    try:
        ganhos_mes = db.session.query(func.sum(Ganho.valor)).filter(
            func.date_format(Ganho.data, '%Y-%m') == mes_atual
        ).scalar() or 0
        total_gastos_avulsos = db.session.query(func.sum(GastoAvulso.valor)).filter(
            func.date_format(GastoAvulso.data, '%Y-%m') == mes_atual
        ).scalar() or 0
        total_gastos_mensais = db.session.query(func.sum(GastoMensal.valor)).filter(
            GastoMensal.mes_ano == mes_atual
        ).scalar() or 0
        total_gastos = total_gastos_avulsos + total_gastos_mensais
        lucro_mes = ganhos_mes - total_gastos
    except Exception as e:
        print(f"Debug Relatórios: {e}")
        ganhos_mes, total_gastos, lucro_mes = 0, 0, 0
    
    return render_template('relatorios.html', 
                           hospedes=hospedes_atuais, 
                           historico=historico, 
                           total=total, 
                           occ=ocupados, 
                           taxa=taxa_ocupacao,
                           ganhos_mes=ganhos_mes, 
                           total_gastos=total_gastos, 
                           lucro_mes=lucro_mes)

if __name__ == '__main__':
    print("Iniciando servidor Flask...")  # Debug final
    try:
        with app.app_context():
            # Teste de conexão
            try:
                db.session.execute("SELECT 1")
                print("DB conectada com sucesso ao MySQL EasyPanel.")
            except Exception as e:
                print(f"Erro na conexão DB: {e}")
            
            # Criar tabelas
            db.create_all()
            print("Tabelas criadas/verificadas no DB remoto (EasyPanel).")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}. Verifique models.py e conexão. App continua rodando.")
    app.run(debug=True, host='127.0.0.1', port=5000)