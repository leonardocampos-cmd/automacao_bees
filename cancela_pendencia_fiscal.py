#CNPJ PENDENTE
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import traceback
import db

load_dotenv()
db.criar_tabelas()

cnpj_problemas = db.get_cnpjs_com_problema()
arquivo_cnpj = pd.DataFrame(cnpj_problemas)

if arquivo_cnpj.empty:
    print('Sem pedidos!')
    exit()

todos_pedidos = db.get_todos_pedidos()
arquivo_pedidos = pd.DataFrame(todos_pedidos).rename(columns={
    'numero_pedido':       'Numero Pedido',
    'id_conta_cliente':    'ID da conta do cliente',
})
arquivo_pedidos.drop_duplicates(subset=['Numero Pedido'], inplace=True)

arquivo_cnpj = arquivo_cnpj.merge(
    arquivo_pedidos[['Numero Pedido', 'ID da conta do cliente']],
    left_on='cnpj', right_on='ID da conta do cliente', how='left'
)
arquivo_cnpj = arquivo_cnpj.dropna(subset=['Numero Pedido'])

motivo = 'Cliente com documento inválido'
if arquivo_cnpj.empty:
    print('Sem pedidos!')
else:
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

    for _, row in arquivo_cnpj.iterrows():
        pedido = row['Numero Pedido']
        print(f"Processando pedido {pedido}...")
        try:
            driver.get(f'https://one.bees.com/order-management/active-orders/{pedido}')
            status = wait.until(EC.visibility_of_element_located((
                By.XPATH, '//p[contains(text(),"A ser preparado")]'
            ))).text.strip()
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
            print(f"Pedido {pedido} atualizado com motivo '{motivo}'")

        except Exception as e:
            print(f"Erro no pedido {pedido}: {e}")
            traceback.print_exc()

    driver.quit()
    print("Todos os pedidos processados.")
