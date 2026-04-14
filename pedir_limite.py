#PEDIR LIMITE
import os
import requests
import pandas as pd
import oracledb
import time
import json
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
oracledb.init_oracle_client(lib_dir=r"C:\instantclient")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

CONTATOS_LIMITE = {
    "SP": {"numero": os.getenv("NUMERO_DESTINO_LIMITE_SP"), "nome": os.getenv("NOME_CONTATO_LIMITE_SP")},
    "RJ": {"numero": os.getenv("NUMERO_DESTINO_LIMITE_RJ"), "nome": os.getenv("NOME_CONTATO_LIMITE_RJ")},
    "MG": {"numero": os.getenv("NUMERO_DESTINO_LIMITE_MG"), "nome": os.getenv("NOME_CONTATO_LIMITE_MG")},
    "ES": {"numero": os.getenv("NUMERO_DESTINO_LIMITE_ES"), "nome": os.getenv("NOME_CONTATO_LIMITE_ES")},
}

# ================== CONFIGURAÇÕES DA EVOLUTION API ==================
SERVER_URL = "http://localhost:8083"
INSTANCE = "bees"
APIKEY = "429683C4C977415CAAFCCE10F7D57E11"
DELAY_ENTRE_MENSAGENS = 2
LOG_FILE = "log_envio_geral.json"

FILIAIS = [
    {
        "nome": "SP",
        "dsn": os.getenv("DSN_SP"),
        "schema": "spon",
        "centros": ["CASTAS SP", "RIGARRSPCAPITAL"],
        "rename_cd": {"RIGARRSPCAPITAL": "SPON"},
    },
    {
        "nome": "RJ",
        "dsn": os.getenv("DSN_RJ"),
        "schema": "crc",
        "centros": ["CASTAS RJ", "RIGARRRJCAPITAL"],
        "rename_cd": {"RIGARRRJCAPITAL": "CRC"},
    },
    {
        "nome": "MG",
        "dsn": os.getenv("DSN_MG"),
        "schema": "mgon",
        "centros": ["CASTAS MG", "RIGARRMGCAPITAL"],
        "rename_cd": {"RIGARRMGCAPITAL": "MGON"},
    },
    {
        "nome": "ES",
        "dsn": os.getenv("DSN_ES"),
        "schema": "CRC",
        "centros": ["CASTAS ES", "RIGARRESCAPITAL"],
        "rename_cd": {"RIGARRESCAPITAL": "ES"},
    },
]

# --- Leitura dos CSVs (única, compartilhada entre filiais) ---
caminho = r'G:\Drives compartilhados\Relatorios BEES'
arquivos_csv = [f for f in os.listdir(caminho) if f.endswith('.csv') and 'Pedidos_A_Preparar' in f]
df_list = [pd.read_csv(os.path.join(caminho, f), dtype=str) for f in arquivos_csv]
arquivo_pedidos_base = pd.concat(df_list, ignore_index=True)

colunas_descartar = [
    'Data Pedido', 'Status', 'Data Entrega', 'Responsavel', 'CEP',
    'Coordenadas', 'ID do negócio', 'ID da conta do cliente', 'IE',
    'Quantidade Preparar', 'Email 1', 'Email 2',
    'Nome Comercial', 'Endereço de Entrega',
    'Cidade/UF', 'SKU', 'Preço', 'Quantidade Pedida', 'Nome do Produto',
    'Telefone 1', 'Telefone 2'
]
arquivo_pedidos_base.drop(columns=colunas_descartar, inplace=True, errors='ignore')
arquivo_pedidos_base['Total Pedido'] = (
    arquivo_pedidos_base['Total Pedido']
    .astype(str)
    .str.replace('$', '', regex=False)
    .str.replace(',', '', regex=False)
)
arquivo_pedidos_base['Tipo Documento'] = arquivo_pedidos_base['Documento'].str.split(':').str[0]
arquivo_pedidos_base['Numero Documento'] = arquivo_pedidos_base['Documento'].str.split(':').str[1].str.strip()
arquivo_pedidos_base.drop(columns=['Documento', 'Tipo Documento'], inplace=True, errors='ignore')


# --- Processamento por filial ---
resultados = []

