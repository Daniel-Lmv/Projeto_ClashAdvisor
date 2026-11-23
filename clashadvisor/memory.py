"""Memória persistente simples: histórico por ID de conversa em SQLite."""
import sqlite3
from .config import ROOT

DB = ROOT / 'clashadvisor.db'


def add_message(session_id: str, role: str, content: str) -> None:
    if not session_id or len(session_id) > 80 or role not in ('user', 'assistant'):
        raise ValueError('Sessão ou papel inválido')
    with sqlite3.connect(DB) as con:
        con.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session TEXT, role TEXT, content TEXT)')
        con.execute('INSERT INTO messages (session, role, content) VALUES (?, ?, ?)', (session_id, role, content[:5000]))


def recent_messages(session_id: str, limit: int = 8) -> list[dict]:
    with sqlite3.connect(DB) as con:
        con.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session TEXT, role TEXT, content TEXT)')
        rows = con.execute('SELECT role, content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?', (session_id, limit)).fetchall()
    return [{'role': role, 'content': content} for role, content in reversed(rows)]
