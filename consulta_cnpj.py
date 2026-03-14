#CNPJ
import pandas as pd
import requests
import os
import time

# Configurações
pasta_arquivos = os.path.expanduser(r'C:\Users\LeonardoCampos\Meu Drive\automacao_bees\relatorios')
 # Caminho da pasta onde os arquivos CSV estão localizado
coluna_cnpj = "ID da conta do cliente" # Nome da coluna que contém os CNPJs nos arquivos CSV
nome_arquivo_saida = "resultados_consulta_cnpj_api.csv" # Nome do arquivo CSV de saída com os resultados
chave_api_cnpja = "1b28050f-2e7a-4803-9ff4-e100532de3e0-01504ddb-8ef6-4ea4-88b2-173c5ec3feb5" # Chave da API CNPJA

# Variável para controlar a taxa de requisições
CONSULTAS_POR_MINUTO = 20 # Número máximo de consultas por minuto permitido pela API
INTERVALO_SEGUNDOS = 60 / CONSULTAS_POR_MINUTO # Intervalo mínimo entre as consultas para respeitar o limite de taxa
ultima_consulta = 0 # Timestamp da última consulta realizada

# Conjunto para armazenar CNPJs únicos já processados para evitar consultas duplicadas
cnpjs_processados = set()
resultados_finais = [] # Lista para armazenar os resultados de todas as consultas

# Função para consultar CNPJ com controle de taxa
def consultar_cnpj(cnpj, chave_api):
    global ultima_consulta
    tempo_atual = time.time()
    tempo_decorrido = tempo_atual - ultima_consulta

    # Verifica se o tempo decorrido desde a última consulta é menor que o intervalo mínimo
    if tempo_decorrido < INTERVALO_SEGUNDOS:
        tempo_espera = INTERVALO_SEGUNDOS - tempo_decorrido
        # print(f"Esperando {tempo_espera:.2f} segundos para evitar limite de taxa...") # Comentado para evitar poluir o console
        time.sleep(tempo_espera) # Pausa a execução pelo tempo necessário

    try:
        headers = {"Authorization": chave_api} # Cabeçalhos da requisição com a chave da API
        url = f'https://api.cnpja.com/office/{cnpj}?simples=true&registrations=BR' # URL da API para consulta do CNPJ
        response = requests.get(url, headers=headers) # Realiza a requisição GET
        response.raise_for_status() # Levanta um erro HTTP para status de erro (4xx ou 5xx)
        empresa = response.json() # Converte a resposta JSON em um dicionário Python
        ultima_consulta = time.time() # Atualiza o timestamp da última consulta
        return empresa # Retorna os dados da empresa
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar CNPJ {cnpj}: {e}") # Captura erros de requisição
        return None
    except ValueError as e:
        print(f"Erro ao decodificar JSON para CNPJ {cnpj}: {e}") # Captura erros ao decodificar JSON
        return None
    except Exception as e:
        print(f"Erro desconhecido ao consultar CNPJ {cnpj}: {e}") # Captura outros erros
        return None

# Função para extrair dados relevantes do JSON da API para um dicionário
def extrair_dados_para_df(dados_cnpj):
    dados = {
        'CNPJ': dados_cnpj['taxId'],
        'Nome': dados_cnpj['company']['name'],
        'Nome Fantasia': dados_cnpj.get('alias', 'Não disponível'),
        'Capital Social': dados_cnpj['company']['equity'],
        'Natureza Jurídica': dados_cnpj['company']['nature']['text'],
        'Tamanho': dados_cnpj['company']['size']['text'],
        'Data de Fundação': dados_cnpj['founded'],
        'Status': dados_cnpj['status']['text'],
        'Data de Status': dados_cnpj['statusDate'],
        'Razão de Status': dados_cnpj.get('reason', {}).get('text', 'Não disponível'),
        # Endereço detalhado
        'Rua': dados_cnpj['address'].get('street', 'Não disponível'),
        'Número': dados_cnpj['address'].get('number', 'Não disponível'),
        'Complemento': dados_cnpj['address'].get('details', 'Não disponível'),
        'Bairro': dados_cnpj['address'].get('district', 'Não disponível'),
        'Cidade/UF': f"{dados_cnpj['address'].get('city', 'Não disponível')}/{dados_cnpj['address'].get('state', 'Não disponível')}",
        'CEP': dados_cnpj['address'].get('zip', 'Não disponível'),
        'País': dados_cnpj['address']['country']['name'],
        'Telefone': ', '.join([f"({telefone['area']}) {telefone['number']}" for telefone in dados_cnpj['phones']]) if dados_cnpj['phones'] else 'Não disponível',
        'Email': ', '.join([email['address'] for email in dados_cnpj['emails']]) if dados_cnpj['emails'] else 'Não disponível',
        'Atividade Principal': dados_cnpj['mainActivity']['text'],
        'Atividades Secundárias': ', '.join([activity['text'] for activity in dados_cnpj['sideActivities']]) if dados_cnpj['sideActivities'] else 'Nenhuma',
        'Simples Nacional Optante': dados_cnpj['company']['simples']['optant'] if 'simples' in dados_cnpj['company'] else 'Não disponível',
        'Simples Nacional Desde': dados_cnpj['company']['simples']['since'] if 'simples' in dados_cnpj['company'] else 'Não disponível',
        'SIMEI Optante': dados_cnpj['company']['simei']['optant'] if 'simei' in dados_cnpj['company'] else 'Não disponível',
        'SIMEI Desde': dados_cnpj['company']['simei']['since'] if 'simei' in dados_cnpj['company'] else 'Não disponível',
    }
    # Inscrição Estadual (se disponível)
    if 'registrations' in dados_cnpj and len(dados_cnpj['registrations']) > 0:
        inscricao_estadual = dados_cnpj['registrations'][0]
        dados['Inscrição Estadual Estado'] = inscricao_estadual.get('state', 'Não encontrada')
        dados['Inscrição Estadual Número'] = inscricao_estadual.get('number', 'Não encontrada')
        dados['Inscrição Estadual Status'] = inscricao_estadual.get('status', {}).get('text', 'Não encontrada')
        dados['Inscrição Estadual Tipo'] = inscricao_estadual.get('type', {}).get('text', 'Não encontrada')
        dados['Inscrição Estadual Data de Status'] = inscricao_estadual.get('statusDate', 'Não encontrada')
    else:
        dados['Inscrição Estadual Estado'] = 'Não encontrada'
        dados['Inscrição Estadual Número'] = 'Não encontrada'
        dados['Inscrição Estadual Status'] = 'Não encontrada'
        dados['Inscrição Estadual Tipo'] = 'Não encontrada'
        dados['Inscrição Estadual Data de Status'] = 'Não encontrada'

    return dados

