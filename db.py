import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent / "carteira.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        email TEXT PRIMARY KEY,
        salt TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        criado_em TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        ticker TEXT NOT NULL,
        tipo TEXT NOT NULL,              -- 'Ação' ou 'FII'
        setor TEXT,
        quantidade REAL NOT NULL,
        preco_medio REAL NOT NULL,
        preco_teto REAL,
        dividendo_anual REAL DEFAULT 0   -- Div Unit 12m
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS renda_fixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,         -- 'CDI', 'FGTS', 'Outro'
        valor_investido REAL NOT NULL,
        taxa TEXT,
        data_aplicacao TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS proventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        origem TEXT NOT NULL,
        categoria TEXT NOT NULL,         -- 'Dividendo/JCP', 'Renda Fixa', 'CDI', 'FGTS'
        valor REAL NOT NULL,
        data TEXT NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS patrimonio_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        data TEXT NOT NULL,
        valor_total REAL NOT NULL,
        aporte REAL DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contab_categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        tipo TEXT NOT NULL,        -- 'Receita' ou 'Despesa'
        nome TEXT NOT NULL,
        especial INTEGER DEFAULT 0, -- Receita: é saque/transferência (exclui do líquido) | Despesa: é investimento (exclui do líquido)
        ordem INTEGER DEFAULT 0,
        UNIQUE(email, tipo, nome)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contab_lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        tipo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        valor REAL DEFAULT 0,
        UNIQUE(email, tipo, categoria, ano, mes)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS metas (
        email TEXT PRIMARY KEY,
        meta_acoes_fiis REAL DEFAULT 0,
        meta_fundo REAL DEFAULT 0,
        ano_meta INTEGER DEFAULT 2026,
        custo_estimado_mensal REAL DEFAULT 0,
        reserva_meses INTEGER DEFAULT 6,
        valor_na_reserva REAL DEFAULT 0,
        meta_desejada REAL DEFAULT 100000,
        meta_master REAL DEFAULT 1000000
    )""")

    conn.commit()
    conn.close()


# ---------- USUÁRIOS (contas) ----------
def add_user(email, salt, senha_hash):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO usuarios (email, salt, senha_hash, criado_em) VALUES (?,?,?,?)",
            (email, salt, senha_hash, str(date.today())),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- ATIVOS ----------
def add_ativo(email, ticker, tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual):
    conn = get_conn()
    conn.execute(
        "INSERT INTO ativos (email, ticker, tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (email, ticker.upper(), tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual),
    )
    conn.commit()
    conn.close()


def replace_ativos(email, lista):
    """Apaga todos os ativos do usuário e regrava com a lista fornecida (lista de dicts)."""
    conn = get_conn()
    conn.execute("DELETE FROM ativos WHERE email=?", (email,))
    conn.commit()
    conn.close()
    for a in lista:
        add_ativo(email, a["ticker"], a["tipo"], a["setor"], a["quantidade"],
                  a["preco_medio"], a["preco_teto"], a["dividendo_anual"])


def get_ativos(email):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ativos WHERE email=? ORDER BY tipo, ticker", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- RENDA FIXA ----------
def add_renda_fixa(email, nome, categoria, valor_investido, taxa, data_aplicacao):
    conn = get_conn()
    conn.execute(
        "INSERT INTO renda_fixa (email, nome, categoria, valor_investido, taxa, data_aplicacao) VALUES (?,?,?,?,?,?)",
        (email, nome, categoria, valor_investido, taxa, data_aplicacao),
    )
    conn.commit()
    conn.close()


def replace_renda_fixa(email, lista):
    conn = get_conn()
    conn.execute("DELETE FROM renda_fixa WHERE email=?", (email,))
    conn.commit()
    conn.close()
    for r in lista:
        add_renda_fixa(email, r["nome"], r["categoria"], r["valor_investido"], r["taxa"], r["data_aplicacao"])


def get_renda_fixa(email):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM renda_fixa WHERE email=? ORDER BY categoria, nome", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- PROVENTOS ----------
def add_provento(email, origem, categoria, valor, data_):
    conn = get_conn()
    conn.execute(
        "INSERT INTO proventos (email, origem, categoria, valor, data) VALUES (?,?,?,?,?)",
        (email, origem, categoria, valor, data_),
    )
    conn.commit()
    conn.close()


def delete_provento(email, id_):
    conn = get_conn()
    conn.execute("DELETE FROM proventos WHERE id=? AND email=?", (id_, email))
    conn.commit()
    conn.close()


def get_proventos(email):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM proventos WHERE email=? ORDER BY data DESC", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- PATRIMÔNIO HISTÓRICO ----------
def add_patrimonio(email, data_, valor_total, aporte):
    conn = get_conn()
    conn.execute(
        "INSERT INTO patrimonio_historico (email, data, valor_total, aporte) VALUES (?,?,?,?)",
        (email, data_, valor_total, aporte),
    )
    conn.commit()
    conn.close()


def delete_patrimonio(email, id_):
    conn = get_conn()
    conn.execute("DELETE FROM patrimonio_historico WHERE id=? AND email=?", (id_, email))
    conn.commit()
    conn.close()


def get_patrimonio_historico(email):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM patrimonio_historico WHERE email=? ORDER BY data ASC", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- CONTABILIDADE MENSAL: CATEGORIAS ----------
def get_categorias(email, tipo):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM contab_categorias WHERE email=? AND tipo=? ORDER BY ordem, id", (email, tipo)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def replace_categorias(email, tipo, lista):
    """lista = [{'nome': str, 'especial': bool}, ...]. Substitui a lista de categorias
    do usuário para aquele tipo e remove lançamentos de categorias que deixaram de existir."""
    nomes_novos = [c["nome"] for c in lista]
    conn = get_conn()
    if nomes_novos:
        placeholders = ",".join("?" * len(nomes_novos))
        conn.execute(
            f"DELETE FROM contab_lancamentos WHERE email=? AND tipo=? AND categoria NOT IN ({placeholders})",
            (email, tipo, *nomes_novos),
        )
    else:
        conn.execute("DELETE FROM contab_lancamentos WHERE email=? AND tipo=?", (email, tipo))
    conn.execute("DELETE FROM contab_categorias WHERE email=? AND tipo=?", (email, tipo))
    for i, c in enumerate(lista):
        conn.execute(
            "INSERT INTO contab_categorias (email, tipo, nome, especial, ordem) VALUES (?,?,?,?,?)",
            (email, tipo, c["nome"], int(bool(c["especial"])), i),
        )
    conn.commit()
    conn.close()


# ---------- CONTABILIDADE MENSAL: LANÇAMENTOS ----------
def get_lancamentos_ano(email, tipo, ano):
    """Retorna dict {categoria: {mes(1-12): valor}}"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT categoria, mes, valor FROM contab_lancamentos WHERE email=? AND tipo=? AND ano=?",
        (email, tipo, ano),
    ).fetchall()
    conn.close()
    resultado = {}
    for r in rows:
        resultado.setdefault(r["categoria"], {})[r["mes"]] = r["valor"]
    return resultado