for filial in FILIAIS:
    nome = filial["nome"]
    dsn = filial["dsn"]
    schema = filial["schema"]

    if not dsn:
        print(f"[{nome}] DSN não configurado no .env, pulando.")
        continue

    print(f"[{nome}] Conectando ao banco {dsn}...")
    try:
        engine = create_engine(f'oracle+oracledb://{DB_USER}:{DB_PASSWORD}@{dsn}')

        tabela_cliente = pd.read_sql(f"""
            SELECT codcli,cliente, cgcent, BLOQUEIO, LIMCRED
            FROM {schema}.PCCLIENT
        """, con=engine, dtype=str)

        tabela_edc = pd.read_sql(f"""
            SELECT NUMPEDCLI
            FROM {schema}.PCPEDC
            WHERE NUMPEDCLI IS NULL
        """, con=engine, dtype=str)

        tabela_rest = pd.read_sql(f"""
            SELECT 
                codcli, 
                SUM(valor) AS valor
                FROM {schema}.PCPREST
            WHERE vpago IS NULL OR vpago = '0'
            GROUP BY codcli
        """, con=engine, dtype=str)

    except Exception as e:
        print(f"[{nome}] Erro ao conectar/consultar banco: {e}")
        continue

    tabela_cliente['cgcent'] = tabela_cliente['cgcent'].str.replace(r'\D', '', regex=True)
    tabela_cliente = tabela_cliente.merge(tabela_rest, on='codcli', how='left')

    df = arquivo_pedidos_base.copy()
    df = df[df['Centro de Distribuição'].isin(filial["centros"])]
    df = df.merge(tabela_edc, left_on='Numero Pedido', right_on='numpedcli', how='left')
    df = df.drop_duplicates(['Numero Documento'])
    df['Numero Documento'] = df['Numero Documento'].str.strip()
    df['Centro de Distribuição'] = df['Centro de Distribuição'].replace(filial["rename_cd"])
    df['Forma de Pagamento'] = df['Forma de Pagamento'].replace({
        'Cartão de Crédito na Entrega (Somente em 1x)': 'CARC',
        'Cartão de Débito na Entrega': 'CARD',
        'Dinheiro': 'D',
        'Pix na entrega': 'QR'
    })

    df = df.merge(tabela_cliente, left_on='Numero Documento', right_on='cgcent', how='left')
    df.drop(columns=['Numero Documento', 'cgcent'], inplace=True)

    df['Total Pedido'] = df['Total Pedido'].astype(float)
    df['limcred'] = df['limcred'].astype(float)
    df['valor'] = df['valor'].astype(float)

    df = df.groupby('codcli').agg({
        'Total Pedido': 'sum',
        'bloqueio': 'first',
        'limcred': 'first',
        'Centro de Distribuição': 'first',
        'valor': 'first',
        'Forma de Pagamento': 'first'
    }).reset_index()

    df.columns = df.columns.str.upper()
    df['Limite Disponivel'] = (
        pd.to_numeric(df['LIMCRED'], errors='coerce').fillna(0) -
        pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    )
    df = df[
        (df['Limite Disponivel'] < df['TOTAL PEDIDO']) |
        (df['BLOQUEIO'] == 'S')
    ]
    df.drop(columns=['BLOQUEIO', 'LIMCRED', 'CENTRO DE DISTRIBUIÇÃO', 'VALOR', 'Limite Disponivel'], inplace=True)
    df['FILIAL'] = nome
    resultados.append(df)
    print(f"[{nome}] {len(df)} clientes com limite insuficiente ou bloqueados.")

# --- Resultado consolidado ---
if resultados:
    df_final = pd.concat(resultados, ignore_index=True)
else:
    df_final = pd.DataFrame()

print(df_final)
# ================== FUNÇÕES DE ENVIO ==================
def _carregar_historico():
    if not os.path.exists(LOG_FILE):
        return {}
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def _salvar_historico(historico):
    with open(LOG_FILE, "w") as f:
        json.dump(historico, f, indent=4)

def ja_enviou_saudacao_hoje(id_cd):
    dados_cd = _carregar_historico().get(id_cd, {})
    return dados_cd.get("ultima_saudacao", "") == datetime.now().strftime("%Y-%m-%d")