# Função principal para consultar CNPJs
def consultar_cnpjs():
    # Itera sobre todos os arquivos na pasta especificada
    for nome_arquivo in os.listdir(pasta_arquivos):
        # Processa apenas arquivos que começam com "Pedidos_A_Preparar_"
        if nome_arquivo.startswith("Pedidos_A_Preparar_"):
            caminho_arquivo = os.path.join(pasta_arquivos, nome_arquivo) # Constrói o caminho completo do arquivo
            try:
                df = pd.read_csv(caminho_arquivo,dtype=str) # Lê o arquivo CSV para um DataFrame do pandas

                print(f"Arquivo: {nome_arquivo}, Linhas antes do filtro: {len(df)}")

                # Limpa e formata a coluna de CNPJ
                df[coluna_cnpj] = df[coluna_cnpj].astype(str).str.strip().str.upper()

                cnpjs_arquivo = set() # Conjunto para armazenar CNPJs únicos deste arquivo
                for valor in df[coluna_cnpj]:
                    valor_sem_formatacao = valor.replace('.', '').replace('/', '').replace('-', '') # Remove formatação do CNPJ
                    if valor_sem_formatacao.isdigit() and len(valor_sem_formatacao) > 11: # Verifica se é um CNPJ válido
                        cnpjs_arquivo.add(valor_sem_formatacao) # Adiciona ao conjunto de CNPJs do arquivo

                print(f"Arquivo: {nome_arquivo}, CNPJs únicos encontrados neste arquivo: {len(cnpjs_arquivo)}")

                # Itera sobre os CNPJs únicos do arquivo
                for cnpj in cnpjs_arquivo:
                    if cnpj not in cnpjs_processados: # Verifica se o CNPJ já foi processado
                        dados_cnpj = consultar_cnpj(cnpj, chave_api_cnpja) # Consulta o CNPJ na API
                        if dados_cnpj:
                            dados_empresa = extrair_dados_para_df(dados_cnpj) # Extrai os dados da empresa
                            resultados_finais.append({
                                "Arquivo": nome_arquivo,
                                "CNPJ": cnpj,
                                **dados_empresa # Adiciona os dados da empresa aos resultados finais
                            })
                            cnpjs_processados.add(cnpj) # Adiciona o CNPJ ao conjunto de processados
                        else:
                            print(f"Erro ao consultar CNPJ: {cnpj}")
                    else:
                        print(f"CNPJ {cnpj} já foi processado. Ignorando.") # Informa que o CNPJ já foi processado

            except Exception as e:
                print(f"Erro ao processar o arquivo {nome_arquivo}: {e}") # Captura erros durante o processamento do arquivo

    # Salva os resultados finais em um novo arquivo CSV
    df_resultados = pd.DataFrame(resultados_finais)
    caminho_saida = os.path.join(pasta_arquivos, nome_arquivo_saida)
    df_resultados.to_csv(caminho_saida, index=False, encoding='utf-8')
    df_resultados = df_resultados[
        (df_resultados['Status'] != "Ativa") |
        (~df_resultados['Inscrição Estadual Status'].str.contains("Sem restrição|Não encontrada", na=False))
    ]
    print(df_resultados)
    print(f"\nConsulta de CNPJs concluída. Os resultados únicos foram salvos em '{caminho_saida}'")

if __name__ == "__main__":
    consultar_cnpjs()