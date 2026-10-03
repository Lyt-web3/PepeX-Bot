import sqlite3

from app.config import DB_PATH


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS linked_wallets (
                discord_id INTEGER PRIMARY KEY,
                wallet TEXT NOT NULL
            )
            """
        )
        conn.commit()


def set_linked_wallet(discord_id, wallet):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO linked_wallets(discord_id, wallet)
            VALUES(?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET wallet = excluded.wallet
            """,
            (discord_id, wallet),
        )
        conn.commit()


def create_linked_wallet(discord_id, wallet):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO linked_wallets(discord_id, wallet)
            VALUES(?, ?)
            """,
            (discord_id, wallet),
        )
        conn.commit()
    return cursor.rowcount == 1


def get_linked_wallet(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT wallet FROM linked_wallets WHERE discord_id = ?",
            (discord_id,),
        ).fetchone()
    return row[0] if row else None


def remove_linked_wallet(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM linked_wallets WHERE discord_id = ?",
            (discord_id,),
        )
        conn.commit()


def get_all_linked_wallets():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT discord_id, wallet FROM linked_wallets"
        ).fetchall()
