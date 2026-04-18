#CANCELA CPF
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
import traceback
import db

load_dotenv()
db.criar_tabelas()

todos = db.get_todos_pedidos()
arquivo = pd.DataFrame(todos).rename(columns={
    'numero_pedido':       'Numero Pedido',
    'centro_distribuicao': 'Centro de Distribuição',
    'documento':           'Documento',
    'forma_pagamento':     'Forma de Pagamento',
    'total_pedido':        'Total Pedido',
    'nome_comercial':      'Nome Comercial',
    'responsavel':         'Responsavel',
})

if arquivo.empty or 'Centro de Distribuição' not in arquivo.columns:
    print('Sem pedidos!')
    exit(0)
arquivo = arquivo[arquivo['Centro de Distribuição'].isin(['CASTAS SP', 'RIGARRSPCAPITAL', 'CASTAS RJ', 'RIGARRRJCAPITAL'])]
arquivo = arquivo[arquivo['Documento'].str.contains('CPF', na=False)]
arquivo.drop_duplicates(subset=['Numero Pedido'], inplace=True)

if arquivo.empty:
    print('Sem pedidos!')
else:
    motivo = 'Cliente com documento inválido'
    pedidos_cancelados = []

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 60)

    driver.get('https://one.bees.com/order-management/active-orders/')
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="signInName"]'))).send_keys('leonardo.campos@rigarr.com.br')
    driver.find_element(By.XPATH, '//*[@id="next"]').click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password"]'))).send_keys('Br@sil32aaaaaaa')
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="next"]'))).click()
    try:
        wait.until(EC.element_to_be_clickable(('xpath', '//button[text()="Entendi"]'))).click()
    except Exception:
        time.sleep(5)

    for _, row in arquivo.iterrows():
        pedido = row['Numero Pedido']
        print(f"Processando pedido {pedido}...")
        try:
            driver.get(f'https://one.bees.com/order-management/active-orders/{pedido}')
            try:
                status = wait.until(EC.visibility_of_element_located((
                    By.XPATH, '//p[contains(text(),"A ser preparado") or contains(text(),"To be prepared")]'
                ))).text.strip()
            except TimeoutException:
                print(f"Pedido {pedido} não está 'A ser preparado'. Pulando.")
                continue
            time.sleep(2)
            if status != "A ser preparado":
                print(f"Pedido {pedido} status: {status}")
                continue

            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Recusar pedido"]'))).click()
            combobox_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]')
            ))
            combobox_btn.click()
            wait.until(lambda d: d.find_element(By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]').get_attribute("aria-expanded") == "true")

            motivos = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@role="option"]')))
            motivo_encontrado = False
            for m in motivos:
                if m.text.strip() == motivo:
                    ActionChains(driver).move_to_element(m).click().perform()
                    motivo_encontrado = True
                    break
            if not motivo_encontrado:
                print(f"Motivo '{motivo}' não encontrado para o pedido {pedido}")
                continue

            wait.until(lambda d: d.find_element(By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]').get_attribute("aria-expanded") == "false")
            confirmar_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@data-testid="modal-confirm-button"]')
            ))
            ActionChains(driver).move_to_element(confirmar_btn).click().perform()

            pedidos_cancelados.append(pedido)
            print(f"Pedido {pedido} cancelado com motivo '{motivo}'")

        except TimeoutException as e:
            print(f"Erro no pedido {pedido}: {e}")
            traceback.print_exc()
            time.sleep(5)

    driver.quit()

    if pedidos_cancelados:
        for numero in pedidos_cancelados:
            db.deletar_pedido_por_numero(numero)
        print(f"{len(pedidos_cancelados)} pedido(s) removido(s) do banco.")

    print("Todos os pedidos processados.")
