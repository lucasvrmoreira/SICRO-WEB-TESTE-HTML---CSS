from flask import Flask, flash, render_template, request, redirect, url_for
import psycopg2
from datetime import datetime
import os
import json
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, flash, render_template, request, redirect, url_for, jsonify
from datetime import date
import secrets



app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Função para obter conexão segura com o banco
def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

@app.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ordens WHERE status = 'pendente'")
    total_pendentes = c.fetchone()[0]
    conn.close()
    return render_template('index.html', total_pendentes=total_pendentes)


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


# 3. Atualizar rota /saida com base no numero_ordem
@app.route('/saida', methods=['GET', 'POST'])
def saida():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        numero_ordem = request.form.get('numero_ordem')
        if not numero_ordem:
            flash("Número da ordem não encontrado.", "danger")
            return redirect(url_for('ordens'))

        tipos = request.form.getlist('tipo[]')
        tamanhos = request.form.getlist('tamanho[]')
        lotes = request.form.getlist('lote[]')
        quantidades = request.form.getlist('quantidade[]')

        for i in range(len(tipos)):
            # Atualiza estoque
            cur.execute("""
                UPDATE roupas
                SET quantidade = quantidade - %s
                WHERE tipo = %s AND tamanho = %s AND lote = %s
            """, (quantidades[i], tipos[i], tamanhos[i], lotes[i]))

            # Verifica validade da roupa
            cur.execute("""
                SELECT validade FROM roupas
                WHERE tipo = %s AND tamanho = %s AND lote = %s
            """, (tipos[i], tamanhos[i], lotes[i]))
            validade = cur.fetchone()
            validade = validade[0] if validade else None

            # Insere no histórico de saída
            cur.execute("""
                INSERT INTO saidas (numero_ordem, tipo, tamanho, lote, validade, quantidade)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (numero_ordem, tipos[i], tamanhos[i], lotes[i], validade, quantidades[i]))

            # Remove do estoque se zerar
            cur.execute("""
                SELECT quantidade FROM roupas
                WHERE tipo = %s AND tamanho = %s AND lote = %s
            """, (tipos[i], tamanhos[i], lotes[i]))
            restante = cur.fetchone()

            if restante and restante[0] <= 0:
                cur.execute("""
                    DELETE FROM roupas
                    WHERE tipo = %s AND tamanho = %s AND lote = %s
                """, (tipos[i], tamanhos[i], lotes[i]))

        # Atualiza o status da ordem
        cur.execute("""
            UPDATE ordens
            SET status = 'atendido'
            WHERE numero_ordem = %s
        """, (numero_ordem,))

        conn.commit()
        conn.close()

        flash("Ordem atendida com sucesso!", "success")
        return redirect(url_for('index'))

    # GET request
    numero_ordem = request.args.get('numero_ordem')
    if not numero_ordem:
        flash("Número da ordem não encontrado.", "danger")
        return redirect(url_for('ordens'))

    # Consulta as solicitações da ordem
    cur.execute("""
        SELECT tipo, tamanho, quantidade FROM ordens
        WHERE numero_ordem = %s
    """, (numero_ordem,))
    rows = cur.fetchall()

    if not rows:
        flash("Número da ordem não encontrado.", "danger")
        return redirect(url_for('ordens'))

    solicitacao = [{'tipo': r[0], 'tamanho': r[1], 'quantidade': r[2]} for r in rows]

    # Consulta o estoque completo
    cur.execute("SELECT tipo, tamanho, lote, validade, quantidade FROM roupas")
    rows = cur.fetchall()
    roupas = [{
        'tipo': r[0],
        'tamanho': r[1],
        'lote': r[2],
        'validade': r[3].strftime('%Y-%m-%d') if r[3] else '',
        'quantidade': r[4]
    } for r in rows]

    tipos_unicos = sorted(set([r['tipo'] for r in roupas]))
    conn.close()

    return render_template('saida.html', roupas=roupas, tipos=tipos_unicos, solicitacao=solicitacao, numero_ordem=numero_ordem)


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



@app.route('/confirmar_saida', methods=['POST'])
def confirmar_saida():
    itens = json.loads(request.form['itens'])
    conn = get_db_connection()
    cur = conn.cursor()

    for item in itens:
        cur.execute("""
            SELECT quantidade FROM roupas
            WHERE id = %s
        """, (item['id'],))
        atual = cur.fetchone()

        if atual and atual[0] >= item['quantidade']:
            nova_qtd = atual[0] - item['quantidade']

            if nova_qtd == 0:
                # Se zerou, remove o item do banco
                cur.execute("DELETE FROM roupas WHERE id = %s", (item['id'],))
            else:
                # Senão, apenas atualiza a quantidade
                cur.execute("UPDATE roupas SET quantidade = %s WHERE id = %s", (nova_qtd, item['id']))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('saida'))


# Rotas da Produção


# 1. Backend da tela de solicitação de roupas (produção)
@app.route('/solicitar', methods=['GET', 'POST'])
def solicitar():
    conn = get_db_connection()
    cur = conn.cursor()

    # Monta dicionário com saldos por tipo e tamanho
    cur.execute("SELECT tipo, tamanho, SUM(quantidade) FROM roupas GROUP BY tipo, tamanho")
    rows = cur.fetchall()

    roupas_por_tipo = {}
    for tipo, tamanho, quantidade in rows:
        if tipo not in roupas_por_tipo:
            roupas_por_tipo[tipo] = {}
        roupas_por_tipo[tipo][tamanho] = quantidade

    if request.method == 'POST':
        solicitacoes = request.get_json()
        if not solicitacoes:
            return jsonify({'status': 'error', 'message': 'Solicitações vazias'}), 400

        # Obtem o maior número de ordem atual e soma 1
        cur.execute("SELECT MAX(CAST(numero_ordem AS INTEGER)) FROM ordens")
        ultimo = cur.fetchone()[0]
        novo_numero = (int(ultimo) + 1) if ultimo else 1
        numero_ordem = str(novo_numero)

        for item in solicitacoes:
            cur.execute("""
                INSERT INTO ordens (tipo, tamanho, quantidade, categoria, status, data_solicitacao, numero_ordem)
                VALUES (%s, %s, %s, %s, 'pendente', %s, %s)
            """, (
                item['tipo'],
                item['tamanho'],
                item['quantidade'],
                item['categoria'],
                date.today(),
                numero_ordem
            ))

        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

    conn.close()
    return render_template('solicitar.html', roupas_por_tipo=roupas_por_tipo)



# 2. Tela de Ordens Pendentes
@app.route('/ordens')
def ordens():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT numero_ordem, SUM(quantidade), MAX(data_solicitacao)
        FROM ordens
        WHERE status = 'pendente'
        GROUP BY numero_ordem
        ORDER BY MAX(data_solicitacao) DESC
    """)
    
    ordens = cur.fetchall()
    conn.close()
    return render_template('ordens.html', ordens=ordens)


