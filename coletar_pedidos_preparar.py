#COLETAR OS DADOS
from selenium import webdriver
import pandas as pd
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

os.makedirs('relatorios', exist_ok=True)

from login import login

def coletar_dados_pedidos(driver, wait):
    order_data = []
    try:
        tbody = wait.until(
            EC.presence_of_element_located((By.XPATH, '//tbody[@role="rowgroup"]'))
        )
        for tr in tbody.find_elements(By.XPATH, './/tr'):
            try:
                order = tr.find_elements(By.XPATH, './/td[1]')[0].text.strip()
                data_pedido = tr.find_elements(By.XPATH, './/td[2]')[0].text.strip()
                data_entrega = tr.find_elements(By.XPATH, './/td[3]')[0].text.strip()
                responsavel = tr.find_elements(By.XPATH, './/td[4]')[0].text.strip()
                total_pedido = tr.find_elements(By.XPATH, './/td[5]')[0].text.strip()
                order_data.append({
                    'Numero Pedido': order,
                    'Data Pedido': data_pedido,
                    'Data Entrega': data_entrega,
                    'Responsavel': responsavel,
                    'Total Pedido': total_pedido
                })
            except IndexError:
                continue
    except Exception as e:
        pass
    return pd.DataFrame(order_data)

def navegar_paginas(driver, wait):
    """Navega por todas as páginas de pedidos e coleta os dados."""
    logging.info("Navegando pelas páginas de pedidos...")
    page_number = 1
    df_total = pd.DataFrame()

    while True:
        try:
            df = coletar_dados_pedidos(driver, wait)
            df_total = pd.concat([df_total, df], ignore_index=True)
            page_xpath = f'//li[@title="page {page_number}"]'
            try:
                next_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, page_xpath))
                )
                next_button.click()
                logging.info(f"Clicando no elemento da página {page_number} para avançar.")

                wait.until(
                    EC.presence_of_element_located((By.XPATH, '//tbody[@role="rowgroup"]'))
                )
                page_number += 1
                time.sleep(2)   

            except Exception as e:
                logging.info(f"Não há mais páginas ou o botão de navegação.")
                break

        except Exception as e:
            logging.error(f"Ocorreu um erro ao coletar dados ou na navegação geral: {e}")
            break

    return df_total

