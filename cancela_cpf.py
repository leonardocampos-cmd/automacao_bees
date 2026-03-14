#CANCELAR CPF
import pandas as pd
import os
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import traceback
from dotenv import load_dotenv
from login import login

load_dotenv()

def preparar_dados():
    pasta = 'relatorios'
    arquivos = [f for f in os.listdir(pasta) if f.endswith('.csv') and 'Pedidos_A_Preparar_' in f]
    lista_arquivos = [pd.read_csv(os.path.join(pasta,f),dtype=str) for f in arquivos]
    arquivo = pd.concat(lista_arquivos,ignore_index=True)
    colunas_descartar = [
        'Data Pedido', 'Status', 'Data Entrega', 'Responsavel', 'CEP',
        'Coordenadas', 'ID do negócio', 'ID da conta do cliente', 'IE',
        'Quantidade Preparar', 'Email 1', 'Email 2'
    ]      
    arquivo.drop(columns=colunas_descartar, inplace=True, errors='ignore')
    arquivo = arquivo[arquivo['Centro de Distribuição'].isin(['RIGARRRJCAPITAL', 'RIGARRSPCAPITAL', 'CASTASSP', 'CASTASRJ'])]
    arquivo = arquivo[arquivo['Documento'].str.contains('CPF')]
    arquivo.drop_duplicates(subset=['Numero Pedido'],inplace=True)
    return arquivo

def cancelar_pedidos(arquivo):
    motivo = 'Cliente com documento inválido'

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)  

    # --- Login ---
    email = os.getenv('EMAIL_CANCEL')
    senha = os.getenv('SENHA_CANCEL')
    login(driver, wait, email, senha)

    # --- Itera pelos pedidos ---
    for _, row in arquivo.iterrows():
        pedido = row['Numero Pedido']
        print(f"🔍 Processando pedido {pedido}...")

        try:
            driver.get(f'https://one.bees.com/order-management/active-orders/{pedido}')

            # --- Espera status ---
            status = wait.until(EC.visibility_of_element_located((
                By.XPATH, '//p[contains(text(),"A ser preparado")]'
            ))).text.strip()
            time.sleep(2)  # Pequena pausa para garantir que a página carregou completamente
            if status != "A ser preparado":
                print(f"⚠️ Pedido {pedido} não está 'A ser preparado'. Status atual: {status}")
                continue

            # --- Clica em "Recusar pedido" ---
            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Recusar pedido"]'))).click()

            # --- Abre o combobox de motivos ---
            combobox_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]')
            ))
            combobox_btn.click()

            # Aguarda o combobox expandir
            wait.until(lambda d: d.find_element(By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]').get_attribute("aria-expanded") == "true")

            # --- Seleciona o motivo correto ---
            motivos = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@role="option"]')))
            motivo_encontrado = False
            for m in motivos:
                if m.text.strip() == motivo:
                    # Move o mouse até o elemento e clica (evita o ElementClickIntercepted)
                    ActionChains(driver).move_to_element(m).click().perform() 
                    motivo_encontrado = True
                    break
            if not motivo_encontrado:
                print(f"❌ Motivo '{motivo}' não encontrado para o pedido {pedido}")
                continue

            # Aguarda o combobox fechar
            wait.until(lambda d: d.find_element(By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]').get_attribute("aria-expanded") == "false")

            # --- Aguarda modal de confirmação ---
            confirmar_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@data-testid="modal-confirm-button"]')
            ))

            # --- Clica no botão confirmar ---
            ActionChains(driver).move_to_element(confirmar_btn).click().perform()

            print(f"✅ Pedido {pedido} atualizado com motivo '{motivo}'")

        except Exception as e:
            print(f"❌ Erro no pedido {pedido}: {e}")
            traceback.print_exc()

    # --- Fecha navegador ao final ---
    driver.quit()
    print("✅ Todos os pedidos processados.")

if __name__ == "__main__":
    arquivo = preparar_dados()
    cancelar_pedidos(arquivo)