# Rota: API – Retorna saldo por tipo
@app.route('/api/saldo/<tipo>')
def saldo_por_tipo(tipo):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(quantidade) FROM roupas WHERE tipo = %s", (tipo,))
    total = cur.fetchone()[0] or 0
    conn.close()
    return {'saldo': total}

@app.route('/api/saldo_por_tamanho/<tipo>')
def saldo_por_tamanho(tipo):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT tamanho, SUM(quantidade)
        FROM roupas
        WHERE tipo = %s
        GROUP BY tamanho
        ORDER BY tamanho
    """, (tipo,))
    rows = cur.fetchall()
    conn.close()

    return {t[0]: t[1] for t in rows}

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    return value.strftime(format)


@app.route('/ordens_atendidas')
def ordens_atendidas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT numero_ordem, SUM(quantidade), MAX(data_solicitacao)
        FROM ordens
        WHERE status = 'atendido'
        GROUP BY numero_ordem
        ORDER BY MAX(data_solicitacao) DESC
    """)
    ordens = cur.fetchall()
    conn.close()
    return render_template('ordens_atendidas.html', ordens=ordens)


@app.route('/ordem/<numero_ordem>')
def detalhes_ordem(numero_ordem):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT tipo, tamanho, lote, validade, quantidade, data_saida
        FROM saidas
        WHERE numero_ordem = %s
    """, (numero_ordem,))
    detalhes = cur.fetchall()
    conn.close()

    return render_template('detalhes_ordem.html', numero_ordem=numero_ordem, detalhes=detalhes)


if __name__ == '__main__':
    app.run(debug=True)
