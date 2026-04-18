import os
import re
import pandas as pd
import oracledb
from sqlalchemy import create_engine
from dotenv import load_dotenv
import db

load_dotenv()
db.criar_tabelas()

oracle_client_dir = os.getenv("ORACLE_CLIENT_DIR", "/opt/instantclient")
try:
    oracledb.init_oracle_client(lib_dir=oracle_client_dir)
except Exception:
    pass

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

FILIAIS = [
    {"nome": "Rigarr", "dsn": os.getenv("DSN_RJ"), "schema": "crc"},
    {"nome": "Castas", "dsn": os.getenv("DSN_RJ"), "schema": "crc"},
    {"nome": "SP",     "dsn": os.getenv("DSN_SP"), "schema": "spon"},
    {"nome": "MG",     "dsn": os.getenv("DSN_MG"), "schema": "mgon"},
    {"nome": "ES",     "dsn": os.getenv("DSN_ES"), "schema": "CRC"},
]

todos_pedidos = db.get_todos_pedidos()
if not todos_pedidos:
    print("Sem pedidos no banco.")
    exit(0)

df_pedidos = pd.DataFrame(todos_pedidos)
df_pedidos["cnpj_limpo"] = df_pedidos["documento"].str.replace(r'\D', '', regex=True)

dsn_processados = set()

for filial in FILIAIS:
    dsn = filial["dsn"]
    schema = filial["schema"]
    nome = filial["nome"]

    if not dsn:
        continue

    # Para cada DSN único, busca todos os pedidos das filiais que usam esse DSN
    filiais_do_dsn = [f["nome"] for f in FILIAIS if f["dsn"] == dsn]

    if dsn not in dsn_processados:
        try:
            engine = create_engine(f'oracle+oracledb://{DB_USER}:{DB_PASSWORD}@{dsn}')
            tabela_cliente = pd.read_sql(
                f"SELECT codcli, cgcent FROM {schema}.PCCLIENT",
                con=engine, dtype=str
            )
        except Exception as e:
            print(f"[{nome}] Erro ao conectar Oracle: {e}")
            dsn_processados.add(dsn)
            continue

        tabela_cliente["cgcent"] = tabela_cliente["cgcent"].str.replace(r'\D', '', regex=True)
        mapa_cnpj = dict(zip(tabela_cliente["cgcent"], tabela_cliente["codcli"]))
        dsn_processados.add(dsn)

        for filial_nome in filiais_do_dsn:
            df_sub = df_pedidos[df_pedidos["filial"] == filial_nome].copy()
            if df_sub.empty:
                continue

            # mapa numero_pedido → codcli
            pedido_codcli = {}
            for _, row in df_sub.drop_duplicates("numero_pedido").iterrows():
                cnpj = row["cnpj_limpo"]
                if cnpj and cnpj in mapa_cnpj:
                    pedido_codcli[row["numero_pedido"]] = mapa_cnpj[cnpj]

            db.atualizar_codcli(pedido_codcli)
            print(f"[{filial_nome}] {len(pedido_codcli)} pedidos com codcli atualizado.")

print("Consulta codcli concluída.")
