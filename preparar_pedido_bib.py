#PREPARAR
import os
import json
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

load_dotenv()

# ============================================================
# CREDENCIAIS POR CENTRO
# ============================================================
credenciais = {
    'RIGARR': {
        'email': os.getenv("EMAIL_RIGARR"),
        'senha': os.getenv("SENHA_RIGARR"),
    }
}

url_base = "https://one.bees.com/order-management/active-orders"

with open('pedidos_enviados.json', 'r', encoding='utf-8') as f:
    pedidos = json.load(f)

# ============================================================
# FUNÇÃO SELENIUM
# ============================================================
def baixa(url_base, email, senha, pedidos):
    preparados = []
    driver = webdriver.Chrome()
    driver.set_window_position(1920, 0)  # move para a segunda tela
    driver.maximize_window()
    wait = WebDriverWait(driver, 60)

    # LOGIN
    driver.get(url_base)
    wait.until(lambda d: d.current_url != 'about:blank')


    campo_email = wait.until(EC.element_to_be_clickable((By.ID, 'signInName')))
    campo_email.send_keys(email)

    wait.until(EC.element_to_be_clickable((By.ID, 'next'))).click()

    campo_senha = wait.until(EC.element_to_be_clickable((By.ID, 'password')))
    campo_senha.send_keys(senha)

    wait.until(EC.element_to_be_clickable((By.ID, 'next'))).click()

    try:
        botao_entendi = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[text()="Entendi"]'))
        )
        botao_entendi.click()
    except TimeoutException:
        pass

    # PROCESSAR PEDIDOS
    for pedido in pedidos:
        order_url = f"{url_base}/{pedido}"
        driver.get(order_url)

        try:
            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//*[@id="single-spa-application:@supplier-portal/order-management-beta-mfe"]')
                )
            )

            try:
                driver.find_element(
                    By.XPATH,
                    '//h3[text()="Algo deu errado"]'
                )
                continue
            except:
                pass

            motivo = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//*[@id="single-spa-application:@supplier-portal/order-management-beta-mfe"]/div/div[4]/div[1]/p[2]')
                )
            ).text.strip()

            if motivo in ["A ser preparado", "To be prepared"]:
                try:
                    chips = wait.until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "div[data-testid='chip-container']")
                        )
                    )
                except Exception as e:
                    print(f"Erro ao buscar os chips: {e}")
                    continue

                wait.until(EC.element_to_be_clickable(chips[-1])).click()

                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[text()="Confirmar preparo"]')
                    )
                ).click()

                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[text()="Confirmar"]')
                    )
                ).click()

                preparados.append(pedido)
                print(f"✅ Pedido {pedido} preparado.")
                time.sleep(3)

        except TimeoutException:
            continue

    driver.quit()
    return preparados


# ============================================================
# EXECUÇÃO POR CENTRO
# ============================================================
JSON_FILE = 'pedidos_enviados.json'

if not pedidos:
    print("ℹ️ Nenhum pedido no JSON. Encerrando.")
    exit()

for centro, creds in credenciais.items():
    print(f"Processando centro: {centro}...")
    preparados = baixa(url_base, creds['email'], creds['senha'], pedidos)

    if preparados:
        pedidos = [p for p in pedidos if p not in preparados]
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(pedidos, f, indent=4)
        print(f"🗑️ {len(preparados)} pedido(s) removido(s) do JSON.")

    print(f"Centro {centro} concluído.")
