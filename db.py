"""
Camada de banco de dados do app.

Usa o Turso (SQLite na nuvem) quando as chaves TURSO_DATABASE_URL e
TURSO_AUTH_TOKEN estiverem configuradas em st.secrets. Se não estiverem
(ex: rodando local sem configurar), cai automaticamente para um arquivo
SQLite local (carteira.db) - útil para testar sem depender da nuvem.
"""
import sqlite3
from pathlib import Path
from datetime import date

import streamlit as st

try:
    import libsql
except ImportError:
    libsql = None

DB_PATH = Path(__file__).parent / "carteira.db"


def _get_turso_config():
    try:
        url = st.secrets.get("TURSO_DATABASE_URL", "")
        token = st.secrets.get("TURSO_AUTH_TOKEN", "")
    except Exception:
        url, token = "", ""
    return url, token


def get_conn():
    url, token = _get_turso_config()
    if url and token and libsql is not None:
        return libsql.connect(database=url, auth_token=token)
    # fallback: SQLite local (modo desenvolvimento sem Turso configurado)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _to_dicts(cursor):
    """Converte o resultado de um cursor (tuplas) em lista de dicts,
    usando os nomes de coluna do cursor.description. Funciona igual para
    SQLite local e para o Turso (libsql), que não tem row_factory."""
    if cursor.description is None:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _to_dict(cursor):
    linhas = _to_dicts(cursor)
    return linhas[0] if linhas else None


