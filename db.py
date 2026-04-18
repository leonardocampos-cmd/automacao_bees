import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import date
from dotenv import load_dotenv

load_dotenv()

_CNPJ_COL_MAP = {
    'CNPJ': 'cnpj',
    'Nome': 'nome',
    'Nome Fantasia': 'nome_fantasia',
    'Capital Social': 'capital_social',
    'Natureza Jurídica': 'natureza_juridica',
    'Tamanho': 'tamanho',
    'Data de Fundação': 'data_fundacao',
    'Status': 'status',
    'Data de Status': 'data_status',
    'Razão de Status': 'razao_status',
    'Rua': 'rua',
    'Número': 'numero',
    'Complemento': 'complemento',
    'Bairro': 'bairro',
    'Cidade': 'cidade',
    'UF': 'uf',
    'CEP': 'cep',
    'Telefone': 'telefone',
    'Email': 'email',
    'Atividade Principal': 'atividade_principal',
    'Atividades Secundárias': 'atividades_secundarias',
    'Simples Nacional Optante': 'simples_optante',
    'SIMEI Optante': 'simei_optante',
    'Inscrição Estadual Estado': 'ie_estado',
    'Inscrição Estadual Número': 'ie_numero',
    'Inscrição Estadual Status': 'ie_status',
    'Inscrição Estadual Tipo': 'ie_tipo',
    'Inscrição Estadual Data de Status': 'ie_data_status',
}


