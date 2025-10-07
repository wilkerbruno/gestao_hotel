import os
print("Iniciando imports...")  # Debug: Confirma execução
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Quarto, Reserva, Ganho, GastoMensal, GastoAvulso
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, and_
print("Imports concluídos.")  # Debug

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_mude_isso'  # Mude para produção

# Conexão MySQL Railway (verifique se senha/URL está correta)
DB_URL = 'mysql+pymysql://root:eTuaKzBPnRjjNMxHBYkFEiYkMWTgFRfA@yamanote.proxy.rlwy.net:30781/railway'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL', DB_URL)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}  # Evita timeouts

try:
    db.init_app(app)
    @app.context_processor
    def inject_is_logged_in():
         return dict(is_logged_in='user_id' in session)
    print("DB inicializada com sucesso.")  # Debug
except Exception as e:
    print(f"Erro na DB: {e}")  # Debug: Mostra se conexão falha no startup

# Categorias fixas
CATEGORIAS_GASTOS = ['Manutenção', 'Suprimentos', 'Salários', 'Aluguel', 'Outros']

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
    total_quartos = Quarto.query.count()
    hoje = datetime.now()
    ocupados = db.session.query(Quarto.id).join(Reserva).filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status != 'Check-out'
    ).distinct().count()
    disponiveis = total_quartos - ocupados
    reservas_hoje = db.session.query(Reserva).filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status != 'Check-out'
    ).count()
    
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
    
    return render_template('dashboard.html', total=total_quartos, disp=disponiveis, occ=ocupados, res=reservas_hoje,
                           ganhos_mes=ganhos_mes, total_gastos=total_gastos, lucro_mes=lucro_mes)

@app.route('/quartos', methods=['GET', 'POST'])
@login_required
def quartos():
    if request.method == 'POST':
        try:
            quarto_id = request.form.get('id', '').strip()
            numero = request.form.get('numero', '').strip()
            tipo = request.form.get('tipo', '').strip()
            preco = request.form.get('preco', '0').strip()
            status = request.form.get('status', 'Disponivel').strip()

            if not all([numero, tipo, preco]):
                flash('Preencha todos os campos obrigatórios!')
                return redirect(url_for('quartos'))
            
            preco_float = float(preco)
            if preco_float <= 0:
                flash('Preço deve ser maior que zero!')
                return redirect(url_for('quartos'))

            if 'excluir' in request.form:
                quarto = Quarto.query.get_or_404(int(quarto_id))
                for reserva in quarto.reservas:
                    if reserva.status == 'Check-in':
                        quarto.status = 'Disponivel'
                    db.session.delete(reserva)
                db.session.delete(quarto)
                db.session.commit()
                flash('Quarto excluído com sucesso!')
                return redirect(url_for('quartos'))

            if not quarto_id:  # Novo
                if Quarto.query.filter_by(numero=numero).first():
                    flash('Número de quarto já existe!')
                    return redirect(url_for('quartos'))
                novo = Quarto(numero=numero, tipo=tipo, preco_diaria=preco_float, status=status)
                db.session.add(novo)
                db.session.commit()
                flash('Quarto criado com sucesso!')
            else:  # Editar
                quarto = Quarto.query.get_or_404(int(quarto_id))
                if quarto.numero != numero and Quarto.query.filter_by(numero=numero).first():
                    flash('Número de quarto já existe!')
                    return redirect(url_for('quartos'))
                quarto.numero = numero
                quarto.tipo = tipo
                quarto.preco_diaria = preco_float
                quarto.status = status
                db.session.commit()
                flash('Quarto atualizado com sucesso!')
        
        except ValueError as e:
            db.session.rollback()
            flash(f'Erro nos dados: {str(e)}')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}')
        return redirect(url_for('quartos'))
    
    quartos_lista = Quarto.query.order_by(Quarto.numero).all()
    return render_template('quartos.html', quartos=quartos_lista)

