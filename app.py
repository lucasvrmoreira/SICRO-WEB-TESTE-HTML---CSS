from flask import Flask, render_template, request, redirect, flash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = 'chave-secreta-supersegura'

# Conexão com o banco PostgreSQL via Render
def conectar_postgres():
    try:
        url = os.environ.get("DATABASE_URL")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    except Exception as e:
        print("Erro ao conectar ao PostgreSQL:", e)
        raise

# Criação da tabela
def init_db():
    conn = conectar_postgres()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS roupas (
            id SERIAL PRIMARY KEY,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tamanho TEXT NOT NULL,
            lote TEXT,
            validade TEXT,
            quantidade INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/entrada', methods=['GET', 'POST'])
def entrada():
    if request.method == 'POST':
        tipo = request.form['tipo']
        tamanho = request.form.get('tamanho', 'Padrão')
        quantidade = int(request.form['quantidade'])

        estereis = ['macacao azul', 'bota azul', 'oculos', 'panos']
        categoria = 'estéril' if tipo.lower() in estereis else 'não estéril'

        lote = request.form['lote'] if categoria == 'estéril' else None
        validade = request.form['validade'] if categoria == 'estéril' else None

        conn = conectar_postgres()
        c = conn.cursor()

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
                INSERT INTO roupas (tipo, categoria, tamanho, lote, validade, quantidade)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (tipo, categoria, tamanho, lote, validade, quantidade))

        conn.commit()
        conn.close()
        flash("Entrada registrada com sucesso!", "success")
        return redirect('/')

    return render_template('entrada.html')

@app.route('/saida', methods=['GET', 'POST'])
def saida():
    if request.method == 'POST':
        selecionados = request.form.getlist('selecionado')
        if not selecionados:
            flash("Nenhum item foi selecionado.", "warning")
            return redirect('/saida')

        conn = conectar_postgres()
        c = conn.cursor()

        for roupa_id in selecionados:
            try:
                roupa_id = int(roupa_id)
                quantidade = int(request.form.get(f'quantidade_{roupa_id}', 0))

                if quantidade <= 0:
                    continue

                c.execute('UPDATE roupas SET quantidade = quantidade - %s WHERE id = %s', (quantidade, roupa_id))
                c.execute('DELETE FROM roupas WHERE quantidade <= 0')

            except Exception as e:
                flash(f"Erro ao processar o item {roupa_id}: {str(e)}", "danger")

        conn.commit()
        conn.close()
        flash("Saída realizada com sucesso!", "success")
        return redirect('/saida')

    conn = conectar_postgres()
    c = conn.cursor()
    c.execute('SELECT * FROM roupas ORDER BY tipo, tamanho')
    roupas = c.fetchall()
    conn.close()

    roupas_por_tipo = {}
    for r in roupas:
        tipo = r[1]
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = []
        roupas_por_tipo[tipo].append(r)

    return render_template('saida.html', roupas_por_tipo=roupas_por_tipo)

@app.route('/saldo')
def saldo():
    conn = conectar_postgres()
    c = conn.cursor()
    c.execute('SELECT * FROM roupas ORDER BY tipo, tamanho')
    roupas = c.fetchall()
    conn.close()

    roupas_por_tipo = {}
    for r in roupas:
        tipo = r[1]
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = []
        roupas_por_tipo[tipo].append(r)

    return render_template('saldo.html', roupas_por_tipo=roupas_por_tipo)

if __name__ == '__main__':
    app.run(debug=True)
