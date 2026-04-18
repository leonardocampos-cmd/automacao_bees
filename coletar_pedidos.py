#COLETAR OS DADOS
import os
from selenium import webdriver
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import logging

url = "https://one.bees.com/order-management/active-orders"

_COL_MAP = {
    'Numero Pedido':          'numero_pedido',
    'Data Pedido':            'data_pedido',
    'Centro de Distribuição': 'centro_distribuicao',
    'Status':                 'status',
    'Forma de Pagamento':     'forma_pagamento',
    'Data Entrega':           'data_entrega',
    'Responsavel':            'responsavel',
    'Total Pedido':           'total_pedido',
    'Documento':              'documento',
    'IE':                     'ie',
    'Nome Comercial':         'nome_comercial',
    'Endereço de Entrega':    'endereco_entrega',
    'Cidade/UF':              'cidade_uf',
    'CEP':                    'cep',
    'Coordenadas':            'coordenadas',
    'ID do negócio':          'id_negocio',
    'ID da conta do cliente': 'id_conta_cliente',
    'SKU':                    'sku',
    'Preço':                  'preco',
    'Quantidade Pedida':      'quantidade_pedida',
    'Nome do Produto':        'nome_produto',
    'Quantidade Preparar':    'quantidade_preparar',
    'Telefone 1':             'telefone_1',
    'Telefone 2':             'telefone_2',
    'Email 1':                'email_1',
    'Email 2':                'email_2',
}


def login(driver, wait, email, senha):
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
    except Exception:
        pass
    return pd.DataFrame(order_data)

def navegar_paginas(driver, wait):
    logging.info("Navegando pelas páginas de pedidos...")
    page_number = 1
    df_total = pd.DataFrame()

    while True:
        try:
            df = coletar_dados_pedidos(driver, wait)
            df_total = pd.concat([df_total, df], ignore_index=True)
            page_xpath = f'//li[@title="page {page_number}"]'
            try:
                next_page_buttons = driver.find_elements(By.XPATH, '//a[@aria-label="go to next page"]')
                if next_page_buttons and next_page_buttons[0].get_attribute("aria-disabled") == "true":
                    logging.info("Botão de próxima página desabilitado. Apenas uma página de resultados.")
                    break

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

            except Exception:
                logging.info("Não há mais páginas ou o botão de navegação.")
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

        logging.info(f"==> Processando Pedido: {order_str}")
        retries = 0
        while retries < max_retries:
            try:
                driver.get(f'https://one.bees.com/order-management/active-orders/{order_str}')
                wait.until(EC.presence_of_element_located((By.XPATH, "//table//tr")))
                time.sleep(3)

                def get_p_texts_by_label(label_name):
                    try:
                        xpath = f"//p[contains(text(), '{label_name}')]/parent::div/p"
                        elements = driver.find_elements(By.XPATH, xpath)
                        return [e.text.strip() for e in elements][1:]
                    except: return []

                def capturar_valor_pelo_label(label_texto):
                    try:
                        xpath = f"//p[contains(text(), '{label_texto}')]/following-sibling::p"
                        return driver.find_element(By.XPATH, xpath).text.strip()
                    except: return None

                forma_pagamento = capturar_valor_pelo_label("pagamento") or row_lista.get('Forma de Pagamento')
                id_negocio = capturar_valor_pelo_label("ID do negócio")
                id_conta = capturar_valor_pelo_label("ID da conta do cliente")

                tax_info = get_p_texts_by_label("Tax ID")
                documento = next((s.strip() for s in tax_info if "CPF" in s or "CNPJ" in s), None)
                ie = next((s.replace("INSCRICAO_ESTADUAL: ", "").strip() for s in tax_info if "INSCRICAO" in s), "ISENTO")

                nome_comercial_lista = get_p_texts_by_label("Nome comercial")
                nome_comercial = nome_comercial_lista[0] if nome_comercial_lista else row_lista.get('Nome Comercial')

                end_lista = get_p_texts_by_label("Endereço de entrega")
                endereco_rua = end_lista[0] if len(end_lista) > 0 else "Não capturado"
                cidade_uf = end_lista[1] if len(end_lista) > 1 else ""
                cep = end_lista[2] if len(end_lista) > 2 else ""
                coords = end_lista[3] if len(end_lista) > 3 else ""

                try:
                    xpath_tels = "//p[contains(text(), 'telefone')]/parent::div/p[contains(@class, 'weight-normal')]"
                    lista_telefones = [e.text.strip() for e in driver.find_elements(By.XPATH, xpath_tels)]
                    xpath_emails = "//p[contains(text(), 'E-mail')]/parent::div/p[contains(@class, 'weight-normal')]"
                    lista_emails = [e.text.strip() for e in driver.find_elements(By.XPATH, xpath_emails)]
                except:
                    lista_telefones, lista_emails = [], []

                tel1 = lista_telefones[0] if len(lista_telefones) > 0 else row_lista.get('Telefone 1')
                tel2 = lista_telefones[1] if len(lista_telefones) > 1 else row_lista.get('Telefone 2')
                email1 = lista_emails[0] if len(lista_emails) > 0 else row_lista.get('Email 1')
                email2 = lista_emails[1] if len(lista_emails) > 1 else row_lista.get('Email 2')

                try:
                    status = driver.find_element(By.XPATH, "//*[@data-testid='order-details-status']//*[contains(@class, 'weight-normal')]").text.strip()
                except: status = row_lista.get('Status')

                try:
                    cd = driver.find_element(By.XPATH, "//*[@data-testid='order-details-ddc-info']//*[contains(@class, 'weight-normal')]").text.strip()
                except: cd = row_lista.get('Centro de Distribuição')

                rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                for row in rows:
                    try:
                        nome_prod = row.find_element(By.XPATH, ".//*[contains(@data-testid, 'product_name')]").text.strip()
                        sku_item = row.find_element(By.XPATH, ".//*[contains(@data-testid, 'product_sku')]").text.strip()
                        preco_un = row.find_element(By.XPATH, ".//*[contains(@data-testid, 'product_price')]").text.strip()

                        cols = row.find_elements(By.TAG_NAME, "td")
                        qtd_pedida = cols[1].text.strip()
                        qtd_prepara = cols[2].text.strip()

                        detalhes.append({
                            "Numero Pedido": order_str,
                            "Data Pedido": row_lista.get('Data Pedido'),
                            "Centro de Distribuição": cd,
                            "Status": status,
                            "Forma de Pagamento": forma_pagamento,
                            "Data Entrega": row_lista.get('Data Entrega'),
                            "Responsavel": row_lista.get('Responsavel'),
                            "Total Pedido": row_lista.get('Total Pedido'),
                            "Documento": documento,
                            "IE": ie,
                            "Nome Comercial": nome_comercial,
                            "Endereço de Entrega": endereco_rua,
                            "Cidade/UF": cidade_uf,
                            "CEP": cep,
                            "Coordenadas": coords,
                            "ID do negócio": id_negocio or row_lista.get('ID do negócio'),
                            "ID da conta do cliente": id_conta or row_lista.get('ID da conta do cliente'),
                            "SKU": sku_item,
                            "Preço": preco_un,
                            "Quantidade Pedida": qtd_pedida,
                            "Nome do Produto": nome_prod,
                            "Quantidade Preparar": qtd_prepara,
                            "Telefone 1": tel1,
                            "Telefone 2": tel2,
                            "Email 1": email1,
                            "Email 2": email2
                        })
                    except: continue

                pedidos_processados.add(order_str)
                break
            except Exception as e:
                retries += 1
                logging.error(f"Erro no pedido {order_str}: {e}")
                time.sleep(2)

    return pd.DataFrame(detalhes)


