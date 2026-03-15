import streamlit as st
import pandas as pd
import os
import subprocess
import sys

st.set_page_config(page_title="Painel Bees", layout="wide")
st.title("Painel de Pedidos Bees")

pagina = st.sidebar.radio(
    "Escolha a página:",
    ("Início", "CRC", "SPON", "MGON", "Pendências")
)

relatorios_dir = os.path.join(os.path.dirname(__file__), "relatorios")

# Carregar pedidos
arquivos_pedidos = [
    f for f in os.listdir(relatorios_dir)
    if f.startswith("Pedidos_A_Preparar_") and f.endswith(".csv")
]
df_list = [
    pd.read_csv(os.path.join(relatorios_dir, f), dtype=str)
    for f in arquivos_pedidos
]
pedidos = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

if pagina == "Início":
    st.title("Painel de Pedidos Bees - Início")
    st.subheader(f"Pedidos encontrados: {len(pedidos)}")
    st.dataframe(pedidos, use_container_width=True)
    python_path = os.path.join(os.path.dirname(sys.executable), "python.exe")
    if st.button("Executar rotina principal (main.py)"):
        with st.spinner("Executando rotina principal..."):
            st.info("[LOG] Iniciando execução do main.py...")
            result = subprocess.run([python_path, "main.py"], capture_output=True, text=True)
            st.success("Rotina principal executada!")
            st.info("[LOG] Saída do main.py:")
            for linha in result.stdout.splitlines():
                st.write(linha)
            if result.stderr:
                st.error("[LOG] Erro:")
                for linha in result.stderr.splitlines():
                    st.write(linha)

elif pagina == "CRC":
    st.title("Pedidos CRC")
    centros_crc = ["RIGARRRJCAPITAL", "CASTAS RJ", "RIGARRESCAPITAL", "CASTAES"]
    pedidos_crc = pedidos[pedidos["Centro de Distribuição"].isin(centros_crc)]
    st.subheader(f"Pedidos CRC: {len(pedidos_crc)}")
    st.dataframe(pedidos_crc, use_container_width=True)

elif pagina == "SPON":
    st.title("Pedidos SPON")
    centros_spon = ["RIGARRSPCAPITAL", "CASTAS SP"]
    pedidos_spon = pedidos[pedidos["Centro de Distribuição"].isin(centros_spon)]
    st.subheader(f"Pedidos SPON: {len(pedidos_spon)}")
    st.dataframe(pedidos_spon, use_container_width=True)

elif pagina == "MGON":
    st.title("Pedidos MGON")
    centros_mgon = ["RIGARRMGCAPITAL", "CASTAS MG"]
    pedidos_mgon = pedidos[pedidos["Centro de Distribuição"].isin(centros_mgon)]
    st.subheader(f"Pedidos MGON: {len(pedidos_mgon)}")
    st.dataframe(pedidos_mgon, use_container_width=True)

elif pagina == "Pendências":
    st.title("Pendências Fiscais")
    pendencias_path = os.path.join(relatorios_dir, "pendencias_fiscais.csv")
    if os.path.exists(pendencias_path):
        pendencias_df = pd.read_csv(pendencias_path, dtype=str)
        st.subheader(f"Pendências fiscais: {len(pendencias_df)}")
        st.dataframe(pendencias_df, use_container_width=True)
    else:
        st.info("Arquivo de pendências fiscais não encontrado.")