#PEDIR LIMITE
import pandas as pd
import oracledb
from sqlalchemy import create_engine
import os

oracledb.init_oracle_client(lib_dir=r"C:\instantclient")

user = "vpn"
password = "vpn2320vpn"
dsn = "crc_oci"
engine = create_engine(f'oracle+oracledb://{user}:{password}@{dsn}')

tabela_cliente = pd.read_sql("""
    SELECT codcli, cgcent, BLOQUEIO, LIMCRED, MOTIVOBLOQ
    FROM crc.PCCLIENT
""", con=engine,dtype=str)

tabela_edc = pd.read_sql("""
    SELECT NUMPED, VLTOTAL, POSICAO, CODCOB, NUMPEDCLI, CODUSUR
    FROM crc.PCPEDC
""", con=engine, dtype=str)
tabela_inad = pd.read_sql("""
    SELECT codcli, valor_nota
    FROM crc.PBI_PCINAD
    GROUP BY codcli, valor_nota
""", con=engine,dtype=str)

# tabela_inad = tabela_inad.groupby('codcli').agg({
#     'valor_nota': 'sum'
# }).reset_index()
tabela_cliente['cgcent'] = tabela_cliente['cgcent'].str.replace(r'\D', '', regex=True)
tabela_cliente = tabela_cliente.merge(tabela_inad,left_on='codcli',right_on='codcli',how='left')
caminho = r'C:\HBox\MEU DRIVE\BEES'
arquivos_csv = [f for f in os.listdir(caminho) if f.endswith('.csv') and 'Pedidos_A_Preparar' in f]
df_list = [pd.read_csv(os.path.join(caminho, f), dtype=str) for f in arquivos_csv]
arquivo_pedidos = pd.concat(df_list, ignore_index=True) 

colunas_descartar = [
    'Data Pedido', 'Status', 'Data Entrega', 'Responsavel', 'CEP',
    'Coordenadas', 'ID do negócio', 'ID da conta do cliente', 'IE',
    'Quantidade Preparar', 'Email 1', 'Email 2', 
       'Responsavel', 'Nome Comercial', 'Endereço de Entrega',
       'Cidade/UF', 'SKU', 'Preço', 'Quantidade Pedida', 'Nome do Produto',
       'Telefone 1', 'Telefone 2'
]
arquivo_pedidos.drop(columns=colunas_descartar, inplace=True, errors='ignore')
arquivo_pedidos = arquivo_pedidos.merge(tabela_edc,left_on='Numero Pedido',right_on='numpedcli',how='left')
arquivo_pedidos = arquivo_pedidos[
    arquivo_pedidos['Centro de Distribuição'].isin(['CASTAS RJ', 'RIGARRRJCAPITAL'])
]
arquivo_pedidos = arquivo_pedidos[
        arquivo_pedidos['Documento'].str.contains('CNPJ',na=False)
 ]
arquivo_pedidos['Forma de Pagamento'] = arquivo_pedidos['Forma de Pagamento'].replace({
    'Cartão de Crédito na Entrega (Somente em 1x)': 'CARC',
    'Cartão de Débito na Entrega': 'CARD',
    'Dinheiro': 'D',
    'Pix na entrega': 'PIX'
})

arquivo_pedidos['Total Pedido'] = (
    arquivo_pedidos['Total Pedido']
    .astype(str)
    .str.replace('$', '', regex=False)
    .str.replace(',', '', regex=False)
)
arquivo_pedidos['Tipo Documento'] = arquivo_pedidos['Documento'].str.split(':').str[0]
arquivo_pedidos['Numero Documento'] = arquivo_pedidos['Documento'].str.split(':').str[1].str.strip()
arquivo_pedidos.drop(columns=['Documento','Tipo Documento'], inplace=True, errors='ignore')
arquivo_pedidos.drop_duplicates(['Numero Documento'],inplace=True)
arquivo_pedidos['Numero Documento'] = arquivo_pedidos['Numero Documento'].str.strip()
arquivo_pedidos['Centro de Distribuição'] = arquivo_pedidos['Centro de Distribuição'].replace({'RIGARRRJCAPITAL': 'CRC'})
arquivo_pedidos = arquivo_pedidos.merge(
    tabela_cliente,
    left_on='Numero Documento',  
    right_on='cgcent',          
    how='left'
)
arquivo_pedidos.drop(columns=['Numero Documento','cgcent'], inplace=True)
arquivo_pedidos['Total Pedido'] = arquivo_pedidos['Total Pedido'].astype(float)
arquivo_pedidos['limcred'] = arquivo_pedidos['limcred'].astype(float)
arquivo_pedidos = arquivo_pedidos[arquivo_pedidos['numpedcli'].isna()]
arquivo_pedidos = arquivo_pedidos.groupby('codcli').agg({
    'Total Pedido': 'sum',           
    'bloqueio': 'first',         
    'limcred': 'first',                
    'Centro de Distribuição': 'first',
    'valor_nota':'first',
    'Forma de Pagamento':'first',
    'motivobloq':'first'  
}).reset_index()
arquivo_pedidos['valor_nota'] = pd.to_numeric(arquivo_pedidos['valor_nota'], errors='coerce').fillna(0)

arquivo_pedidos['Limite Disponível'] = arquivo_pedidos['limcred']-arquivo_pedidos['valor_nota']
arquivo_pedidos = arquivo_pedidos[
    (arquivo_pedidos['Limite Disponível'] < arquivo_pedidos['Total Pedido']) |
    (arquivo_pedidos['bloqueio'] == 'S') ]

arquivo_pedidos.drop(columns=['bloqueio','limcred','valor_nota','Limite Disponível','motivobloq'],inplace=True)
arquivo_pedidos.style.hide(axis="index").format(precision=2)