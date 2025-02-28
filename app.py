from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
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

class Protocolo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    assunto = db.Column(db.String(200), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.datetime.now)

# Criar o banco de dados
with app.app_context():
    db.create_all()

# Criar o diretório 'static/' se não existir
if not os.path.exists("static"):
    os.makedirs("static")

# Rota principal (lista protocolos)
@app.route('/')
def index():
    protocolos = Protocolo.query.all()
    return render_template("index.html", protocolos=protocolos)

# Adicionar protocolo
@app.route('/add', methods=['POST'])
def add():
    nome = request.form['nome']
    assunto = request.form['assunto']
    
    novo_protocolo = Protocolo(nome=nome, assunto=assunto)
    db.session.add(novo_protocolo)
    db.session.commit()
    
    flash("Protocolo adicionado com sucesso!", "success")
    return redirect(url_for('index'))

# Excluir protocolo
@app.route('/delete/<int:id>')
def delete(id):
    protocolo = Protocolo.query.get_or_404(id)
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
        print(f"📄 Gerando PDF: {pdf_filename}...")
        c = canvas.Canvas(pdf_filename, pagesize=letter)

        # Adiciona informações ao PDF
        c.drawString(100, 750, f"ID: {protocolo.id}")
        c.drawString(100, 730, f"Nome: {protocolo.nome}")
        c.drawString(100, 710, f"Assunto: {protocolo.assunto}")
        c.drawString(100, 690, f"Data: {protocolo.data_hora.strftime('%d/%m/%Y %H:%M')}")

        # Criar código de barras
        barcode_value = str(protocolo.id)
        barcode = code128.Code128(barcode_value, barHeight=50, barWidth=1.5)
        barcode.drawOn(c, 100, 600)

        # Salva o PDF corretamente
        c.showPage()
        c.save()

        time.sleep(1)  # Aguarda para garantir que o arquivo foi gravado

        if os.path.exists(pdf_filename):
            print(f"✅ PDF gerado com sucesso: {pdf_filename}")
            return True
        else:
            print("⚠ Erro ao gerar o PDF! Arquivo não encontrado.")
            return False
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        return False

# Rota para baixar PDF
@app.route('/print/pdf/<int:id>')
def print_pdf(id):
    protocolo = Protocolo.query.get_or_404(id)
    pdf_filename = os.path.join("static", f"label_{id}.pdf")
    pdf_filename_abs = os.path.abspath(pdf_filename)  # Obtém o caminho absoluto

    if gerar_pdf(protocolo, pdf_filename_abs):
        time.sleep(1)  # Pequena pausa antes de tentar acessar o arquivo

        if os.path.exists(pdf_filename_abs):
            print(f"📂 Enviando PDF para download: {pdf_filename_abs}")
            return send_file(pdf_filename_abs, as_attachment=True, mimetype="application/pdf")
        else:
            flash("Erro: Arquivo PDF não encontrado após a geração!", "danger")
            print("❌ Erro: Arquivo PDF não encontrado após a geração!")
    else:
        flash("Erro ao gerar o PDF!", "danger")
        print("❌ Erro ao gerar o PDF!")

    return redirect(url_for('index'))

# Rota para impressão direta (somente Windows)
@app.route('/print/direct/<int:id>')
def print_direct(id):
    protocolo = Protocolo.query.get_or_404(id)
    pdf_filename = os.path.join("static", f"label_{id}.pdf")
    pdf_filename_abs = os.path.abspath(pdf_filename)

    if gerar_pdf(protocolo, pdf_filename_abs):
        time.sleep(1)  # Pequena pausa antes de tentar imprimir

        if os.path.exists(pdf_filename_abs):
            print(f"🖨 Enviando para impressão: {pdf_filename_abs}")
            try:
                os.startfile(pdf_filename_abs, "print")  # Envia para impressão (Windows)
                flash("Documento enviado para impressão!", "info")
            except Exception as e:
                print(f"❌ Erro ao imprimir: {e}")
                flash(f"Erro ao enviar para impressão: {e}", "danger")
        else:
            flash("Erro: Arquivo PDF não encontrado após a geração!", "danger")
            print("❌ Erro: Arquivo PDF não encontrado após a geração!")
    else:
        flash("Erro ao gerar o PDF para impressão!", "danger")
        print("❌ Erro ao gerar o PDF para impressão!")

    return redirect(url_for('index'))

# Executar o servidor Flask
if __name__ == '__main__':
    app.run(debug=True)
