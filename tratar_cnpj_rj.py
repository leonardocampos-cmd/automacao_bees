# TRATAR DADOS CADASTROS
import os

import pandas as pd
import oracledb
from sqlalchemy import create_engine

oracledb.init_oracle_client(lib_dir=r"C:\instantclient")


def tratar_cnpj_rj(base_dir: str | None = None):
    """Processa os resultados da consulta de CNPJ e prepara os dados finais.

    Args:
        base_dir: Diretório base do projeto. Se None, usa o diretório deste arquivo.
    """

    if base_dir is None:
        base_dir = os.path.dirname(__file__)

    # Diretórios padrão
    relatorios_dir = os.path.join(base_dir, "relatorios")
    arquivo_cnpjs = os.path.join(relatorios_dir, "resultados_consulta_cnpj_api.csv")

    user = "vpn"
    password = "vpn2320vpn"
    dsn = "crc_oci"

    engine = create_engine(f"oracle+oracledb://{user}:{password}@{dsn}")

    tabela_ativ = pd.read_sql(
        """
        SELECT CODATIV, RAMO
        FROM crc.PCATIVI
    """,
        con=engine,
    )
    tabela_cliente = pd.read_sql(
        """
        SELECT codcli, CGCENT
        FROM crc.PCCLIENT
    """,
        con=engine,
    )

    tabela_praca = pd.read_sql(
        """
        SELECT CODPRACA, PRACA, SITUACAO
        FROM crc.PCPRACA
    """,
        con=engine,
        dtype=str,
    )

    arquivo_cnpjs = pd.read_csv(
        arquivo_cnpjs,
        sep=",",
        encoding="utf-8",
        dtype=str,
    )

    arquivos_csv = [
        f
        for f in os.listdir(relatorios_dir)
        if f.endswith(".csv") and "Pedidos_A_Preparar_" in f
    ]

    df_list = [
        pd.read_csv(os.path.join(relatorios_dir, f), dtype=str) for f in arquivos_csv
    ]
    arquivo_pedidos = pd.concat(df_list, ignore_index=True)

    arquivo_cnpjs.drop(columns=[
        'Arquivo', 'Capital Social', 'Natureza Jurídica', 'Data de Fundação',
        'Data de Status', 'Razão de Status', 'Simples Nacional Desde',
        'SIMEI Desde', 'Inscrição Estadual Estado', 'Inscrição Estadual Tipo',
        'Inscrição Estadual Data de Status'
    ], inplace=True)

    arquivo_cnpjs['Nome Fantasia'] = arquivo_cnpjs['Nome Fantasia'].fillna(arquivo_cnpjs['Nome'])

    arquivo_cnpjs = arquivo_cnpjs[arquivo_cnpjs['Status'] == 'Ativa']

    cidades_interior = [
        'PATY DO ALFERES','VALENCA','ITATIAIA', 'RESENDE', 'PORTO REAL', 'QUATIS',
        'BARRA MANSA', 'VOLTA REDONDA', 'ARROZAL', 'PINHEIRAL', 'PIRAI',
        'BARRA DO PIRAI', 'MENDES', 'VASSOURA', 'RIO CLARO', 'CACHOEIRAS DE MACACU',
        'MIGUEL PEREIRA', 'TANGUA', 'Barra do Piraí', 'SAO JOSE DO VALE DO RIO PRETO',
        'Barra do Pirai', 'Areal', 'AREAL', 'PARAÍBA DO SUL', 'ANGRA DOS REIS','SAPUCAIA','PARATY']

    arquivo_cnpjs = arquivo_cnpjs[arquivo_cnpjs['Cidade/UF'].str.contains('/RJ', na=False)]
    tabela_praca = tabela_praca[tabela_praca['situacao'] == 'A']
    cidades_upper = [c.upper() for c in cidades_interior]
    arquivo_cnpjs = arquivo_cnpjs[
        ~arquivo_cnpjs['Cidade/UF'].str.split('/').str[0].str.upper().isin(cidades_upper)
    ]

    arquivo_cnpjs['País'] = arquivo_cnpjs['País'].replace('Brasil', '1058')
    arquivo_cnpjs['Atividade Principal'] = arquivo_cnpjs['Atividade Principal'].replace({'Comércio varejista de bebidas':'COMERCIO VAREJISTA DE BEBIDAS','Restaurantes e similares':'RESTAURANTE','Serviços de lavagem, lubrificação e polimento de veículos automotores':'SERVICO DE MECANICA','Bares e outros estabelecimentos especializados em servir bebidas':'BAR','Padaria e confeitaria com predominância de revenda':'PADARIA','Lanchonetes, casas de chá, de sucos e similares':'CAFE/LANCHONETE','Representantes comerciais e agentes do comércio de mercadorias em geral não especializado':'OUTROS','Bares e outros estabelecimentos especializados em servir bebidas, com entretenimento':'BAR','Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - minimercados, mercearias e armazéns':'MERCEARIA','Comércio varejista de mercadorias em lojas de conveniência':'LOJAS DE CONVENIENCIA/ VARIEDADES','Serviços de organização de feiras, congressos, exposições e festas':'SERVICOS DE ORGANIZACAO DE FEIRAS, CONGR','Comércio atacadista de mercadorias em geral, sem predominância de alimentos ou de insumos agropecuários':'SUPERMERCADO','Comércio varejista de carnes - açougues':'ACOUGUE','Fornecimento de alimentos preparados preponderantemente para consumo domiciliar':'OUTROS','Serviços de malote não realizados pelo Correio Nacional':'TRANSPORTADOR','Transporte rodoviário de mudanças':'TRANSPORTADOR','Bares e outros estabelecimentos especializados em servir bebidas, sem entretenimento':'BAR','Comércio varejista de hortifrutigranjeiros':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de cosméticos, produtos de perfumaria e de higiene pessoal':'COMERCIO VAREJISTA (GERAL)','Serviços de entrega rápida':'DELIVERY','Hotéis':'HOTEL','Comércio varejista de animais vivos e de artigos e alimentos para animais de estimação':'PET SHOP','Comércio varejista de produtos alimentícios em geral ou especializado em produtos alimentícios não especificados anteriormente':'COMERCIO VAREJISTA (GERAL)','Tabacaria':'TABACARIA','Comércio varejista de combustíveis para veículos automotores':'POSTO DE GASOLINA','Comércio varejista de artigos do vestuário e acessórios':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de laticínios e frios':'COMERCIO VAREJISTA (GERAL)','Instalação e manutenção elétrica':'OUTROS','Serviços ambulantes de alimentação':'QUIOSQUE','Obras de alvenaria':'CONSTRUCAO DE EDIFICIOS','Peixaria':'ACOUGUE/PEIXARIA','Instalação de máquinas e equipamentos industriais':'OUTROS','Fabricação de produtos de panificação industrial':'PADARIA','Comercio varejista de artigos de armarinho':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de outros produtos não especificados anteriormente':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de artigos de papelaria':'COMERCIO VAREJISTA (GERAL)','Organização logística do transporte de carga':'TRANSPORTADOR','Atividades de fornecimento de infra-estrutura de apoio e assistência a paciente no domicílio':'OUTROS','Comércio varejista de materiais de construção em geral':'COMERCIO VAREJISTA (GERAL)','Aluguel de móveis, utensílios e aparelhos de uso doméstico e pessoal; instrumentos musicais':'OUTROS','Fabricação de produtos de carne':'ACOUGUE/PEIXARIA',"Comércio varejista de produtos farmacêuticos, sem manipulação de fórmulas":'COMERCIO VAREJISTA (GERAL)','Coleta de resíduos não-perigosos':'OUTROS','Lojas de variedades, exceto lojas de departamentos ou magazines':'LOJAS DE CONVENIENCIA/ VARIEDADES','Fabricação de alimentos e pratos prontos':"FABRICA","Cantinas - serviços de alimentação privativos":"CANTINAS","Comércio varejista de doces, balas, bombons e semelhantes":'COMERCIO VAREJISTA (GERAL)','Pensões (alojamento)':'HOSTEL','Serviços de alimentação para eventos e recepções - bufê':'BUFFET','Correspondentes de instituições financeiras':"OUTROS",'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - supermercados':'SUPERMERCADO','Clubes sociais, esportivos e similares':'CLUBE ESPORTIVO','Serviços de borracharia para veículos automotores':'OFICINA MECANICA','Fornecimento de alimentos preparados preponderantemente para empresas':'OUTROS','Construção de edifícios':'OUTROS','Outras atividades de serviços prestados principalmente às empresas não especificadas anteriormente':'OUTROS','Transporte rodoviário de carga, exceto produtos perigosos e mudanças, municipal.':'TRANSPORTADOR','Aluguel de equipamentos recreativos e esportivos':'OUTROS','Comércio varejista de bebidas em geral ou especializado em tipos de bebidas não especificados anteriormente':'COMERCIO VAREJISTA DE BEBIDAS','Comércio varejista de produtos alimentícios em lojas de conveniência':'LOJAS DE CONVENIENCIA/ VARIEDADES','Albergues, exceto assistenciais':'HOSTEL','Comércio varejista de produtos de padaria e confeitaria com predominância de revenda':'PADARIA','Comércio varejista de jornais e revistas':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de produtos alimentícios em geral ou especializado em produtos alimentícios não especificados anteriormente':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de artigos do vestuário e acessórios':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de mercadorias em lojas de conveniência':'LOJAS DE CONVENIENCIA/ VARIEDADES','Comércio varejista de cosméticos, produtos de perfumaria e de higiene pessoal':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de combustíveis para veículos automotores':'POSTO DE GASOLINA','Comércio varejista de produtos farmacêuticos, sem manipulação de fórmulas':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de materiais de construção em geral':'COMERCIO VAREJISTA (GERAL)','Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - supermercados':'SUPERMERCADO','Guarda-móveis':'OUTROS','Condomínios prediais':'OUTROS','Fabricação de produtos de padaria e confeitaria com predominância de produção própria':'PADARIA','Fabricação de vinho':'FABRICA','Atividades de limpeza não especificadas anteriormente':'OUTROS','Fabricação de escovas, pincéis e vassouras':'OUTROS'})
    tabela_ativ.columns = tabela_ativ.columns.str.strip().str.upper()
    tabela_ativ['CODATIV'] = tabela_ativ['CODATIV'].astype(str)
    arquivo_cnpjs.columns = arquivo_cnpjs.columns.str.strip()
    arquivo_cnpjs = arquivo_cnpjs.merge(tabela_ativ, left_on='Atividade Principal', right_on='RAMO', how='left')
    arquivo_cnpjs.drop(columns=['RAMO','Atividades Secundárias'], inplace=True)
    arquivo_cnpjs['CNPJ'] = arquivo_cnpjs['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)
    tabela_cliente['cgcent'] = tabela_cliente['cgcent'].astype(str).str.replace(r'\D', '', regex=True)    
    arquivo_cnpjs = arquivo_cnpjs.merge(tabela_cliente, left_on='CNPJ', right_on='cgcent', how='left')
    arquivo_cnpjs.drop(columns=['cgcent', 'Status'], inplace=True)
    arquivo_cnpjs = arquivo_cnpjs[arquivo_cnpjs['codcli'].isna()]
    arquivo_cnpjs['CIDADE'] = arquivo_cnpjs['Cidade/UF'].str.split('/').str[0]  
    arquivo_cnpjs['UF'] = arquivo_cnpjs['Cidade/UF'].str.split('/').str[1]
    tabela_praca.columns = tabela_praca.columns.str.strip().str.upper()
    arquivo_cnpjs.columns = arquivo_cnpjs.columns.str.strip().str.upper()
    arquivo_cnpjs.drop(columns=['CIDADE/UF'], inplace=True)
    arquivo_cnpjs['SIMEI OPTANTE'] = arquivo_cnpjs['SIMEI OPTANTE'].astype(str)
    arquivo_cnpjs['SIMPLES NACIONAL OPTANTE'] = arquivo_cnpjs['SIMPLES NACIONAL OPTANTE'].astype(str)
    arquivo_cnpjs['TIPO EMPRESA'] = arquivo_cnpjs.apply(
        lambda row: "Microempreendedor" if row['SIMEI OPTANTE'] == "True"
                    else ("Simples" if row['SIMPLES NACIONAL OPTANTE'] == "True"
                            else row['TAMANHO']),
        axis=1
    )   
    arquivo_cnpjs['TIPO EMPRESA'] = arquivo_cnpjs['TIPO EMPRESA'].replace('Demais','Outros')
    arquivo_cnpjs['TIPO EMPRESA'] = arquivo_cnpjs['TIPO EMPRESA'].astype(str)
    arquivo_cnpjs.drop(columns=['SIMEI OPTANTE', 'SIMPLES NACIONAL OPTANTE', 'TAMANHO','CODCLI','UF'], inplace=True)
    arquivo_cnpjs['CIDADE'] = arquivo_cnpjs['CIDADE'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.strip().str.upper()
    arquivo_cnpjs['BAIRRO'] = arquivo_cnpjs['BAIRRO'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.strip().str.upper()
    tabela_praca['PRACA'] = tabela_praca['PRACA'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.strip().str.upper()
    tabela_praca['PRACA'] = tabela_praca['PRACA'].str.upper()
    tabela_praca = tabela_praca[~tabela_praca['PRACA'].str.upper().str.contains('INATIV[AO]', regex=True)]
    #remover acento das paladas praca e arquivo cnps
    arquivo_cnpjs['BAIRRO'] = arquivo_cnpjs['BAIRRO'].replace('É','E')
    tabela_praca['PRACA'] = tabela_praca['PRACA'].replace('É','E')
    if (arquivo_cnpjs['CIDADE'] == 'Rio de Janeiro').any():
        
        arquivo_cnpjs = arquivo_cnpjs.merge(tabela_praca, left_on='BAIRRO', right_on='PRACA', how='left')
    else:
        arquivo_cnpjs = arquivo_cnpjs.merge(tabela_praca, left_on='CIDADE', right_on='PRACA', how='left')
    arquivo_cnpjs.drop(columns=['PRACA','ATIVIDADE PRINCIPAL'], inplace=True)
    arquivo_cnpjs['TELEFONE'] = arquivo_cnpjs['TELEFONE'].astype(str).str.replace(r'\D', '', regex=True)
    arquivo_cnpjs['INSCRIÇÃO ESTADUAL NÚMERO'] = arquivo_cnpjs['INSCRIÇÃO ESTADUAL NÚMERO'].str.replace('Não encontrada','ISENTO')
    arquivo_cnpjs['EMAIL'] = arquivo_cnpjs['EMAIL'].str.replace('Não disponível','teste@teste.com')
    arquivo_cnpjs['RCA'] = '437'
    arquivo_cnpjs['TELEFONE'] = arquivo_cnpjs['TELEFONE'].replace('', '21999999999')
    arquivo_cnpjs['COMPLEMENTO'] = arquivo_cnpjs['COMPLEMENTO'].fillna('.')
    arquivo_cnpjs = arquivo_cnpjs.drop_duplicates(subset='CNPJ')
    # Observe os colchetes duplos [[ ]]
    arquivo_cnpjs = arquivo_cnpjs.merge(
        arquivo_pedidos[['Endereço de Entrega', 'Cidade/UF', 'CEP', 'ID da conta do cliente']], 
        left_on='CNPJ', 
        right_on='ID da conta do cliente'
    )
    if arquivo_cnpjs.empty:
        print("Nenhum CNPJ do arquivo_cnpjs corresponde ao ID da conta do cliente no arquivo_pedidos.")
    else:
        cols = ["Rua", "Número", "Complemento", "Bairro", "Cidade", "UF"]
        def dividir_endereco(endereco):
            # Se o endereço for nulo ou não for string, retorna 6 pontos
            if not isinstance(endereco, str) or endereco.strip() == "":
                return [".", ".", ".", ".", ".", "."]

            partes = [p.strip() for p in endereco.split(",")]

            # Se tiver 5 partes: insere "." no Complemento (índice 2)
            if len(partes) == 5:
                partes.insert(2, ".")
            
            # Ajusta para garantir EXATAMENTE 6 elementos
            if len(partes) < 6:
                partes.extend(["."] * (6 - len(partes)))
            
            return partes[:6]

        # Aplicação garantindo o formato de colunas
        # Remova o result_type='expand' e converta o resultado em uma lista/DataFrame
        res_endereco = arquivo_cnpjs["Endereço de Entrega"].apply(dividir_endereco)
        arquivo_cnpjs[cols] = pd.DataFrame(res_endereco.tolist(), index=arquivo_cnpjs.index)
        arquivo_cnpjs.drop_duplicates('CNPJ', inplace=True)
        arquivo_cnpjs.to_csv(os.path.join(relatorios_dir, "dados_tratados_cnpj_rj.csv"), index=False, encoding='utf-8')
    return arquivo_cnpjs