def init_db():
    conn = get_conn()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        email TEXT PRIMARY KEY,
        salt TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        criado_em TEXT
    );

    CREATE TABLE IF NOT EXISTS ativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        ticker TEXT NOT NULL,
        tipo TEXT NOT NULL,
        setor TEXT,
        quantidade REAL NOT NULL,
        preco_medio REAL NOT NULL,
        preco_teto REAL,
        dividendo_anual REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS renda_fixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor_investido REAL NOT NULL,
        taxa TEXT,
        data_aplicacao TEXT
    );

    CREATE TABLE IF NOT EXISTS proventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        origem TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS patrimonio_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        data TEXT NOT NULL,
        valor_total REAL NOT NULL,
        aporte REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS metas (
        email TEXT PRIMARY KEY,
        meta_acoes_fiis REAL DEFAULT 0,
        meta_fundo REAL DEFAULT 0,
        ano_meta INTEGER DEFAULT 2026,
        custo_estimado_mensal REAL DEFAULT 0,
        reserva_meses INTEGER DEFAULT 6,
        valor_na_reserva REAL DEFAULT 0,
        meta_desejada REAL DEFAULT 100000,
        meta_master REAL DEFAULT 1000000
    );

    CREATE TABLE IF NOT EXISTS contab_categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        tipo TEXT NOT NULL,
        nome TEXT NOT NULL,
        especial INTEGER DEFAULT 0,
        ordem INTEGER DEFAULT 0,
        UNIQUE(email, tipo, nome)
    );

    CREATE TABLE IF NOT EXISTS contab_lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        tipo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        valor REAL DEFAULT 0,
        UNIQUE(email, tipo, categoria, ano, mes)
    );
    """)
    conn.commit()
    conn.close()


# ---------- USUÁRIOS (contas) ----------
def add_user(email, salt, senha_hash):
    conn = get_conn()
    try:
        existente = _to_dict(conn.execute("SELECT 1 FROM usuarios WHERE email=?", (email,)))
        if existente:
            return False
        conn.execute(
            "INSERT INTO usuarios (email, salt, senha_hash, criado_em) VALUES (?,?,?,?)",
            (email, salt, senha_hash, str(date.today())),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_user(email):
    conn = get_conn()
    try:
        return _to_dict(conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)))
    finally:
        conn.close()


# ---------- ATIVOS ----------
def add_ativo(email, ticker, tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO ativos (email, ticker, tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (email, ticker.upper(), tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual),
        )
        conn.commit()
    finally:
        conn.close()


def replace_ativos(email, lista):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM ativos WHERE email=?", (email,))
        for a in lista:
            conn.execute(
                "INSERT INTO ativos (email, ticker, tipo, setor, quantidade, preco_medio, preco_teto, dividendo_anual) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (email, a["ticker"].upper(), a["tipo"], a["setor"], a["quantidade"],
                 a["preco_medio"], a["preco_teto"], a["dividendo_anual"]),
            )
        conn.commit()
    finally:
        conn.close()


def get_ativos(email):
    conn = get_conn()
    try:
        return _to_dicts(conn.execute("SELECT * FROM ativos WHERE email=? ORDER BY tipo, ticker", (email,)))
    finally:
        conn.close()
def delete_ativo(email, id_):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM ativos WHERE id=? AND email=?", (id_, email))
        conn.commit()
    finally:
        conn.close()

# ---------- RENDA FIXA ----------
def add_renda_fixa(email, nome, categoria, valor_investido, taxa, data_aplicacao):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO renda_fixa (email, nome, categoria, valor_investido, taxa, data_aplicacao) VALUES (?,?,?,?,?,?)",
            (email, nome, categoria, valor_investido, taxa, data_aplicacao),
        )
        conn.commit()
    finally:
        conn.close()


def replace_renda_fixa(email, lista):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM renda_fixa WHERE email=?", (email,))
        for r in lista:
            conn.execute(
                "INSERT INTO renda_fixa (email, nome, categoria, valor_investido, taxa, data_aplicacao) VALUES (?,?,?,?,?,?)",
                (email, r["nome"], r["categoria"], r["valor_investido"], r["taxa"], r["data_aplicacao"]),
            )
        conn.commit()
    finally:
        conn.close()


def get_renda_fixa(email):
    conn = get_conn()
    try:
        return _to_dicts(conn.execute("SELECT * FROM renda_fixa WHERE email=? ORDER BY categoria, nome", (email,)))
    finally:
        conn.close()
def delete_renda_fixa(email, id_):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM renda_fixa WHERE id=? AND email=?", (id_, email))
        conn.commit()
    finally:
        conn.close()


# ---------- PROVENTOS ----------
def add_provento(email, origem, categoria, valor, data_):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO proventos (email, origem, categoria, valor, data) VALUES (?,?,?,?,?)",
            (email, origem, categoria, valor, data_),
        )
        conn.commit()
    finally:
        conn.close()


def delete_provento(email, id_):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM proventos WHERE id=? AND email=?", (id_, email))
        conn.commit()
    finally:
        conn.close()


def get_proventos(email):
    conn = get_conn()
    try:
        return _to_dicts(conn.execute("SELECT * FROM proventos WHERE email=? ORDER BY data DESC", (email,)))
    finally:
        conn.close()


# ---------- PATRIMÔNIO HISTÓRICO ----------
def add_patrimonio(email, data_, valor_total, aporte):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO patrimonio_historico (email, data, valor_total, aporte) VALUES (?,?,?,?)",
            (email, data_, valor_total, aporte),
        )
        conn.commit()
    finally:
        conn.close()


def delete_patrimonio(email, id_):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM patrimonio_historico WHERE id=? AND email=?", (id_, email))
        conn.commit()
    finally:
        conn.close()


def get_patrimonio_historico(email):
    conn = get_conn()
    try:
        return _to_dicts(conn.execute(
            "SELECT * FROM patrimonio_historico WHERE email=? ORDER BY data ASC", (email,)
        ))
    finally:
        conn.close()


# ---------- METAS ----------
def get_metas(email):
    conn = get_conn()
    try:
        row = _to_dict(conn.execute("SELECT * FROM metas WHERE email=?", (email,)))
        if row:
            return row
        return {
            "email": email, "meta_acoes_fiis": 0, "meta_fundo": 0, "ano_meta": 2026,
            "custo_estimado_mensal": 0, "reserva_meses": 6, "valor_na_reserva": 0,
            "meta_desejada": 100000, "meta_master": 1000000,
        }
    finally:
        conn.close()


def save_metas(email, meta_acoes_fiis, meta_fundo, ano_meta, custo_estimado_mensal,
               reserva_meses, valor_na_reserva, meta_desejada, meta_master):
    conn = get_conn()
    try:
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
    finally:
        conn.close()


# ---------- CONTABILIDADE MENSAL: CATEGORIAS ----------
def get_categorias(email, tipo):
    conn = get_conn()
    try:
        return _to_dicts(conn.execute(
            "SELECT * FROM contab_categorias WHERE email=? AND tipo=? ORDER BY ordem, id", (email, tipo)
        ))
    finally:
        conn.close()


def replace_categorias(email, tipo, lista):
    nomes_novos = [c["nome"] for c in lista]
    conn = get_conn()
    try:
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
    finally:
        conn.close()


# ---------- CONTABILIDADE MENSAL: LANÇAMENTOS ----------
def get_lancamentos_ano(email, tipo, ano):
    conn = get_conn()
    try:
        linhas = _to_dicts(conn.execute(
            "SELECT categoria, mes, valor FROM contab_lancamentos WHERE email=? AND tipo=? AND ano=?",
            (email, tipo, ano),
        ))
    finally:
        conn.close()
    resultado = {}
    for r in linhas:
        resultado.setdefault(r["categoria"], {})[r["mes"]] = r["valor"]
    return resultado


def save_lancamentos_ano(email, tipo, ano, dados):
    conn = get_conn()
    try:
        for categoria, meses in dados.items():
            for mes, valor in meses.items():
                conn.execute(
                    """INSERT INTO contab_lancamentos (email, tipo, categoria, ano, mes, valor)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(email, tipo, categoria, ano, mes) DO UPDATE SET valor=excluded.valor""",
                    (email, tipo, categoria, ano, int(mes), float(valor)),
                )
        conn.commit()
    finally:
        conn.close()


def get_anos_contab(email):
    conn = get_conn()
    try:
        linhas = _to_dicts(conn.execute(
            "SELECT DISTINCT ano FROM contab_lancamentos WHERE email=? ORDER BY ano", (email,)
        ))
    finally:
        conn.close()
    return [r["ano"] for r in linhas]

def get_todos_lancamentos(email):
    """Retorna todos os lançamentos de contabilidade mensal do usuário, de todos
    os anos e tipos, em formato tabular (útil para exportação)."""
    conn = get_conn()
    try:
        return _to_dicts(conn.execute(
            "SELECT tipo, categoria, ano, mes, valor FROM contab_lancamentos "
            "WHERE email=? ORDER BY ano, mes, tipo, categoria",
            (email,),
        ))
    finally:
        conn.close()