def registrar_envio_saudacao(id_cd):
    historico = _carregar_historico()
    historico.setdefault(id_cd, {})
    historico[id_cd]["ultima_saudacao"] = datetime.now().strftime("%Y-%m-%d")
    historico[id_cd]["horario"] = datetime.now().strftime("%H:%M:%S")
    _salvar_historico(historico)

def ja_enviou_cliente_hoje(id_cd, codcli):
    hoje = datetime.now().strftime("%Y-%m-%d")
    clientes_hoje = _carregar_historico().get(id_cd, {}).get("clientes", {}).get(hoje, [])
    return str(codcli) in clientes_hoje

def registrar_envio_cliente(id_cd, codcli):
    hoje = datetime.now().strftime("%Y-%m-%d")
    historico = _carregar_historico()
    historico.setdefault(id_cd, {})
    historico[id_cd].setdefault("clientes", {})
    historico[id_cd]["clientes"].setdefault(hoje, [])
    if str(codcli) not in historico[id_cd]["clientes"][hoje]:
        historico[id_cd]["clientes"][hoje].append(str(codcli))
    _salvar_historico(historico)

def obter_saudacao(nome=""):
    hora_atual = datetime.now().hour
    if 5 <= hora_atual < 12: prefixo = "Bom dia"
    elif 12 <= hora_atual < 18: prefixo = "Boa tarde"
    else: prefixo = "Boa noite"
    return f"{prefixo}, {nome}" if nome else prefixo

def enviar_mensagem_whatsapp(numero, mensagem, id_cd=None):
    url_presence = f"{SERVER_URL}/chat/presenceUpdate/{INSTANCE}"
    try:
        requests.post(url_presence, json={"number": numero, "presence": "composing"}, headers={"apikey": APIKEY}, timeout=5)
        time.sleep(1.5)
    except: pass

    url_send = f"{SERVER_URL}/message/sendText/{INSTANCE}"
    payload = {"number": numero, "text": mensagem}
    headers = {"apikey": APIKEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url_send, json=payload, headers=headers, timeout=10)
        return response.status_code
    except Exception as e:
        return str(e)

def executar_automacao(df, id_cd):
    contato = CONTATOS_LIMITE.get(id_cd, {})
    numero = contato.get("numero")
    nome = contato.get("nome", "")

    if not numero:
        print(f"⚠️ {id_cd}: Número de destino não configurado no .env. Pulando...")
        return

    if df is None or df.empty:
        print(f"⚠️ {id_cd}: Nenhum dado encontrado para envio. Encerrando...")
        return

    if not ja_enviou_saudacao_hoje(id_cd):
        saudacao = f"{obter_saudacao(nome)}! Seguem os clientes para solicitação de limite:"
        print(f"📤 Enviando saudação inicial do {id_cd}...")
        enviar_mensagem_whatsapp(numero, saudacao)
        registrar_envio_saudacao(id_cd)
        time.sleep(DELAY_ENTRE_MENSAGENS)
    else:
        print(f"⏭️ {id_cd} já saudou hoje. Enviando apenas os novos pedidos...")

    algum_enviado = False
    for _, row in df.iterrows():
        codcli = row['CODCLI']
        if ja_enviou_cliente_hoje(id_cd, codcli):
            print(f"⏭️ Cliente {codcli} já solicitado hoje. Pulando...")
            continue
        mensagem = (
            f"👤 *Cod Cliente:* {codcli}\n"
            f"💰 *Valor do Pedido:* R$ {row['TOTAL PEDIDO']:.2f}\n"
            f"💳 *Forma de Pagamento:* {row['FORMA DE PAGAMENTO']}\n"
        )
        print(f"📤 Enviando limite {codcli}...")
        enviar_mensagem_whatsapp(numero, mensagem)
        registrar_envio_cliente(id_cd, codcli)
        time.sleep(DELAY_ENTRE_MENSAGENS)
        algum_enviado = True

    if algum_enviado:
        print(f"📤 Enviando fechamento...")
        enviar_mensagem_whatsapp(numero, "Poderia liberar o limite para esses clientes, por favor? Obrigado!")

# --- EXECUÇÃO DO ENVIO ---
for filial_nome, df_filial in df_final.groupby('FILIAL'):
    executar_automacao(df_filial, filial_nome)
