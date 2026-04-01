#envio para o whatsapp via Evolution API
import os
import json
import requests
import pandas as pd
import time
from datetime import datetime

# Configurações da Evolution API
EVOLUTION_URL = "http://localhost:8083"
EVOLUTION_KEY = "429683C4C977415CAAFCCE10F7D57E11"
INSTANCE      = "bees"
GRUPO_ANGRA   = "120363387684802858@g.us"   # Pedidos BEES - BIB Angra
#GRUPO_GERAL   = "120363387684802858@g.us"   # NF PEDIDOS VENDAS bebida in box Bees (ajuste o ID)

REGISTRO_JSON = "pedidos_enviados.json"

cidades_interior = ['PARATY','PARATY, RJ','PATY DO ALFERES','VALENCA','ITATIAIA', 'RESENDE', 'PORTO REAL', 'QUATIS', 'BARRA MANSA', 'VOLTA REDONDA', 'ARROZAL', 'PINHEIRAL', 'PIRAI', 'BARRA DO PIRAI', 'MENDES', 'VASSOURA', 'RIO CLARO','CACHOEIRAS DE MACACU','MIGUEL PEREIRA','TANGUA','Barra do Piraí','SAO JOSE DO VALE DO RIO PRETO','Barra do Pirai','Barra do Piraí','Areal','AREAL','PARAÍBA DO SUL','ANGRA DOS REIS','PETRÓPOLIS','Petrópolis','Teresópolis','TERESÓPOLIS','LIDICE','Paraty','Lídice', 'LÍDICE']


def localizar_arquivos_csv(diretorio_base):
    arquivos = []
    for raiz, _, nomes in os.walk(diretorio_base):
        for nome in nomes:
            if nome.startswith("Pedidos_A_Preparar_") and nome.endswith(".csv"):
                arquivos.append(os.path.join(raiz, nome))
    return arquivos


