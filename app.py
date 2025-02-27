from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import tempfile
import os
import subprocess
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///protocolo.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)

# Modelo do Banco de Dados
class Protocolo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    assunto = db.Column(db.String(200), nullable=False)
    data_hora = db.Column(db.String(50), default=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

# Rota principal
@app.route('/')
def index():
    protocolos = Protocolo.query.all()
    return render_template('index.html', protocolos=protocolos)

# Rota para adicionar protocolo
@app.route('/add', methods=['POST'])
def add():
    nome = request.form['nome']
    assunto = request.form['assunto']
    if nome and assunto:
        novo_protocolo = Protocolo(nome=nome, assunto=assunto)
        db.session.add(novo_protocolo)
        db.session.commit()
        flash('Protocolo adicionado com sucesso!')
    return redirect(url_for('index'))

# Rota para excluir protocolo
@app.route('/delete/<int:id>')
def delete(id):
    protocolo = Protocolo.query.get(id)
    if protocolo:
        db.session.delete(protocolo)
        db.session.commit()
        flash('Protocolo excluído com sucesso!')
    return redirect(url_for('index'))

# Rota para imprimir protocolo
@app.route('/print/<int:id>')
def print_protocolo(id):
    protocolo = Protocolo.query.get(id)
    if protocolo:
        temp_pdf = tempfile.mktemp(".pdf")
        c = canvas.Canvas(temp_pdf, pagesize=(9 * cm, 5 * cm))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(10, 90, "Câmara de Vereadores de Glória do Goitá")
        c.setFont("Helvetica", 8)
        c.drawString(10, 75, f"Data e Hora: {protocolo.data_hora}")
        c.drawString(10, 60, f"Assunto: {protocolo.assunto}")
        c.drawString(10, 45, "Email: camaraggp@gmail.com")
        c.save()

        try:
            subprocess.run(["cmd", "/c", "start", "", temp_pdf], check=True)
            flash("Protocolo enviado para impressão!")
        except Exception as e:
            flash(f"Erro ao imprimir: {e}")
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    os.makedirs("instance", exist_ok=True)  # Criar a pasta instance se não existir
    with app.app_context():
        db.create_all()
    app.run(debug=True)
