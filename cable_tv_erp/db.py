import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def get_db_connection():
    """Opens and returns a new MySQL connection. Caller must close it."""
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False
    )
    return conn


def query_db(sql, args=(), one=False, commit=False):
    """
    Executes sql with args.
    - If commit=True: executes and commits (INSERT/UPDATE/DELETE).
      Returns lastrowid for INSERT, rowcount for UPDATE/DELETE.
    - If commit=False: executes and returns all rows as dicts (or one row if one=True).
    Always closes the connection.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, args)
        if commit:
            conn.commit()
            last_id = cursor.lastrowid
            row_count = cursor.rowcount
            cursor.close()
            conn.close()
            return last_id if last_id else row_count
        else:
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            if one:
                return rows[0] if rows else None
            return rows
    except Exception:
        conn.rollback()
        cursor.close()
        conn.close()
        raise
