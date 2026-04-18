import sys
import traceback
import subprocess
from datetime import datetime

def step(nome):
    print(f"\n{'-' * 50}")
    print(f"  {nome}")
    print(f"{'-' * 50}")

def main():
    inicio = datetime.now()
    print(f"\n{'='*50}")
    print(f" BEES - {inicio.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")

    import db
    db.criar_tabelas()

    try:
        step("Coletando Pedidos BEES")
        subprocess.run([sys.executable, "coletar_pedidos.py"], check=True)  
        step("Consulta CNPJ")
        subprocess.run([sys.executable, "consulta_cnpj.py"], check=True)
        step("Consulta Cod Cliente (PCCLIENT)")
        subprocess.run([sys.executable, "consulta_codcli.py"], check=True)
        step("Cancelar CPF")
        subprocess.run([sys.executable, "cancela_cpf.py"], check=True)
        step("Cancela CNPJ Invalido")
        subprocess.run([sys.executable, "cancela_pendencia_fiscal.py"], check=True)
        step("Enviando Pedido Para BIB Angra")
        subprocess.run([sys.executable, "envio_pedidos_bib.py"], check=True)
        step("Baixando Pedido Para BIB Angra")
        subprocess.run([sys.executable, "preparar_pedido_bib.py"], check=True)
        step("Pedir Limite")
        subprocess.run([sys.executable, "pedir_limite.py"], check=True)
        
    except Exception:
        print("\n[ERRO] Falha na execução:")
        traceback.print_exc()
        sys.exit(1)

    fim = datetime.now()
    duracao = (fim - inicio).seconds
    print(f"\n{'='*50}")
    print(f"  Concluído em {duracao}s")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
