from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from datetime import datetime

app = Flask(__name__)

# Conexão com o PostgreSQL da Render
conn = psycopg2.connect(
    host="dpg-cvkpk5t6ubrc73fshg00-a.oregon-postgres.render.com",
    database="sicro_db",
    user="sicro_user",
    password="U4JVLkBlxC6YqmSzDN8hrtbgegXm1O4R"
)
c = conn.cursor()

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
        lote = request.form['lote'] if categoria == 'estéril' else None
        validade = request.form['validade'] if categoria == 'estéril' else None
        data_entrada = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
        return redirect(url_for('entrada'))

    return render_template('entrada.html')

@app.route('/saida', methods=['GET', 'POST'])
def saida():
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

        return redirect(url_for('saida'))

    c.execute('SELECT * FROM roupas ORDER BY tipo, tamanho')
    roupas = c.fetchall()
    return render_template('saida.html', roupas=roupas)

@app.route('/saldo')
def saldo():
    c.execute('SELECT * FROM roupas ORDER BY tipo, tamanho')
    roupas = c.fetchall()
    return render_template('saldo.html', roupas=roupas)

if __name__ == '__main__':
    app.run(debug=True)
