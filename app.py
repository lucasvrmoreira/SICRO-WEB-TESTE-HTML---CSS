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
        lote = request.form['lote']
        validade_str = request.form['validade']
        validade = datetime.strptime(validade_str, '%Y-%m-%d').date() if validade_str else None
        data_entrada = datetime.now().date()

        conn = get_db_connection()
        c = conn.cursor()

        # Verifica se já existe uma roupa com os mesmos dados
        c.execute('''
            SELECT id FROM roupas
            WHERE tipo = %s AND tamanho = %s AND categoria = %s AND lote = %s AND validade = %s
        ''', (tipo, tamanho, categoria, lote, validade))
        existente = c.fetchone()

        if existente:
            # Se já existe, apenas atualiza a quantidade
            c.execute('''
                UPDATE roupas
                SET quantidade = quantidade + %s
                WHERE id = %s
            ''', (quantidade, existente[0]))
        else:
            # Caso contrário, insere nova linha
            c.execute('''
                INSERT INTO roupas (tipo, tamanho, categoria, lote, validade, quantidade, data_entrada)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (tipo, tamanho, categoria, lote, validade, quantidade, data_entrada))

        conn.commit()
        conn.close()
        return redirect('/')

    return render_template('entrada.html')


@app.route('/saida', methods=['GET'])
def saida():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, tipo, tamanho, lote, validade, quantidade FROM roupas ORDER BY tipo")
    roupas = c.fetchall()
    roupas_por_tipo = {}

    for r in roupas:
        tipo = r[1]
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = []
        roupas_por_tipo[tipo].append({
            'id': r[0],
            'tipo': r[1],
            'tamanho': r[2],
            'lote': r[3] or '-',
            'validade': r[4].strftime('%d/%m/%Y') if r[4] else '-',
            'quantidade': r[5]
        })

    return render_template('saida.html', roupas_por_tipo=roupas_por_tipo, roupas=roupas_por_tipo)



@app.route('/saldo')
def saldo():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tipo, tamanho, categoria, lote, validade, quantidade, data_entrada FROM roupas ORDER BY tipo, tamanho")
    roupas = c.fetchall()
    conn.close()

    roupas_por_tipo = {}
    for r in roupas:
        tipo = r[0]
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = []
        roupas_por_tipo[tipo].append({
            'tamanho': r[1],
            'categoria': r[2],
            'lote': r[3] if r[3] else '-',
            'validade': r[4].strftime('%d/%m/%Y') if r[4] else '-',
            'quantidade': r[5],
            'data_entrada': r[6].strftime('%d/%m/%Y') if r[6] else '-'
        })

    return render_template('saldo.html', roupas_por_tipo=roupas_por_tipo)


    conn.close()
    return render_template('saldo.html', roupas_por_tipo=roupas_por_tipo)

@app.route('/confirmar_saida', methods=['POST'])
def confirmar_saida():
    itens = request.form.get('itens')
    if itens:
        import json
        roupas = json.loads(itens)

        conn = get_db_connection()
        c = conn.cursor()

        for roupa in roupas:
            c.execute('''
                UPDATE roupas
                SET quantidade = quantidade - %s
                WHERE id = %s AND quantidade >= %s
            ''', (roupa['quantidade'], roupa['id'], roupa['quantidade']))

        conn.commit()
        conn.close()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