def save_lancamentos_ano(email, tipo, ano, dados):
    """dados = {categoria: {mes(1-12): valor}}"""
    conn = get_conn()
    for categoria, meses in dados.items():
        for mes, valor in meses.items():
            conn.execute(
                """INSERT INTO contab_lancamentos (email, tipo, categoria, ano, mes, valor)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(email, tipo, categoria, ano, mes) DO UPDATE SET valor=excluded.valor""",
                (email, tipo, categoria, ano, int(mes), float(valor)),
            )
    conn.commit()
    conn.close()


def get_anos_contab(email):
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT ano FROM contab_lancamentos WHERE email=? ORDER BY ano", (email,)
    ).fetchall()
    conn.close()
    return [r["ano"] for r in rows]


# ---------- METAS ----------
def get_metas(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM metas WHERE email=?", (email,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "email": email, "meta_acoes_fiis": 0, "meta_fundo": 0, "ano_meta": 2026,
        "custo_estimado_mensal": 0, "reserva_meses": 6, "valor_na_reserva": 0,
        "meta_desejada": 100000, "meta_master": 1000000,
    }


def save_metas(email, meta_acoes_fiis, meta_fundo, ano_meta, custo_estimado_mensal,
               reserva_meses, valor_na_reserva, meta_desejada, meta_master):
    conn = get_conn()
    conn.execute(
        """INSERT INTO metas (email, meta_acoes_fiis, meta_fundo, ano_meta, custo_estimado_mensal,
                               reserva_meses, valor_na_reserva, meta_desejada, meta_master)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(email) DO UPDATE SET
               meta_acoes_fiis=excluded.meta_acoes_fiis,
               meta_fundo=excluded.meta_fundo,
               ano_meta=excluded.ano_meta,
               custo_estimado_mensal=excluded.custo_estimado_mensal,
               reserva_meses=excluded.reserva_meses,
               valor_na_reserva=excluded.valor_na_reserva,
               meta_desejada=excluded.meta_desejada,
               meta_master=excluded.meta_master
        """,
        (email, meta_acoes_fiis, meta_fundo, ano_meta, custo_estimado_mensal,
         reserva_meses, valor_na_reserva, meta_desejada, meta_master),
    )
    conn.commit()
    conn.close()