def carregar_pedidos_enviados():
    try:
        with open(REGISTRO_JSON, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def salvar_pedidos_enviados(pedidos_enviados):
    with open(REGISTRO_JSON, 'w', encoding='utf-8') as f:
        json.dump(sorted(pedidos_enviados), f, ensure_ascii=False, indent=2)


def enviar_mensagem(numero, mensagem):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE}"
    headers = {
        "apikey": EVOLUTION_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": numero,
        "text": mensagem
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            return True
        else:
            print(f"Erro ao enviar para {numero}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Erro ao enviar mensagem para {numero}: {e}")
        return False


def enviar_mensagem_pedido(grupo, pedido):
    estabelecimento = grupo['Nome Comercial'].iloc[0]
    responsavel = grupo['Responsavel'].iloc[0]
    forma_pgto = grupo['Forma de Pagamento'].iloc[0]
    total_pedido = grupo['Total Pedido'].iloc[0]
    endereco = grupo['Endereço de Entrega'].iloc[0]
    cidade_uf = grupo['Cidade/UF'].iloc[0].strip().upper()
    cep = str(grupo['CEP'].iloc[0])
    documento = grupo['Documento'].iloc[0]
    data_entrega = grupo['Data Entrega'].iloc[0]

    mensagem = (
        f"*Número Pedido*: *{pedido}*\n"
        f"*Responsavel*: {responsavel}\n"
        f"*Documento*: {documento}\n"
        f"*Estabelecimento*: {estabelecimento}\n"
    )

    if 'Email 1' in grupo.columns and pd.notna(grupo['Email 1'].iloc[0]):
        mensagem += f"*Email*: {grupo['Email 1'].iloc[0]}\n"

    if 'Telefone 1' in grupo.columns and pd.notna(grupo['Telefone 1'].iloc[0]):
        tel1 = str(grupo['Telefone 1'].iloc[0]).replace('.0', '').replace('+55','').replace('(', '').replace(')', '').replace('-', '').strip()
        if tel1:
            mensagem += f"*Telefone 1*: {tel1}\n"

    if 'Telefone 2' in grupo.columns and pd.notna(grupo['Telefone 2'].iloc[0]):
        tel2 = str(grupo['Telefone 2'].iloc[0]).replace('.0', '').replace('+55','').replace('(', '').replace(')', '').replace('-', '').strip()
        if tel2:
            mensagem += f"*Telefone 2*: {tel2}\n"

    for i in range(3, 6):
        coluna_contato = f'Contato {i}'
        if coluna_contato in grupo.columns and pd.notna(grupo[coluna_contato].iloc[0]):
            mensagem += f"*Contato {i}*: {grupo[coluna_contato].iloc[0]}\n"

    mensagem += (
        f"*Forma de Pagamento*: {forma_pgto}\n"
        f"*Total Pedido*: {total_pedido}\n"
        f"*Endereço de Entrega*: {endereco}\n"
        f"*Cidade/UF*: {cidade_uf}\n"
        f"*CEP*: {cep}\n"
        f"*Data Entrega*: {data_entrega}\n"
    )

    for _, row in grupo.iterrows():
        try:
            preco_total_float = float(row['Preço'])
            quantidade_pedida_float = float(row['Quantidade Pedida'])
            if quantidade_pedida_float != 0:
                unit_price = preco_total_float / quantidade_pedida_float
                mensagem += f"*Produto*: {row['Nome do Produto']} | Quantidade: {row['Quantidade Pedida']} | Preço Unitário: R${unit_price:.2f}\n"
            else:
                mensagem += f"*Produto*: {row['Nome do Produto']} | Quantidade: {row['Quantidade Pedida']} | Preço Total: R${row['Preço']} (Quantidade zero)\n"
        except ValueError:
            mensagem += f"*Produto*: {row['Nome do Produto']} | Quantidade: {row['Quantidade Pedida']} | Preço Total: {row['Preço']} (Erro de cálculo)\n"
        except Exception:
            mensagem += f"*Produto*: {row['Nome do Produto']} | Quantidade: {row['Quantidade Pedida']} | Preço Total: {row['Preço']} (Erro inesperado)\n"

    return mensagem


def verificar_condicoes_e_enviar_mensagem(df_final):
    pedidos_enviados = carregar_pedidos_enviados()

    pedidos_para_enviar_geral = []
    pedidos_para_enviar_angra = []

    for pedido, grupo in df_final.groupby('Numero Pedido'):
        pedido_str = str(pedido).strip()
        cidade_uf = str(grupo['Cidade/UF'].iloc[0]).strip().upper()
        documento = str(grupo['Documento'].iloc[0]).strip().upper()

        if pedido_str in pedidos_enviados:
            continue

        if any(c in cidade_uf for c in ["BARRA MANSA", "VOLTA REDONDA", "RIO CLARO", "MANGARATIBA", "ANGRA DOS REIS", "PINHEIRAL", "PARATY", "LÍDICE", "Lídice"]):
            pedidos_para_enviar_angra.append(pedido)
        elif not any(cidade in cidade_uf for cidade in cidades_interior) and "CPF" in documento and "RJ" in cidade_uf:
            pedidos_para_enviar_geral.append(pedido)

    if not pedidos_para_enviar_geral and not pedidos_para_enviar_angra:
        print("Nenhum pedido novo elegível para envio.")
        return

    now = datetime.now()
    hora = now.hour
    if 5 <= hora < 12:
        saudacao = "Bom dia!"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde!"
    else:
        saudacao = "Boa noite!"

    mensagem_inicial = f"{saudacao} Pedidos sendo enviados!"

    if pedidos_para_enviar_angra:
        enviar_mensagem(GRUPO_ANGRA, mensagem_inicial)
        time.sleep(2)

    for pedido in pedidos_para_enviar_angra:
        try:
            grupo = df_final[df_final['Numero Pedido'] == pedido]
            pedido_str = str(pedido).strip()
            mensagem = enviar_mensagem_pedido(grupo, pedido)
            print(f"Enviando pedido {pedido_str} para o grupo de Angra...")
            if enviar_mensagem(GRUPO_ANGRA, mensagem):
                pedidos_enviados.add(pedido_str)
                salvar_pedidos_enviados(pedidos_enviados)
                time.sleep(1)
        except Exception as e:
            print(f"Falha ao processar e enviar o pedido {pedido} para o grupo de Angra: {e}")

    # for pedido in pedidos_para_enviar_geral:
    #     try:
    #         grupo = df_final[df_final['Numero Pedido'] == pedido]
    #         pedido_str = str(pedido).strip()
    #         mensagem = enviar_mensagem_pedido(grupo, pedido)
    #         print(f"Enviando pedido {pedido_str} para o grupo geral...")
    #         if enviar_mensagem(GRUPO_GERAL, mensagem):
    #             pedidos_enviados.add(pedido_str)
    #             salvar_pedidos_enviados(pedidos_enviados)
    #             time.sleep(1)
    #     except Exception as e:
    #         print(f"Falha ao processar e enviar o pedido {pedido} para o grupo geral: {e}")


def existem_pedidos_para_envio(df_final):
    pedidos_enviados = carregar_pedidos_enviados()

    for pedido, grupo in df_final.groupby('Numero Pedido'):
        pedido_str = str(pedido).strip()
        cidade_uf = str(grupo['Cidade/UF'].iloc[0]).strip().upper()
        documento = str(grupo['Documento'].iloc[0]).strip().upper()

        if pedido_str in pedidos_enviados:
            continue

        if any(c in cidade_uf for c in ["PARATY","BARRA MANSA", "VOLTA REDONDA", "RIO CLARO", "MANGARATIBA", "ANGRA DOS REIS", "PINHEIRAL", "ARROZAL"]):
            return True

        if not any(cidade in cidade_uf for cidade in cidades_interior) and "CPF" in documento and "RJ" in cidade_uf:
            return True

    return False


# --- Início da Execução Principal ---
caminho = r'G:\Drives compartilhados\Relatorios BEES'
arquivos_csv = localizar_arquivos_csv(caminho)

if not arquivos_csv:
    print(f"Nenhum arquivo CSV encontrado em: {caminho}")
else:
    df_list = []
    print(f"Encontrados {len(arquivos_csv)} arquivos CSV. Lendo...")
    for arquivo in arquivos_csv:
        try:
            df_list.append(pd.read_csv(arquivo, encoding='utf-8-sig', on_bad_lines='skip'))
            print(f"Arquivo '{os.path.basename(arquivo)}' lido com sucesso.")
        except pd.errors.ParserError as e:
            print(f"Erro de parser no arquivo '{os.path.basename(arquivo)}': {e}.")
        except Exception as e:
            print(f"Erro ao ler o arquivo '{os.path.basename(arquivo)}': {e}.")

    if not df_list:
        print("Nenhum arquivo CSV pôde ser lido. Encerrando.")
    else:
        df_final = pd.concat(df_list, ignore_index=True)
        print("Todos os arquivos lidos foram concatenados.")
        print("Verificando se existem pedidos elegíveis para envio...")

        if not existem_pedidos_para_envio(df_final):
            print("Nenhum pedido novo elegível. Encerrando.")
        else:
            df_final['Preço'] = df_final['Preço'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
            df_final['Preço'] = pd.to_numeric(df_final['Preço'], errors='coerce').fillna(0)
            df_final['Quantidade Pedida'] = pd.to_numeric(df_final['Quantidade Pedida'], errors='coerce').fillna(0)
            print("Colunas 'Preço' e 'Quantidade Pedida' processadas.")

            try:
                verificar_condicoes_e_enviar_mensagem(df_final)
            except Exception as e:
                print(f"Ocorreu um erro durante o envio: {e}")
