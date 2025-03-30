from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from datetime import datetime
import os

app = Flask(__name__)

# Função para obter conexão segura com o banco
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/entrada', methods=['GET', 'POST'])
def entrada():
    if request.method == 'POST':
        tipo = request.form['tipo']
        tamanho = request.form['tamanho']
        categoria = request.form['categoria']
        quantidade = int(request.form['quantidade'])
        lote = request.form['lote'] if categoria == 'estéril' and request.form['lote'] else None
        validade = request.form['validade'] if categoria == 'estéril' and request.form['validade'] else None
        data_entrada = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()
        c = conn.cursor()

        # Verifica se a roupa já existe
        c.execute('''
            SELECT id FROM roupas WHERE tipo=%s AND tamanho=%s AND lote=%s AND validade=%s
        ''', (tipo, tamanho, lote, validade))
        result = c.fetchone()

        if result:
            c.execute('''
                UPDATE roupas SET quantidade = quantidade + %s WHERE id = %s
            ''', (quantidade, result[0]))
        else:
            c.execute('''
                INSERT INTO roupas (tipo, tamanho, categoria, quantidade, lote, validade, data_entrada)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (tipo, tamanho, categoria, quantidade, lote, validade, data_entrada))

        conn.commit()
        conn.close()
        return redirect(url_for('entrada'))

    return render_template('entrada.html')

@app.route('/saida', methods=['GET', 'POST'])
def saida():
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        id_roupa = int(request.form['id'])
        quantidade_saida = int(request.form['quantidade'])

        c.execute('SELECT quantidade FROM roupas WHERE id = %s', (id_roupa,))
        result = c.fetchone()

        if result and result[0] >= quantidade_saida:
            nova_quantidade = result[0] - quantidade_saida
            if nova_quantidade == 0:
                c.execute('DELETE FROM roupas WHERE id = %s', (id_roupa,))
            else:
                c.execute('UPDATE roupas SET quantidade = %s WHERE id = %s', (nova_quantidade, id_roupa))

        conn.commit()
        conn.close()
        return redirect(url_for('saida'))

    c.execute('SELECT * FROM roupas ORDER BY tipo, tamanho')
    roupas = c.fetchall()
    conn.close()
    return render_template('saida.html', roupas=roupas)

@app.route('/saldo')
def saldo():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT * FROM roupas')
    roupas = c.fetchall()

    roupas_por_tipo = {}
    for r in roupas:
        tipo = r[1]
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = []

        roupas_por_tipo[tipo].append({
            'tamanho': r[2] or '-',
            'lote': r[4] or '-',
            'validade': r[5].strftime('%d/%m/%Y') if r[5] else '-',
            'quantidade': r[3] or 0,
            'data_entrada': r[6].strftime('%d/%m/%Y %H:%M') if r[6] else '-'
        })

    conn.close()
    return render_template('saldo.html', roupas_por_tipo=roupas_por_tipo)



if __name__ == '__main__':
    app.run(debug=True)