if __name__ == "__main__":
    import db
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    db.criar_tabelas()

    emails = [
        os.getenv('EMAIL_RIGARR', 'leonardo.campos@rigarr.com.br'),
        os.getenv('EMAIL_CASTAS', 'cadastro@rigarr.com.br'),
    ]
    senhas = [
        os.getenv('SENHA_RIGARR', 'Br@sil32aaaaaaa'),
        os.getenv('SENHA_CASTAS', 'Rigarrdistribuidora@2024'),
    ]
    filiais = ['Rigarr', 'Castas']
    max_retries_main = 3

    for email, senha, filial in zip(emails, senhas, filiais):
        retries = 0
        while retries < max_retries_main:
            driver = None
            try:
                logging.info(f'Iniciando processamento para a filial {filial}...')

                chrome_options = Options()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--window-size=1920,1080")
                driver = webdriver.Chrome(options=chrome_options)
                wait = WebDriverWait(driver, 60)

                logging.info(f"Tentando login com {email} para a filial {filial}.")
                login(driver, wait, email, senha)
                logging.info(f"Login bem-sucedido para {email}.")

                df_pedidos_ativos_site = navegar_paginas(driver, wait)
                logging.info(f"Total de {len(df_pedidos_ativos_site)} pedidos ativos encontrados para {filial}.")

                if df_pedidos_ativos_site.empty:
                    logging.info(f"Nenhum pedido ativo para {filial}.")
                    db.deletar_pedidos_inativos(filial, set())
                    break

                pedidos_ativos_site = set(df_pedidos_ativos_site['Numero Pedido'].astype(str))
                pedidos_existentes = db.get_numeros_pedido_existentes(filial)
                novos = list(pedidos_ativos_site - pedidos_existentes)
                df_novos = df_pedidos_ativos_site[
                    df_pedidos_ativos_site['Numero Pedido'].isin(novos)
                ].copy()

                if not df_novos.empty:
                    logging.info(f"Coletando detalhes de {len(df_novos)} novos pedidos para {filial}.")
                    df_detalhes = coletar_detalhes(driver, wait, df_novos, pedidos_existentes, filial)

                    if not df_detalhes.empty:
                        df_detalhes['filial'] = filial
                        rows = df_detalhes.rename(columns=_COL_MAP).to_dict('records')
                        db.upsert_pedidos_itens(rows)
                        logging.info(f"{len(df_detalhes)} linhas salvas no banco para {filial}.")

                db.deletar_pedidos_inativos(filial, pedidos_ativos_site)
                logging.info(f"Pedidos inativos removidos para {filial}.")
                break

            except Exception as e:
                logging.error(f"Erro geral para {filial}: {e}")
                retries += 1
                if driver:
                    driver.quit()
                time.sleep(10)
            finally:
                if retries >= max_retries_main:
                    logging.error(f"Script falhou após {max_retries_main} tentativas para {filial}.")
                if driver and retries < max_retries_main:
                    driver.quit()
