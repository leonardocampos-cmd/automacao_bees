#PREPARAR
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import db

load_dotenv()
db.criar_tabelas()

credenciais = {
    'RIGARR': {
        'email': os.getenv("EMAIL_RIGARR"),
        'senha': os.getenv("SENHA_RIGARR"),
    }
}

url_base = "https://one.bees.com/order-management/active-orders"

pedidos = list(db.get_pedidos_enviados())

if not pedidos:
    print("Nenhum pedido enviado aguardando preparo. Encerrando.")
    exit()


def baixa(url_base, email, senha, pedidos):
    preparados = []
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 60)

    driver.get(url_base)
    wait.until(lambda d: d.current_url != 'about:blank')

    wait.until(EC.element_to_be_clickable((By.ID, 'signInName'))).send_keys(email)
    wait.until(EC.element_to_be_clickable((By.ID, 'next'))).click()
    wait.until(EC.element_to_be_clickable((By.ID, 'password'))).send_keys(senha)
    wait.until(EC.element_to_be_clickable((By.ID, 'next'))).click()
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Entendi"]'))).click()
    except TimeoutException:
        pass

    for pedido in pedidos:
        order_url = f"{url_base}/{pedido}"
        driver.get(order_url)
        try:
            wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="single-spa-application:@supplier-portal/order-management-beta-mfe"]')
            ))
            try:
                driver.find_element(By.XPATH, '//h3[text()="Algo deu errado"]')
                continue
            except:
                pass

            motivo = wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="single-spa-application:@supplier-portal/order-management-beta-mfe"]/div/div[4]/div[1]/p[2]')
            )).text.strip()

            if motivo in ["A ser preparado", "To be prepared"]:
                try:
                    chips = wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div[data-testid='chip-container']")
                    ))
                except Exception as e:
                    print(f"Erro ao buscar os chips: {e}")
                    continue

                wait.until(EC.element_to_be_clickable(chips[-1])).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//button[text()="Confirmar preparo"]')
                )).click()
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//button[text()="Confirmar"]')
                )).click()

                preparados.append(pedido)
                print(f"Pedido {pedido} preparado.")
                time.sleep(3)

        except TimeoutException:
            continue

    driver.quit()
    return preparados


for centro, creds in credenciais.items():
    print(f"Processando centro: {centro}...")
    preparados = baixa(url_base, creds['email'], creds['senha'], pedidos)

    if preparados:
        for p in preparados:
            db.deletar_pedido_enviado(p)
        print(f"{len(preparados)} pedido(s) removido(s) da fila.")

    print(f"Centro {centro} concluído.")
