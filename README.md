# Automação Bees

Este projeto automatiza processos relacionados ao sistema Bees, incluindo coleta de pedidos, cancelamento de pedidos com CPF inválido, consulta de CNPJ via API e tratamento de dados para o estado do Rio de Janeiro (RJ).

## Estrutura do Projeto

```
automacao_bees/
├── main.py                    # Script principal que orquestra toda a rotina
├── coletar_pedidos_preparar.py # Coleta pedidos ativos dos sites Bees
├── cancela_cpf.py             # Cancela pedidos com CPF inválido
├── consulta_cnpj.py           # Consulta CNPJ via API CNPJA
├── tratar_cnpj_rj.py          # Trata e filtra dados CNPJ para RJ
├── requirements.txt           # Dependências Python
├── relatorios/                # Pasta com arquivos CSV gerados
│   ├── Pedidos_A_Preparar_*.csv
│   ├── resultados_consulta_cnpj_api.csv
│   └── dados_tratados_cnpj_rj.csv
└── README.md                  # Este arquivo
```

## Lógica do Projeto

### Rotina Principal (main.py)

A rotina é executada em 4 passos sequenciais:

1. **Coleta de Dados**: Executa `coletar_pedidos_preparar.py` para coletar pedidos ativos dos sites Bees (filiais Rigarr e Castas). Salva em CSV na pasta `relatorios/`.

2. **Cancelamento de CPF**: Verifica se há pedidos elegíveis para cancelamento (com CPF inválido). Se houver, executa `cancela_cpf.py` para cancelar esses pedidos.

3. **Consulta de CNPJ**: Executa `consulta_cnpj.py` para consultar CNPJ dos pedidos via API CNPJA. Processa arquivos CSV em `relatorios/`, consulta CNPJs únicos, salva resultados em `resultados_consulta_cnpj_api.csv`.

4. **Tratamento de Dados CNPJ RJ**: Executa `tratar_cnpj_rj.py` para processar os dados consultados. Filtra para empresas ativas no RJ (excluindo interior), faz merges com tabelas Oracle (atividades, clientes, praças), normaliza dados e salva em `dados_tratados_cnpj_rj.csv`.

### Detalhes dos Scripts

#### coletar_pedidos_preparar.py
- Faz login nos sites Bees das filiais Rigarr e Castas
- Coleta pedidos ativos (status "A Preparar")
- Salva em CSV por filial: `Pedidos_A_Preparar_[Filial].csv`
- Limpa pedidos inativos existentes

#### cancela_cpf.py
- Função `preparar_dados()`: Lê CSVs de pedidos, identifica pedidos com CPF inválido
- Função `cancelar_pedidos()`: Cancela pedidos via interface web Bees

#### consulta_cnpj.py
- Lê arquivos CSV de pedidos em `relatorios/`
- Extrai CNPJs únicos (coluna "ID da conta do cliente")
- Consulta API CNPJA com controle de taxa (20/min)
- Salva dados detalhados da empresa em CSV

#### tratar_cnpj_rj.py
- Lê `resultados_consulta_cnpj_api.csv`
- Filtra empresas ativas no RJ (excluindo cidades do interior)
- Mapeia atividades para códigos Oracle
- Merge com tabelas Oracle: PCATIVI (atividades), PCCLIENT (clientes), PCPRACA (praças)
- Filtra clientes não cadastrados
- Trata endereços, telefones, emails
- Salva dados finais para importação

## Cancelamento de Pendências Fiscais

O projeto possui uma rotina para identificar e cancelar pendências fiscais de clientes/pedidos. Os dados são processados e salvos em `relatorios/pendencias_fiscais.csv`.

No painel Streamlit, há uma página específica chamada **Pendências**, onde é possível visualizar todas as pendências fiscais encontradas.

### Lógica

- Identifica pedidos/clientes com pendências fiscais
- Cancela ou sinaliza conforme regras do negócio
- Salva os resultados em CSV para consulta
- Exibe no painel para acompanhamento

### Integração no fluxo principal

O passo de cancelamento de pendências fiscais pode ser chamado no `main.py` após o tratamento de dados RJ, garantindo que todas as pendências sejam processadas e registradas.

## Painel Interativo (Streamlit)

O projeto possui um painel web interativo para visualização dos pedidos, dividido em páginas:

- **Início**: Mostra todos os pedidos coletados.
- **CRC**: Filtra pedidos dos centros de distribuição RIGARRRJCAPITAL, CASTAS RJ, RIGARRESCAPITAL, CASTAES.
- **SPON**: Filtra pedidos dos centros RIGARRSPCAPITAL, CASTAS SP.
- **MGON**: Filtra pedidos dos centros RIGARRMGCAPITAL, CASTAS MG.

O painel é construído com Streamlit e lê os arquivos CSV gerados pela rotina principal. Permite navegação fácil entre as páginas e visualização dos dados em tabelas.

### Lógica do Projeto

1. **Coleta de pedidos**: Automatiza login e coleta dos pedidos ativos de cada filial, salvando em CSV.
2. **Cancelamento de pedidos**: Identifica e cancela pedidos com CPF inválido.
3. **Consulta de CNPJ**: Consulta dados de CNPJ via API, salvando resultados detalhados.
4. **Tratamento de dados RJ**: Filtra e prepara dados para importação, cruzando com tabelas Oracle.
5. **Painel Streamlit**: Permite visualizar todos os dados, com filtros por centro de distribuição.

### Como executar o painel

1. Ative o ambiente virtual:
   ```
   & "c:/Users/LeonardoCampos/Meu Drive/automacao_bees/.venv/Scripts/Activate.ps1"
   ```
2. Execute:
   ```
   streamlit run painel.py
   ```

O painel será aberto no navegador, mostrando as páginas e filtros conforme a lógica acima.

## Dependências

- Python 3.11+
- Ambiente virtual (.venv)
- Oracle Instant Client (para conexão Oracle)
- Pacotes: selenium, pandas, python-dotenv, oracledb, sqlalchemy

## Como Executar

1. Ativar ambiente virtual:
   ```
   & "c:/Users/LeonardoCampos/Meu Drive/automacao_bees/.venv/Scripts/Activate.ps1"
   ```

2. Instalar dependências:
   ```
   pip install -r requirements.txt
   ```

3. Executar rotina principal:
   ```
   python main.py
   ```

## Configurações

- **API CNPJ**: Chave hardcoded em `consulta_cnpj.py` (recomenda usar .env)
- **Oracle**: Credenciais hardcoded em `tratar_cnpj_rj.py` (recomenda usar .env)
- **Diretórios**: `relatorios/` para CSVs
- **Oracle Client**: Path hardcoded `C:\instantclient`

## Logs

Logs são exibidos no console com níveis INFO/ERROR.

## Notas

- Scripts usam Selenium para automação web
- Consultas CNPJ respeitam limite de taxa da API
- Dados finais filtrados para RJ capital (excluindo interior)
- Arquivos CSV salvos em UTF-8