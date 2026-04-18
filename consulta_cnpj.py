#CNPJ
import os
import time
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import db

chave_api_cnpja = os.getenv("CNPJA_API_KEY")
CONSULTAS_POR_MINUTO = 20
INTERVALO_SEGUNDOS = 60 / CONSULTAS_POR_MINUTO
ultima_consulta = 0


def consultar_cnpj(cnpj, chave_api):
    global ultima_consulta
    tempo_decorrido = time.time() - ultima_consulta
    if tempo_decorrido < INTERVALO_SEGUNDOS:
        time.sleep(INTERVALO_SEGUNDOS - tempo_decorrido)
    try:
        headers = {"Authorization": chave_api}
        url = f'https://api.cnpja.com/office/{cnpj}?simples=true&registrations=BR'
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        empresa = response.json()
        ultima_consulta = time.time()
        return empresa
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar CNPJ {cnpj}: {e}")
        return None
    except Exception as e:
        print(f"Erro desconhecido ao consultar CNPJ {cnpj}: {e}")
        return None


def extrair_dados_para_df(dados_cnpj):
    company = dados_cnpj.get('company', {})
    address = dados_cnpj.get('address', {})
    status = dados_cnpj.get('status', {})
    dados = {
        'CNPJ': dados_cnpj.get('taxId'),
        'Nome': company.get('name'),
        'Nome Fantasia': dados_cnpj.get('alias', 'Não disponível'),
        'Capital Social': company.get('equity'),
        'Natureza Jurídica': company.get('nature', {}).get('text', 'N/D'),
        'Tamanho': company.get('size', {}).get('text', 'N/D'),
        'Data de Fundação': dados_cnpj.get('founded'),
        'Status': status.get('text'),
        'Data de Status': dados_cnpj.get('statusDate'),
        'Razão de Status': dados_cnpj.get('reason', {}).get('text', 'Não disponível'),
        'Rua': address.get('street', 'Não disponível'),
        'Número': address.get('number', 'Não disponível'),
        'Complemento': address.get('details', 'Não disponível'),
        'Bairro': address.get('district', 'Não disponível'),
        'Cidade': address.get('city', 'Não disponível'),
        'UF': address.get('state', 'Não disponível'),
        'CEP': address.get('zip', 'Não disponível'),
        'Telefone': ', '.join([f"({t['area']}) {t['number']}" for t in dados_cnpj.get('phones', [])]) or 'N/D',
        'Email': ', '.join([e['address'] for e in dados_cnpj.get('emails', [])]) or 'N/D',
        'Atividade Principal': dados_cnpj.get('mainActivity', {}).get('text', 'N/D'),
        'Atividades Secundárias': ', '.join([a['text'] for a in dados_cnpj.get('sideActivities', [])]) or 'Nenhuma',
        'Simples Nacional Optante': company.get('simples', {}).get('optant', 'N/D'),
        'SIMEI Optante': company.get('simei', {}).get('optant', 'N/D'),
    }
    if 'registrations' in dados_cnpj and len(dados_cnpj['registrations']) > 0:
        ie = dados_cnpj['registrations'][0]
        dados['Inscrição Estadual Estado'] = ie.get('state', 'Não encontrada')
        dados['Inscrição Estadual Número'] = ie.get('number', 'Não encontrada')
        dados['Inscrição Estadual Status'] = ie.get('status', {}).get('text', 'Não encontrada')
        dados['Inscrição Estadual Tipo'] = ie.get('type', {}).get('text', 'Não encontrada')
        dados['Inscrição Estadual Data de Status'] = ie.get('statusDate', 'Não encontrada')
    else:
        dados['Inscrição Estadual Estado'] = 'Não encontrada'
        dados['Inscrição Estadual Número'] = 'Não encontrada'
        dados['Inscrição Estadual Status'] = 'Não encontrada'
        dados['Inscrição Estadual Tipo'] = 'Não encontrada'
        dados['Inscrição Estadual Data de Status'] = 'Não encontrada'
    return dados


db.criar_tabelas()

cnpjs_processados = db.get_cnpjs_existentes()
print(f"{len(cnpjs_processados)} CNPJs já consultados no banco.")

todos_pedidos = db.get_todos_pedidos()
todos_cnpjs_planilha = set()
for row in todos_pedidos:
    valor = str(row.get('id_conta_cliente', '') or '')
    valor_limpo = valor.replace('.', '').replace('/', '').replace('-', '').strip().upper()
    if valor_limpo.isdigit() and len(valor_limpo) > 11:
        todos_cnpjs_planilha.add(valor_limpo)

print(f"CNPJs únicos encontrados nos pedidos: {len(todos_cnpjs_planilha)}")

for cnpj in todos_cnpjs_planilha:
    if cnpj not in cnpjs_processados:
        dados_cnpj = consultar_cnpj(cnpj, chave_api_cnpja)
        if dados_cnpj:
            dados_empresa = extrair_dados_para_df(dados_cnpj)
            db.upsert_cnpj(dados_empresa)
            cnpjs_processados.add(cnpj)
            print(f"CNPJ {cnpj} salvo no banco.")
        else:
            print(f"Erro ao consultar CNPJ: {cnpj}")
    else:
        print(f"CNPJ {cnpj} já processado. Ignorando.")

print(f"\nConsulta de CNPJs concluída. Total de CNPJs únicos: {len(todos_cnpjs_planilha)}")
