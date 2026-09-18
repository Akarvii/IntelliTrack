import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "intellitrack.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Usuarios con método exclusivo de autenticación ('CARNET' o 'ROSTRO')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Colaborador',
        auth_method TEXT NOT NULL DEFAULT 'CARNET', -- 'CARNET' o 'ROSTRO'
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Añadir columna auth_method si la tabla ya existía sin ella
    cursor.execute("PRAGMA table_info(users)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "auth_method" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_method TEXT NOT NULL DEFAULT 'CARNET'")
    
    # 2. Tabla de Inventario (Items con Stock)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Disponible', -- 'Disponible', 'No Disponible', 'Prestado'
        stock INTEGER NOT NULL DEFAULT 1,
        current_holder_id INTEGER,
        current_holder_name TEXT,
        current_destination TEXT,
        image_icon TEXT,
        description TEXT,
        FOREIGN KEY (current_holder_id) REFERENCES users(id)
    )
    """)
    
    cursor.execute("PRAGMA table_info(items)")
    item_cols = [row["name"] for row in cursor.fetchall()]
    if "stock" not in item_cols:
        cursor.execute("ALTER TABLE items ADD COLUMN stock INTEGER NOT NULL DEFAULT 1")

    
    # 3. Tabla de Transacciones / Préstamos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        destination TEXT NOT NULL,
        borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        returned_at TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'ACTIVO', -- 'ACTIVO', 'DEVUELTO'
        physical_condition_on_return TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (item_id) REFERENCES items(id)
    )
    """)
    
    # 4. Tabla del Libro Mayor Criptográfico (Hash Ledger SHA-256)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
        block_index INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL, -- 'GENESIS', 'PRESTAMO', 'DEVOLUCION', 'MODO_LIBRE'
        user_name TEXT NOT NULL,
        user_document TEXT NOT NULL,
        item_code TEXT,
        item_name TEXT,
        details TEXT,
        previous_hash TEXT NOT NULL,
        current_hash TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with auth_method support.")
