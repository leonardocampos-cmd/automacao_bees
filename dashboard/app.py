import os
import logging
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

import scraper

app = Flask(__name__)

HEADLESS = os.getenv('SCRAPER_HEADLESS', 'false').lower() == 'true'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/pedidos')
def api_pedidos():
    pedidos = scraper.get_pedidos()
    return jsonify(pedidos)


@app.route('/api/pedidos/<numero>')
def api_pedido_detalhe(numero):
    for p in scraper.get_pedidos():
        if str(p.get('Numero Pedido', '')).strip() == str(numero):
            return jsonify(p)
    return jsonify({'erro': 'Pedido não encontrado'}), 404


@app.route('/api/stats')
def api_stats():
    pedidos = scraper.get_pedidos()
    total = len(pedidos)
    valor_total = 0.0
    por_filial = {}

    for p in pedidos:
        filial = p.get('filial', 'Desconhecida')
        por_filial[filial] = por_filial.get(filial, 0) + 1

        val_str = (p.get('Total Pedido') or '').replace('$', '').replace('.', '').replace(',', '.').strip()
        try:
            valor_total += float(val_str)
        except ValueError:
            pass

    return jsonify({'total': total, 'valor_total': valor_total, 'por_filial': por_filial})


@app.route('/api/status')
def api_status():
    return jsonify(scraper.get_status())


@app.route('/api/debug')
def api_debug():
    pedidos = scraper.get_pedidos()
    return jsonify({
        'total_na_memoria': len(pedidos),
        'numeros': [p.get('Numero Pedido') for p in pedidos],
        'status': scraper.get_status(),
    })


if __name__ == '__main__':
    import atexit
    scraper.iniciar(headless=HEADLESS)
    atexit.register(scraper.encerrar)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
