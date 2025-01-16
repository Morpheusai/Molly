import logging
import sqlite3

conn = sqlite3.connect('example.db', check_same_thread=False)
cursor = conn.cursor()


# 连接到SQLite数据库（如果不存在则会自动创建）
def init_tables():
    """
    检查指定的表是否存在。
    """
    cursor = conn.cursor()
    table_name = 'code_agent'
    cursor.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name=?""", (table_name,))
    if cursor.fetchone() is None:
        cursor.execute("""
            CREATE TABLE code_agent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                state TEXT NOT NULL,
                queue_position INTEGER NOT NULL
            )
        """)
        conn.commit()
    cursor.close()

def insert_code_agent(task_id, state, queue_position):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO code_agent (task_id, state, queue_position)
        VALUES (?, ?, ?)
    """, (task_id, state, queue_position))
    conn.commit()
    cursor.close()

def update_code_agent(task_id, state, queue_position):
    cursor = conn.cursor()
    logging.info(f"Updating code agent with task ID: {task_id} {state} {queue_position}")
    cursor.execute("""
        UPDATE code_agent
        SET state = ?, queue_position = ?
        WHERE task_id = ?
    """, (state, queue_position, task_id))
    conn.commit()
    cursor.close()

def delete_code_agent(task_id):
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM code_agent
        WHERE task_id = ?
    """, (task_id,))
    conn.commit()
    cursor.close()

def qeury_code_agent(task_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM code_agent
        WHERE task_id = ?
    """, (task_id,))
    result = cursor.fetchone()
    cursor.close()
    return result