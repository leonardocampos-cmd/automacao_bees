#CNPJ PENDENTE
import pandas as pd
import os
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import traceback

def executar_cancelamento_fiscal():
    arquivo_cnpj = pd.read_csv(r'C:\HBox\MEU DRIVE\BEES\resultados_consulta_cnpj_api.csv',dtype=str)
    arquivo_cnpj.drop(columns=['Arquivo', 'Nome', 'Nome Fantasia', 'Capital Social',
        'Natureza Jurídica', 'Tamanho', 'Data de Fundação', 
        'Data de Status', 'Razão de Status', 'Rua', 'Número', 'Complemento',
        'Bairro', 'Cidade/UF', 'CEP', 'País', 'Telefone', 'Email',
        'Atividade Principal', 'Atividades Secundárias',
        'Simples Nacional Optante', 'Simples Nacional Desde', 'SIMEI Optante',
        'SIMEI Desde', 'Inscrição Estadual Estado', 'Inscrição Estadual Número',
        'Inscrição Estadual Tipo',
        'Inscrição Estadual Data de Status'],inplace=True)

    arquivo_cnpj = arquivo_cnpj[(arquivo_cnpj['Status'] !='Ativa' ) | (~arquivo_cnpj['Inscrição Estadual Status'].isin(['Sem restrição','Não encontrada']))]

    pasta = r'C:\HBox\MEU DRIVE\BEES'
    arquivos = [f for f in os.listdir(pasta) if f.endswith('.csv') and 'Pedidos_A_Preparar_' in f]
    lista_arquivos = [pd.read_csv(os.path.join(pasta,f),dtype=str) for f in arquivos]
    arquivo_pedidos = pd.concat(lista_arquivos,ignore_index=True)
    colunas_descartar = [
        'Data Pedido', 'Status', 'Data Entrega', 'Responsavel', 'CEP',
        'Coordenadas', 'ID do negócio', 'IE',
        'Quantidade Preparar', 'Email 1', 'Email 2','Centro de Distribuição', 'Forma de Pagamento',
        'Total Pedido', 'Documento', 'Nome Comercial', 'Endereço de Entrega',
        'Cidade/UF', 'SKU', 'Preço', 'Quantidade Pedida', 'Nome do Produto',
        'Telefone 1', 'Telefone 2']
    arquivo_pedidos.drop(columns=colunas_descartar, inplace=True, errors='ignore')
    arquivo_pedidos.drop_duplicates(subset=['Numero Pedido'],inplace=True)
    arquivo_cnpj['CNPJ'] = arquivo_cnpj['CNPJ'].astype(str)
    arquivo_cnpj = arquivo_cnpj.merge(arquivo_pedidos,right_on='ID da conta do cliente',left_on='CNPJ',how='left')

    motivo = 'Cliente com documento inválido'

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.minimize_window()
    wait = WebDriverWait(driver, 60)  

    # --- Login ---
    driver.get('https://one.bees.com/order-management/active-orders/')
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="signInName"]'))).send_keys('leonardo.campos@rigarr.com.br')
    driver.find_element(By.XPATH, '//*[@id="next"]').click()

    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password"]'))).send_keys('Br@sil32aaaaaaa')
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="next"]'))).click()

    # Clica no "Entendi" se aparecer
    try:
        botao_entendi = wait.until(EC.element_to_be_clickable(('xpath', '//button[text()="Entendi"]')))
        botao_entendi.click()
    except Exception:
        time.sleep(5)
    # --- Itera pelos pedidos ---
    for _, row in arquivo_cnpj.iterrows():
        pedido = row['Numero Pedido']
        motivo = motivo
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

            # --- Clica em "Falha na entrega" ---
            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Recusar pedido"]'))).click()

            # --- Abre o combobox de motivos ---
            combobox_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]')
            ))
            combobox_btn.click()

            # Aguarda o combobox expandir
            wait.until(lambda d: d.find_element(By.XPATH, '//button[@role="combobox" and @data-testid="reason-select-combobox"]').get_attribute("aria-expanded") == "true")

            # --- Seleciona o motivo correto ---
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