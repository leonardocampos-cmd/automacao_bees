import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

url = "https://one.bees.com/order-management/active-orders"

def login(driver, wait, email, senha):
    """Realiza o login no site do Bees."""
    logging.info("Tentando realizar o login...")
    driver.get(url)
    campo_email = wait.until(EC.element_to_be_clickable(('id', 'signInName')))
    campo_email.send_keys(email)
    botao_continue = wait.until(EC.element_to_be_clickable(('id', 'next')))
    botao_continue.click()
    campo_senha = wait.until(EC.element_to_be_clickable(('id', 'password')))
    campo_senha.send_keys(senha)
    botao_continue = wait.until(EC.element_to_be_clickable(('id', 'next')))
    botao_continue.click()
    try:
        botao_entendi = wait.until(EC.element_to_be_clickable(('xpath', '//button[text()="Entendi"]')))
        botao_entendi.click()
    except Exception:
        time.sleep(5)
    logging.info("Login realizado com sucesso.")