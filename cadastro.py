#TRATAR CNPJ
import pandas as pd
import oracledb
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
oracledb.init_oracle_client(lib_dir=os.getenv("ORACLE_CLIENT_DIR", "/opt/instantclient"))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

FILIAIS = [
    {"nome": "SP", "dsn": os.getenv("DSN_SP"), "schema": "spon", "uf": "SP"},
    {"nome": "RJ", "dsn": os.getenv("DSN_RJ"), "schema": "crc",  "uf": "RJ"},
    {"nome": "MG", "dsn": os.getenv("DSN_MG"), "schema": "mgon", "uf": "MG"},
    {"nome": "ES", "dsn": os.getenv("DSN_ES"), "schema": "CRC",  "uf": "ES"},
]

caminho = r'G:\Drives compartilhados\Relatorios BEES'
arquivo_cnpjs = pd.read_csv(
    os.path.join(caminho, 'resultados_consulta_cnpj_api.csv'),
    sep=',', encoding='utf-8', dtype=str
)

arquivo_cnpjs.drop(columns=[
    'Capital Social', 'Natureza Jurídica', 'Data de Fundação',
    'Data de Status', 'Razão de Status', 'Inscrição Estadual Estado', 'Inscrição Estadual Tipo',
    'Inscrição Estadual Data de Status'
], inplace=True)

arquivo_cnpjs['Nome Fantasia'] = arquivo_cnpjs['Nome Fantasia'].fillna(arquivo_cnpjs['Nome'])
arquivo_cnpjs = arquivo_cnpjs[arquivo_cnpjs['Status'] == 'Ativa']
arquivo_cnpjs['CNPJ'] = arquivo_cnpjs['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)

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
            SELECT codcli, CGCENT
            FROM {schema}.PCCLIENT
        """, con=engine, dtype=str)
    except Exception as e:
        print(f"[{nome}] Erro ao conectar/consultar banco: {e}")
        continue

    tabela_cliente['cgcent'] = tabela_cliente['cgcent'].astype(str).str.replace(r'\D', '', regex=True)

    df = arquivo_cnpjs[arquivo_cnpjs['UF'] == filial["uf"]].copy()
    df = df.merge(tabela_cliente, left_on='CNPJ', right_on='cgcent', how='left')
    df.drop(columns=['Arquivo', 'Nome Fantasia', 'Tamanho', 'Status', 'Rua',
                     'Número', 'Complemento', 'Bairro', 'CEP', 'Telefone',
                     'Email', 'Atividade Principal', 'Atividades Secundárias',
                     'Simples Nacional Optante', 'SIMEI Optante',
                     'Inscrição Estadual Número', 'Inscrição Estadual Status',
                     'cgcent'], inplace=True, errors='ignore')
    df['FILIAL'] = nome
    resultados.append(df)
    print(f"[{nome}] {len(df)} registros processados.")

if resultados:
    resultado_final = pd.concat(resultados, ignore_index=True)
else:
    resultado_final = pd.DataFrame()

print(resultado_final)
