from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import datetime
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.graphics.barcode import code128

# Configuração do Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///protocolos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"

# Banco de Dados
db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Criar pasta static se não existir
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Modelo de Usuário
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# Modelo de Protocolo
class Protocolo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    assunto = db.Column(db.String(200), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# Criar tabelas SE não existirem
with app.app_context():
    print("🔄 Verificando banco de dados...")
    db.create_all()

# Gerenciar sessão do usuário
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# Rota de Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if Usuario.query.filter_by(username=username).first():
            flash("Usuário já existe!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        novo_usuario = Usuario(username=username, password_hash=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Conta criada com sucesso! Faça login.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('index'))
        else:
            flash("Credenciais inválidas!", "danger")

    return render_template('login.html')

# Rota de Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Você saiu da conta.", "info")
    return redirect(url_for('login'))

# Rota Principal (Lista Protocolos)
@app.route('/')
@login_required
def index():
    protocolos = Protocolo.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", protocolos=protocolos, current_user=current_user)

# Adicionar Protocolo
@app.route('/add', methods=['POST'])
@login_required
def add():
    nome = request.form['nome']
    assunto = request.form['assunto']
    
    novo_protocolo = Protocolo(nome=nome, assunto=assunto, user_id=current_user.id)
    db.session.add(novo_protocolo)
    db.session.commit()
    
    flash("Protocolo adicionado com sucesso!", "success")
    return redirect(url_for('index'))

# Excluir Protocolo
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    protocolo = Protocolo.query.get_or_404(id)

    if protocolo.user_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('index'))
    
    db.session.delete(protocolo)
    db.session.commit()
    
    flash("Protocolo removido!", "danger")
    return redirect(url_for('index'))

# Função para gerar PDF
def gerar_pdf(protocolo, pdf_filename):
    """
    Função que gera um PDF com os detalhes do protocolo.
    """
    try:
        print(f"📄 Gerando PDF em: {pdf_filename}...")

        c = canvas.Canvas(pdf_filename, pagesize=letter)

        # Adiciona informações ao PDF
        c.setFont("Helvetica-Bold", 16)
        c.drawString(200, 800, "PROTOCOLO DE REGISTRO")

        c.setFont("Helvetica", 12)
        c.drawString(100, 750, f"ID: {protocolo.id}")
        c.drawString(100, 730, f"Nome: {protocolo.nome}")
        c.drawString(100, 710, f"Assunto: {protocolo.assunto}")
        c.drawString(100, 690, f"Data: {protocolo.data_hora.strftime('%d/%m/%Y %H:%M')}")

        # Criar código de barras
        barcode_value = str(protocolo.id)
        barcode = code128.Code128(barcode_value, barHeight=50, barWidth=1.5)
        barcode.drawOn(c, 100, 600)

        c.showPage()
        c.save()

        # Verifica se o arquivo foi realmente criado
        for _ in range(3):
            if os.path.exists(pdf_filename):
                print(f"✅ PDF gerado com sucesso: {pdf_filename}")
                return True
            time.sleep(1)

        print("⚠ Erro ao gerar o PDF! Arquivo não encontrado.")
        return False

    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        return False

# Rota para baixar PDF
@app.route('/print/pdf/<int:id>')
@login_required
def print_pdf(id):
    protocolo = Protocolo.query.get_or_404(id)

    pdf_filename = os.path.join(STATIC_DIR, f"protocolo_{id}.pdf")
    print(f"📂 Criando PDF em: {pdf_filename}")

    if gerar_pdf(protocolo, pdf_filename):
        if os.path.exists(pdf_filename):
            print(f"📂 Enviando PDF para download: {pdf_filename}")
            return send_file(pdf_filename, as_attachment=True, mimetype="application/pdf")

        flash("Erro ao gerar o PDF!", "danger")
    else:
        flash("Erro ao criar o PDF!", "danger")

    return redirect(url_for('index'))

# Executar o servidor Flask
if __name__ == '__main__':
    app.run(debug=True)