@app.route('/reservas', methods=['GET', 'POST'])
@login_required
def reservas():
    quartos = Quarto.query.all()  # Lista de quartos para select
    data_hoje = datetime.now().date()  # Data de hoje para minDate no calendário
    
    if request.method == 'POST':
        if 'quarto_id' in request.form:  # Nova reserva
            quarto_id = request.form.get('quarto_id')
            hospede_nome = request.form.get('hospede')
            data_checkin = datetime.strptime(request.form.get('data_checkin'), '%Y-%m-%d').date()
            data_checkout = datetime.strptime(request.form.get('data_checkout'), '%Y-%m-%d').date()
            
            if not all([quarto_id, hospede_nome, data_checkin, data_checkout]):
                flash('Preencha todos os campos!', 'error')
                return redirect(url_for('reservas'))
            
            quarto = Quarto.query.get_or_404(quarto_id)
            if quarto.status != 'Disponivel':
                flash('Quarto não disponível!', 'error')
                return redirect(url_for('reservas'))
            
            if data_checkin >= data_checkout:
                flash('Data de check-out deve ser posterior ao check-in!', 'error')
                return redirect(url_for('reservas'))
            
            # Verificar overlap com reservas existentes
            overlap = db.session.query(Reserva).filter(
                Reserva.quarto_id == quarto_id,
                Reserva.status != 'Cancelada',
                Reserva.data_checkin < data_checkout,
                Reserva.data_checkout > data_checkin
            ).first()
            if overlap:
                flash('Datas conflitam com reserva existente!', 'error')
                return redirect(url_for('reservas'))
            
            # Calcular total (diárias * preço)
            diarias = (data_checkout - data_checkin).days
            total = diarias * quarto.preco_diaria
            
            nova_reserva = Reserva(
                quarto_id=quarto_id,
                hospede_nome=hospede_nome,
                data_checkin=data_checkin,
                data_checkout=data_checkout,
                total=total,
                status='Confirmada'
            )
            quarto.status = 'Reservado'
            db.session.add(nova_reserva)
            db.session.commit()
            flash('Reserva confirmada com sucesso!')
            return redirect(url_for('reservas'))
        
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
            reserva.quarto.status = 'Ocupado'
            db.session.commit()
            flash('Check-in realizado!')
            return redirect(url_for('reservas'))
        
        elif 'checkout' in request.form:
            reserva_id = request.form.get('id')
            if not reserva_id:
                flash('ID da reserva inválido!', 'error')
                return redirect(url_for('reservas'))
            reserva = Reserva.query.get_or_404(int(reserva_id))
            reserva.status = 'Check-out'
            reserva.quarto.status = 'Disponivel'
            
            # Inserção automática de ganho no financeiro (se não existir)
            if not reserva.ganho:  # Verifica duplicata via relacionamento
                novo_ganho = Ganho(
                    descricao=f'Check-out Reserva #{reserva.id} - {reserva.hospede_nome}',
                    valor=reserva.total,  # Usa o total da reserva
                    data=datetime.now(),
                    reserva_id=reserva.id  # Link para rastrear
                )
                db.session.add(novo_ganho)
                print(f"Debug: Ganho automático adicionado para reserva #{reserva.id} - Valor: R$ {reserva.total}")  # Log opcional
            
            db.session.commit()
            flash('Check-out realizado! Ganho registrado no financeiro.')
            return redirect(url_for('reservas'))
        
        elif 'excluir' in request.form:
            reserva_id = request.form.get('id')
            if not reserva_id:
                flash('ID da reserva inválido!', 'error')
                return redirect(url_for('reservas'))
            reserva = Reserva.query.get_or_404(int(reserva_id))
            reserva.status = 'Cancelada'
            reserva.quarto.status = 'Disponivel'
            db.session.commit()
            flash('Reserva cancelada!')
            return redirect(url_for('reservas'))
    
    # GET: Lista reservas
    reservas_lista = Reserva.query.order_by(Reserva.data_checkin.desc()).all()
    
    # Preparar datas reservadas para calendário JS (por quarto)
    datas_reservadas = []
    for res in reservas_lista:
        if res.status != 'Cancelada':  # Só reservas ativas
            datas_reservadas.append({
                'quarto_id': res.quarto_id,
                'checkin': res.data_checkin.strftime('%Y-%m-%d'),
                'checkout': res.data_checkout.strftime('%Y-%m-%d')
            })
    
    return render_template('reservas.html', reservas=reservas_lista, quartos=quartos, data_hoje=data_hoje,
                           datas_reservadas=datas_reservadas)


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
        ).filter(Ganho.data >= data_inicio        ).group_by('mes').order_by('mes').all()
        
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
    hospedes_atuais = Reserva.query.filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status != 'Check-out'
    ).all()
    historico = Reserva.query.order_by(Reserva.data_checkin.desc()).limit(10).all()
    total = Quarto.query.count()
    ocupados = db.session.query(Quarto.id).join(Reserva).filter(
        Reserva.data_checkin <= hoje,
        Reserva.data_checkout > hoje,
        Reserva.status != 'Check-out'
    ).distinct().count()
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
    
    return render_template('relatorios.html', hospedes=hospedes_atuais, historico=historico, total=total, occ=ocupados, taxa=taxa_ocupacao,
                           ganhos_mes=ganhos_mes, total_gastos=total_gastos, lucro_mes=lucro_mes)

if __name__ == '__main__':
    print("Iniciando servidor Flask...")  # Debug final
    app.run(debug=True, host='127.0.0.1', port=5000)