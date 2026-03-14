import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Painel Bees", layout="wide")
st.title("Painel de Pedidos Bees")

relatorios_dir = os.path.join(os.path.dirname(__file__), "relatorios")

# Pedidos
arquivos_pedidos = [
    f for f in os.listdir(relatorios_dir)
    if f.startswith("Pedidos_A_Preparar_") and f.endswith(".csv")
]
df_list = [
    pd.read_csv(os.path.join(relatorios_dir, f), dtype=str)
    for f in arquivos_pedidos
]
if df_list:
    pedidos = pd.concat(df_list, ignore_index=True)
    st.subheader(f"Pedidos encontrados: {len(pedidos)}")
    st.dataframe(pedidos, use_container_width=True)
else:
    st.warning("Nenhum pedido encontrado nos arquivos.")

# CNPJ
cnpj_path = os.path.join(relatorios_dir, "resultados_consulta_cnpj_api.csv")
if os.path.exists(cnpj_path):
    cnpj_df = pd.read_csv(cnpj_path, dtype=str)
    st.subheader(f"Consultas de CNPJ: {len(cnpj_df)}")
    st.dataframe(cnpj_df, use_container_width=True)
else:
    st.info("Arquivo de resultados de consulta CNPJ não encontrado.")

# Dados tratados RJ
tratado_path = os.path.join(relatorios_dir, "dados_tratados_cnpj_rj.csv")
if os.path.exists(tratado_path):
    tratado_df = pd.read_csv(tratado_path, dtype=str)
    st.subheader(f"Dados tratados RJ: {len(tratado_df)}")
    st.dataframe(tratado_df, use_container_width=True)
else:
    st.info("Arquivo de dados tratados RJ não encontrado.")
