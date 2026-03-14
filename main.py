"""
Script principal para automação Bees.

Rotina:
1. Coletar dados dos pedidos a preparar
2. Cancelar pedidos com CPF inválido nos centros de distribuição especificados (apenas se houver pedidos elegíveis)
"""

import subprocess
import sys
import os
import logging
from cancela_cpf import preparar_dados, cancelar_pedidos
import consulta_cnpj

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("Iniciando rotina principal...")

    # Passo 1: Coletar dados
    logging.info("Passo 1: Coletando dados dos pedidos...")
    try:
        result = subprocess.run([sys.executable, 'coletar_pedidos_preparar.py'], check=True)
        logging.info("Coleta de dados concluída com sucesso.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro na coleta de dados: {e}")
        return

    # Verificar se há pedidos elegíveis para cancelamento
    logging.info("Verificando pedidos elegíveis para cancelamento...")
    arquivo = preparar_dados()
    if arquivo.empty:
        logging.info("Nenhum pedido elegível para cancelamento encontrado.")
        return

    # Passo 2: Cancelar CPF
    logging.info(f"Encontrados {len(arquivo)} pedidos elegíveis. Iniciando cancelamento...")
    try:
        cancelar_pedidos(arquivo)
        logging.info("Cancelamento de CPF concluído com sucesso.")
    except Exception as e:
        logging.error(f"Erro no cancelamento de CPF: {e}")
        return

    # Passo 3: Consultar CNPJs
    logging.info("Passo 3: Consultando CNPJs...")
    try:
        consulta_cnpj.consultar_cnpjs()
        logging.info("Consulta de CNPJs concluída com sucesso.")
    except Exception as e:
        logging.error(f"Erro na consulta de CNPJs: {e}")
        return

    logging.info("Rotina principal concluída.")

if __name__ == "__main__":
    main()