def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", 5432)),
        dbname=os.getenv("PG_DB", "bees"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


@contextmanager
def cursor():
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def criar_tabelas():
    with cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pedidos_itens (
                id                  SERIAL PRIMARY KEY,
                filial              TEXT NOT NULL,
                numero_pedido       TEXT NOT NULL,
                data_pedido         TEXT,
                centro_distribuicao TEXT,
                status              TEXT,
                forma_pagamento     TEXT,
                data_entrega        TEXT,
                responsavel         TEXT,
                total_pedido        TEXT,
                documento           TEXT,
                ie                  TEXT,
                nome_comercial      TEXT,
                endereco_entrega    TEXT,
                cidade_uf           TEXT,
                cep                 TEXT,
                coordenadas         TEXT,
                id_negocio          TEXT,
                id_conta_cliente    TEXT,
                codcli              TEXT,
                sku                 TEXT NOT NULL,
                preco               TEXT,
                quantidade_pedida   TEXT,
                nome_produto        TEXT,
                quantidade_preparar TEXT,
                telefone_1          TEXT,
                telefone_2          TEXT,
                email_1             TEXT,
                email_2             TEXT,
                coletado_em         TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (numero_pedido, sku)
            );

            CREATE TABLE IF NOT EXISTS cnpj_dados (
                cnpj                TEXT PRIMARY KEY,
                nome                TEXT,
                nome_fantasia       TEXT,
                capital_social      TEXT,
                natureza_juridica   TEXT,
                tamanho             TEXT,
                data_fundacao       TEXT,
                status              TEXT,
                data_status         TEXT,
                razao_status        TEXT,
                rua                 TEXT,
                numero              TEXT,
                complemento         TEXT,
                bairro              TEXT,
                cidade              TEXT,
                uf                  TEXT,
                cep                 TEXT,
                telefone            TEXT,
                email               TEXT,
                atividade_principal      TEXT,
                atividades_secundarias   TEXT,
                simples_optante          TEXT,
                simei_optante            TEXT,
                ie_estado                TEXT,
                ie_numero                TEXT,
                ie_status                TEXT,
                ie_tipo                  TEXT,
                ie_data_status           TEXT,
                consultado_em            TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS pedidos_enviados (
                numero_pedido TEXT PRIMARY KEY,
                enviado_em    TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS log_envio_limite (
                id_cd           TEXT NOT NULL,
                codcli          TEXT NOT NULL,
                data_envio      DATE NOT NULL DEFAULT CURRENT_DATE,
                horario_envio   TEXT,
                ultima_saudacao DATE,
                PRIMARY KEY (id_cd, codcli, data_envio)
            );
        """)
        cur.execute("""
            ALTER TABLE pedidos_itens ADD COLUMN IF NOT EXISTS codcli TEXT;
        """)


# ── pedidos_itens ─────────────────────────────────────────────────────────────

def upsert_pedidos_itens(rows: list[dict]):
    if not rows:
        return
    cols = [
        'filial', 'numero_pedido', 'data_pedido', 'centro_distribuicao',
        'status', 'forma_pagamento', 'data_entrega', 'responsavel',
        'total_pedido', 'documento', 'ie', 'nome_comercial',
        'endereco_entrega', 'cidade_uf', 'cep', 'coordenadas',
        'id_negocio', 'id_conta_cliente', 'sku', 'preco',
        'quantidade_pedida', 'nome_produto', 'quantidade_preparar',
        'telefone_1', 'telefone_2', 'email_1', 'email_2',
    ]
    placeholders = ', '.join(['%s'] * len(cols))
    col_names = ', '.join(cols)
    sql = (
        f"INSERT INTO pedidos_itens ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT (numero_pedido, sku) DO NOTHING"
    )
    with cursor() as cur:
        for row in rows:
            values = [str(row.get(c, '') or '') for c in cols]
            cur.execute(sql, values)


def deletar_pedidos_inativos(filial: str, numeros_ativos: set):
    with cursor() as cur:
        if numeros_ativos:
            cur.execute(
                "DELETE FROM pedidos_itens WHERE filial = %s AND numero_pedido != ALL(%s)",
                (filial, list(numeros_ativos))
            )
        else:
            cur.execute("DELETE FROM pedidos_itens WHERE filial = %s", (filial,))


def get_numeros_pedido_existentes(filial: str) -> set:
    with cursor() as cur:
        cur.execute(
            "SELECT DISTINCT numero_pedido FROM pedidos_itens WHERE filial = %s",
            (filial,)
        )
        return {row['numero_pedido'] for row in cur.fetchall()}


def get_todos_pedidos() -> list:
    with cursor() as cur:
        cur.execute("SELECT * FROM pedidos_itens ORDER BY numero_pedido")
        return [dict(r) for r in cur.fetchall()]


def get_pedidos_agrupados() -> list:
    rows = get_todos_pedidos()
    seen = {}
    result = []
    for row in rows:
        num = row['numero_pedido']
        if num not in seen:
            entry = {
                'Numero Pedido':          row.get('numero_pedido', ''),
                'Data Pedido':            row.get('data_pedido', ''),
                'Data Entrega':           row.get('data_entrega', ''),
                'Status':                 row.get('status', ''),
                'Centro de Distribuição': row.get('centro_distribuicao', ''),
                'Total Pedido':           row.get('total_pedido', ''),
                'Documento':              row.get('documento', ''),
                'IE':                     row.get('ie', ''),
                'Nome Comercial':         row.get('nome_comercial', ''),
                'Endereço de Entrega':    row.get('endereco_entrega', ''),
                'Cidade/UF':              row.get('cidade_uf', ''),
                'CEP':                    row.get('cep', ''),
                'Forma de Pagamento':     row.get('forma_pagamento', ''),
                'Responsavel':            row.get('responsavel', ''),
                'Telefone 1':             row.get('telefone_1', ''),
                'Telefone 2':             row.get('telefone_2', ''),
                'Email 1':                row.get('email_1', ''),
                'Email 2':                row.get('email_2', ''),
                'ID do negócio':          row.get('id_negocio', ''),
                'ID da conta do cliente': row.get('id_conta_cliente', ''),
                'Cod Cliente':            row.get('codcli', ''),
                'filial':                 row.get('filial', ''),
                'itens': [],
            }
            seen[num] = entry
            result.append(entry)
        seen[num]['itens'].append({
            'SKU':                 row.get('sku', ''),
            'Nome do Produto':     row.get('nome_produto', ''),
            'Preco':               row.get('preco', ''),
            'Quantidade Pedida':   row.get('quantidade_pedida', ''),
            'Quantidade Preparar': row.get('quantidade_preparar', ''),
        })
    return result


def atualizar_codcli(pedido_para_codcli: dict):
    if not pedido_para_codcli:
        return
    with cursor() as cur:
        for numero_pedido, codcli in pedido_para_codcli.items():
            cur.execute(
                "UPDATE pedidos_itens SET codcli = %s WHERE numero_pedido = %s",
                (str(codcli), numero_pedido)
            )


def deletar_pedido_por_numero(numero: str):
    with cursor() as cur:
        cur.execute("DELETE FROM pedidos_itens WHERE numero_pedido = %s", (numero,))


# ── cnpj_dados ────────────────────────────────────────────────────────────────

def upsert_cnpj(dados: dict):
    mapped = {_CNPJ_COL_MAP.get(k, k): v for k, v in dados.items()}
    cnpj = mapped.pop('cnpj', None)
    if not cnpj:
        return
    cols = list(mapped.keys())
    if not cols:
        return
    set_clause = ', '.join(f"{c} = EXCLUDED.{c}" for c in cols)
    placeholders = ', '.join(['%s'] * (len(cols) + 1))
    col_names = 'cnpj, ' + ', '.join(cols)
    sql = (
        f"INSERT INTO cnpj_dados ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT (cnpj) DO UPDATE SET {set_clause}"
    )
    with cursor() as cur:
        cur.execute(sql, [cnpj] + [str(mapped[c]) if mapped[c] is not None else None for c in cols])


def get_cnpjs_existentes() -> set:
    with cursor() as cur:
        cur.execute("SELECT cnpj FROM cnpj_dados")
        return {row['cnpj'] for row in cur.fetchall()}


def get_cnpjs_com_problema() -> list:
    with cursor() as cur:
        cur.execute("""
            SELECT cnpj, status, ie_status
            FROM cnpj_dados
            WHERE status != 'Ativa'
               OR ie_status NOT IN ('Sem restrição', 'Não encontrada')
        """)
        return [dict(r) for r in cur.fetchall()]


# ── pedidos_enviados ──────────────────────────────────────────────────────────

def marcar_pedido_enviado(numero: str):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO pedidos_enviados (numero_pedido) VALUES (%s) ON CONFLICT DO NOTHING",
            (numero,)
        )


def get_pedidos_enviados() -> set:
    with cursor() as cur:
        cur.execute("SELECT numero_pedido FROM pedidos_enviados")
        return {row['numero_pedido'] for row in cur.fetchall()}


def deletar_pedido_enviado(numero: str):
    with cursor() as cur:
        cur.execute("DELETE FROM pedidos_enviados WHERE numero_pedido = %s", (numero,))


# ── log_envio_limite ──────────────────────────────────────────────────────────

def ja_enviou_saudacao_hoje(id_cd: str) -> bool:
    with cursor() as cur:
        cur.execute(
            "SELECT 1 FROM log_envio_limite WHERE id_cd = %s AND ultima_saudacao = CURRENT_DATE LIMIT 1",
            (id_cd,)
        )
        return cur.fetchone() is not None


def registrar_saudacao(id_cd: str):
    import datetime
    horario = datetime.datetime.now().strftime("%H:%M:%S")
    with cursor() as cur:
        cur.execute("""
            INSERT INTO log_envio_limite (id_cd, codcli, data_envio, horario_envio, ultima_saudacao)
            VALUES (%s, '__saudacao__', CURRENT_DATE, %s, CURRENT_DATE)
            ON CONFLICT (id_cd, codcli, data_envio) DO UPDATE
            SET ultima_saudacao = CURRENT_DATE, horario_envio = EXCLUDED.horario_envio
        """, (id_cd, horario))


def ja_enviou_cliente_hoje(id_cd: str, codcli: str) -> bool:
    with cursor() as cur:
        cur.execute(
            "SELECT 1 FROM log_envio_limite WHERE id_cd = %s AND codcli = %s AND data_envio = CURRENT_DATE LIMIT 1",
            (id_cd, str(codcli))
        )
        return cur.fetchone() is not None


def registrar_cliente(id_cd: str, codcli: str):
    import datetime
    horario = datetime.datetime.now().strftime("%H:%M:%S")
    with cursor() as cur:
        cur.execute("""
            INSERT INTO log_envio_limite (id_cd, codcli, data_envio, horario_envio)
            VALUES (%s, %s, CURRENT_DATE, %s)
            ON CONFLICT (id_cd, codcli, data_envio) DO NOTHING
        """, (id_cd, str(codcli), horario))
