import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import db

logger = logging.getLogger(__name__)


def get_pedidos() -> list:
    return db.get_pedidos_agrupados()


def get_status() -> dict:
    try:
        with db.cursor() as cur:
            cur.execute("SELECT MAX(coletado_em) AS ultima FROM pedidos_itens")
            row = cur.fetchone()
            ultima = row['ultima'].strftime('%H:%M:%S') if row and row['ultima'] else 'nunca'
    except Exception:
        ultima = 'erro'
    return {
        'pipeline': {
            'estado': 'cron',
            'ultima_atualizacao': ultima,
            'coletando': False,
        }
    }


def iniciar(headless: bool = False):
    logger.info('Scraper: modo banco de dados ativo. Cron alimenta o banco.')


def encerrar():
    pass