def coletar_detalhes(driver, wait, df_pedidos_ativos, pedidos_existentes, filial, max_retries=3):
    detalhes = []
    pedidos_processados = set()

    for index, row_lista in df_pedidos_ativos.iterrows():
        order_str = str(row_lista['Numero Pedido'])
        if order_str in pedidos_processados or order_str in pedidos_existentes:
            continue

        logging.info(f"==> Extraindo Detalhes (Seletores Específicos): {order_str}")
        retries = 0
        while retries < max_retries:
            try:
                driver.get(f'https://one.bees.com/order-management/active-orders/{order_str}')
                
                # Espera o carregamento dos itens da tabela
                wait.until(EC.presence_of_element_located((By.XPATH, "//table//tr")))
                
                # 1. Captura do Centro de Distribuição (usando data-testid e classe normal)
                try:
                    cd_elem = driver.find_element(By.XPATH, "//*[@data-testid='order-details-ddc-info']//*[contains(@class, '-weight-normal')]")
                    cd = cd_elem.text.strip()
                except:
                    cd = row_lista.get('Centro de Distribuição')

                # 2. Captura do Status
                try:
                    status_elem = driver.find_element(By.XPATH, "//*[@data-testid='order-details-status']")
                    status = status_elem.text.strip()
                except:
                    status = row_lista.get('Status')

                # 3. Captura do Endereço (Seletor da div c-jJgXmn)
                # Esperamos até que o texto não seja o placeholder de carregamento
                try:
                    xpath_end = "//div[@class='c-jJgXmn']"
                    wait.until(lambda d: "Selecione a data" not in d.find_element(By.XPATH, xpath_end).text)
                    endereco_full = driver.find_element(By.XPATH, xpath_end).text.strip()
                except:
                    endereco_full = "Não capturado"

                # 4. Parsing de Endereço, Cidade, CEP e Coordenadas
                cidade, cep, coords = "", "", ""
                if endereco_full and endereco_full != "Não capturado":
                    # Busca CEP (00000-000)
                    match_cep = re.search(r'\d{5}-?\d{3}', endereco_full)
                    if match_cep: cep = match_cep.group()
                    
                    # Busca Coordenadas (Latitude/Longitude costumam ter o padrão -00.000, -00.000)
                    match_coords = re.search(r'(-?\d{1,2}\.\d+,\s*-?\d{1,2}\.\d+)', endereco_full)
                    if match_coords: coords = match_coords.group()

                    # Separa Cidade/UF (Geralmente a penúltima parte antes da sigla do estado)
                    partes = [p.strip() for p in endereco_full.split(',')]
                    if len(partes) >= 3:
                        # Pega o item que contém o nome da cidade (normalmente antes de MG, SP, etc)
                        cidade = partes[-2] if len(partes[-1]) <= 3 else partes[-1]

                # 5. Captura de ID Negócio / Documento / Cliente (Via classes semibold/normal)
                def capturar_por_labels_bees(label_text):
                    try:
                        xpath = f"//*[contains(@class, '-weight-semibold') and contains(text(), '{label_text}')]/parent::div//*[contains(@class, '-weight-normal')]"
                        return driver.find_element(By.XPATH, xpath).text.strip()
                    except: return None

                documento = capturar_por_labels_bees("Tax ID") or capturar_por_labels_bees("CPF")
                id_negocio = capturar_por_labels_bees("ID do negócio")
                id_conta = capturar_por_labels_bees("ID da conta do cliente")
                forma_pgto = capturar_por_labels_bees("pagamento") or row_lista.get('Forma de Pagamento')

                # 6. Itens do Pedido
                rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) < 3: continue

                        # Detalhes do Produto (Nome, SKU e Preço na primeira célula)
                        linhas_prod = cols[0].text.split('\n')
                        nome_prod = linhas_prod[0]
                        sku_item = next((s.replace("SKU: ", "").strip() for s in linhas_prod if "SKU" in s), "")
                        preco_un = next((p.strip() for p in linhas_prod if "$" in p or "R$" in p), "0.00")

                        detalhes.append({
                            "Numero Pedido": order_str,
                            "Data Pedido": row_lista.get('Data Pedido'),
                            "Centro de Distribuição": cd,
                            "Status": status,
                            "Forma de Pagamento": forma_pgto,
                            "Data Entrega": row_lista.get('Data Entrega'),
                            "Responsavel": row_lista.get('Responsavel'),
                            "Total Pedido": row_lista.get('Total Pedido'),
                            "Documento": documento,
                            "IE": capturar_por_labels_bees("Inscrição"),
                            "Nome Comercial": row_lista.get('Nome Comercial'),
                            "Endereço de Entrega": endereco_full,
                            "Cidade/UF": cidade,
                            "CEP": cep,
                            "Coordenadas": coords,
                            "ID do negócio": id_negocio,
                            "ID da conta do cliente": id_conta,
                            "SKU": sku_item,
                            "Preço": preco_un,
                            "Quantidade Pedida": cols[1].text.strip(),
                            "Nome do Produto": nome_prod,
                            "Quantidade Preparar": cols[2].text.strip(),
                            "Telefone 1": row_lista.get('Telefone 1'),
                            "Telefone 2": row_lista.get('Telefone 2'),
                            "Email 1": row_lista.get('Email 1')
                        })
                    except: continue

                pedidos_processados.add(order_str)
                break

            except Exception as e:
                retries += 1
                logging.error(f"Erro no pedido {order_str}: {e}")
                time.sleep(3)
    
    return pd.DataFrame(detalhes)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    emails = [os.getenv('EMAIL1'), os.getenv('EMAIL2')]
    senhas = [os.getenv('SENHA1'), os.getenv('SENHA2')]
    filiais = [os.getenv('FILIAL1'), os.getenv('FILIAL2')] 
    max_retries_main = 3
    
    expected_cols = [
        'Numero Pedido', 'Data Pedido', 'Centro de Distribuição', 'Status',
        'Forma de Pagamento', 'Data Entrega', 'Responsavel', 'Total Pedido',
        'Documento', 'IE', 'Nome Comercial', 'Endereço de Entrega',
        'Cidade/UF', 'CEP', 'Coordenadas', 'ID do negócio', 'ID da conta do cliente',
        'SKU', 'Preço', 'Quantidade Pedida', 'Nome do Produto', 'Quantidade Preparar'
    ]
    for i in range(1, 3):  
        expected_cols.append(f'Telefone {i}')
    for i in range(1, 3):  
        expected_cols.append(f'Email {i}')

    for email, senha, filial in zip(emails, senhas, filiais):
        retries = 0
        while retries < max_retries_main:
            driver = None
            try:
                arquivo_csv = f'relatorios/Pedidos_A_Preparar_{filial}.csv'
                logging.info(f'Iniciando processamento para a filial {filial}...')

                chrome_options = Options()
                #chrome_options.add_argument("--headless")
                chrome_options.add_argument("--window-size=1920,1080")
                driver = webdriver.Chrome(options=chrome_options)
                driver.maximize_window()
                wait = WebDriverWait(driver, 60)

                logging.info(f"Tentando login com {email} para a filial {filial}.")
                login(driver, wait, email, senha)
                logging.info(f"Login bem-sucedido para {email}.")
                logging.info(f"Coletando pedidos ativos do site para a filial {filial}.")
                df_pedidos_ativos_site = navegar_paginas(driver, wait)
                logging.info(f"Total de {len(df_pedidos_ativos_site)} pedidos ativos encontrados no site para a filial {filial}.")

                if df_pedidos_ativos_site.empty:
                    logging.info(f"Nenhum pedido ativo encontrado para a filial {filial} no site.")
                    if os.path.exists(arquivo_csv):
                        os.remove(arquivo_csv)
                        logging.info(f"Arquivo '{arquivo_csv}' excluído, pois nenhum pedido ativo foi encontrado.")
                    else:
                        logging.info(f"Arquivo '{arquivo_csv}' não existe, nenhuma ação necessária.")
                    break # Sai do loop de retries e vai para a próxima filial
                
                df_pedidos_ativos_site_duplicados = df_pedidos_ativos_site[
                    df_pedidos_ativos_site.duplicated(subset=['Numero Pedido'], keep=False)]
                if not df_pedidos_ativos_site_duplicados.empty:
                    logging.warning("Atenção: Foram encontradas linhas duplicadas de pedidos ativos:")
                    logging.warning(df_pedidos_ativos_site_duplicados)

                if not df_pedidos_ativos_site.empty:
                    pedidos_ativos_site = set(df_pedidos_ativos_site['Numero Pedido'].astype(str))
                    df_detalhes_novos = pd.DataFrame()
                    pedidos_existente = set()

                    if os.path.exists(arquivo_csv):
                        try:
                            logging.info(f"Arquivo '{arquivo_csv}' encontrado. Lendo pedidos existentes.")
                        
                            df_pedidos_existente = pd.read_csv(arquivo_csv, encoding='utf-8-sig',
                                                                dtype={'CEP': str, 'Documento': str, 'IE': str,
                                                                        'Telefone 1': str, 'Telefone 2': str,
                                                                        'Email 1': str, 'Email 2': str})
                            pedidos_existente = set(df_pedidos_existente['Numero Pedido'].astype(str))
                            logging.info(f"Total de {len(pedidos_existente)} pedidos existentes no CSV para a filial {filial}.")

                            novos_pedidos = list(pedidos_ativos_site - pedidos_existente)
                            df_novos_pedidos = df_pedidos_ativos_site[
                                df_pedidos_ativos_site['Numero Pedido'].isin(novos_pedidos)].copy()
                            
                            if not df_novos_pedidos.empty:
                                logging.info(f"Encontrados {len(df_novos_pedidos)} novos pedidos para coletar detalhes.")
                                df_detalhes_novos = coletar_detalhes(driver, wait, df_novos_pedidos, pedidos_existente, filial)
                                logging.info(f"Tamanho do df_detalhes_novos após coletar detalhes: {len(df_detalhes_novos)}")

                            if not df_detalhes_novos.empty:
                                
                                for col in expected_cols:
                                    if col not in df_detalhes_novos.columns:
                                        df_detalhes_novos[col] = None

                                df_detalhes_novos = df_detalhes_novos[expected_cols]

                                df_pedidos_existente = pd.concat([df_pedidos_existente, df_detalhes_novos],
                                                                    ignore_index=True).drop_duplicates(
                                        subset=['Numero Pedido', 'SKU'], keep='first')
                                
                                cols_to_clean = ['CEP', 'Documento', 'IE'] + \
                                                    [f'Telefone {i}' for i in range(1, 3)] + \
                                                    [f'Email {i}' for i in range(1, 3)]
                                for col in cols_to_clean:
                                    if col in df_pedidos_existente.columns:
                                        df_pedidos_existente[col] = df_pedidos_existente[col].astype(str).replace(r'\.0$', '', regex=True)

                                df_pedidos_atualizado = df_pedidos_existente[
                                    df_pedidos_existente['Numero Pedido'].astype(str).isin(list(pedidos_ativos_site))].copy()
                                
                                for col in cols_to_clean:
                                    if col in df_pedidos_atualizado.columns:
                                        df_pedidos_atualizado[col] = df_pedidos_atualizado[col].astype(str).replace(r'\.0$', '', regex=True)
                                
                                
                                for col in expected_cols:
                                    if col not in df_pedidos_atualizado.columns:
                                        df_pedidos_atualizado[col] = None
                                df_pedidos_atualizado = df_pedidos_atualizado[expected_cols]

                                df_pedidos_atualizado.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
                                logging.info(f'Arquivo "{arquivo_csv}" atualizado para a filial {filial}.')

                            else: 
                                df_pedidos_atualizado = df_pedidos_existente[
                                    df_pedidos_existente['Numero Pedido'].astype(str).isin(list(pedidos_ativos_site))].copy()

                                cols_to_clean = ['CEP', 'Documento', 'IE'] + \
                                                    [f'Telefone {i}' for i in range(1, 3)] + \
                                                    [f'Email {i}' for i in range(1, 3)]
                                for col in cols_to_clean:
                                    if col in df_pedidos_atualizado.columns:
                                        df_pedidos_atualizado[col] = df_pedidos_atualizado[col].astype(str).replace(r'\.0$', '', regex=True)
                                
                                for col in expected_cols:
                                    if col not in df_pedidos_atualizado.columns:
                                        df_pedidos_atualizado[col] = None
                                df_pedidos_atualizado = df_pedidos_atualizado[expected_cols]
                                
                                df_pedidos_atualizado.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
                                logging.info(f'Arquivo "{arquivo_csv}" atualizado (sem novos detalhes, mas com limpeza de inativos) para a filial {filial}.')


                        except pd.errors.EmptyDataError:
                            logging.info(f"Arquivo '{arquivo_csv}' está vazio. Criando um novo arquivo.")
                            df_detalhes_novos = coletar_detalhes(driver, wait, df_pedidos_ativos_site, set(), filial)
                            logging.info(f"Tamanho do df_detalhes_novos após coletar detalhes (arquivo vazio): {len(df_detalhes_novos)}")
                            if not df_detalhes_novos.empty:
                        
                                for col in expected_cols:
                                    if col not in df_detalhes_novos.columns:
                                        df_detalhes_novos[col] = None
                                df_detalhes_novos = df_detalhes_novos[expected_cols]

                                cols_to_clean = ['CEP', 'Documento', 'IE'] + \
                                                    [f'Telefone {i}' for i in range(1, 3)] + \
                                                    [f'Email {i}' for i in range(1, 3)]
                                for col in cols_to_clean:
                                    if col in df_detalhes_novos.columns:
                                        df_detalhes_novos[col] = df_detalhes_novos[col].astype(str).replace(r'\.0$', '', regex=True)
                                df_detalhes_novos.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
                                logging.info(f'Dados salvos em "{arquivo_csv}" para a filial {filial}.')
                            else:
                                logging.info(f"Não foram encontrados pedidos ativos para salvar no arquivo '{arquivo_csv}' da filial {filial}. ")

                        except Exception as e:
                            logging.error(f"Erro ao ler ou processar o arquivo '{arquivo_csv}': {e}")

                    else:
                        logging.info(f"Arquivo '{arquivo_csv}' não encontrado. Criando um novo arquivo.")
                        df_detalhes_novos = coletar_detalhes(driver, wait, df_pedidos_ativos_site, set(), filial)
                        logging.info(f"Tamanho do df_detalhes_novos após coletar detalhes (arquivo novo): {len(df_detalhes_novos)}")

                        if not df_detalhes_novos.empty:
                        
                            for col in expected_cols:
                                if col not in df_detalhes_novos.columns:
                                    df_detalhes_novos[col] = None
                            
                            df_detalhes_novos = df_detalhes_novos[expected_cols]

                            cols_to_clean = ['CEP', 'Documento', 'IE'] + \
                                                [f'Telefone {i}' for i in range(1, 3)] + \
                                                [f'Email {i}' for i in range(1, 3)]
                            for col in cols_to_clean:
                                if col in df_detalhes_novos.columns:
                                    df_detalhes_novos[col] = df_detalhes_novos[col].astype(str).replace(r'\.0$', '', regex=True)
                            df_detalhes_novos.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
                            logging.info(f'Dados salvos em "{arquivo_csv}" para a filial {filial}.')
                        else:
                            logging.info(f"Não foram encontrados pedidos ativos para salvar no arquivo '{arquivo_csv}' da filial {filial}. ")

                break 

            except Exception as e:
                logging.error(f"Ocorreu um erro geral para a filial {filial}: {e}")
                retries += 1
                logging.info(f"Tentando novamente... Tentativa {retries} de {max_retries_main}.")
                if driver:
                    driver.quit() 
                time.sleep(10) 
            finally:
                if retries >= max_retries_main:
                    logging.error(f"O script falhou após {max_retries_main} tentativas para a filial {filial}. Prosseguindo para a próxima filial, se houver.")
                if driver and retries < max_retries_main:
                    driver.quit()