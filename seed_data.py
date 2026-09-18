from database import get_connection, init_db
from ledger import ensure_genesis_block

def seed_database():
    init_db()
    ensure_genesis_block()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Poblar catálogo de inventario si está vacío
    cursor.execute("SELECT COUNT(*) as count FROM items")
    if cursor.fetchone()["count"] == 0:
        sample_items = [
            ("HERR-001", "Multímetro Digital True-RMS Fluke 117", "Instrumentación", "Ingeniería / Mantenimiento", "Disponible", 6, "⚡", "Multímetro profesional para mediciones eléctricas y electrónicas de precisión."),
            ("HERR-002", "Osciloscopio Digital Portátil Hantek 2D72", "Laboratorio", "Ingeniería / Mantenimiento", "Disponible", 3, "🔬", "Osciloscopio de 2 canales con generador de formas de onda."),
            ("HERR-003", "Kit de Herramientas de Precisión iFixit Pro", "Herramientas", "Ingeniería / Mantenimiento", "Disponible", 12, "🔧", "Set completo de 64 puntas para apertura y reparación de equipos."),
            ("COMP-101", "Laptop de Desarrollo ThinkPad T14 Gen 3", "Cómputo", "Sistemas / TI", "Disponible", 5, "💻", "Equipo de cómputo para pruebas de software y diagnóstico."),
            ("COMP-102", "Kit Arduino & Raspberry Pi 4 (8GB)", "Prototipado", "Sistemas / TI", "Disponible", 8, "🤖", "Módulo de desarrollo embebido con sensores IoT."),
            ("LOG-201", "Lector Láser de Código de Barras Honeywell", "Logística", "Logística / Almacén", "Disponible", 4, "📦", "Terminal de escaneo inalámbrico industrial."),
            ("HERR-004", "Cautín Estación de Soldadura Hakko FX-888D", "Soldadura", "Ingeniería / Mantenimiento", "No Disponible", 0, "🔥", "Estación de soldadura digital con control térmico (Stock temporalmente agotado)."),
            ("SEG-301", "Kit EPP Casco Dieléctrico + Gafas UV", "Seguridad", "Operaciones", "No Disponible", 0, "🦺", "Equipo de protección personal normado (En reposición de almacén)."),
        ]
        
        cursor.executemany("""
            INSERT INTO items (code, name, category, department, status, stock, image_icon, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_items)
        print("Catálogo de inventario inicial con control de stock cargado.")

    
    # NOTA: Sin usuarios pre-cargados. La base de datos de usuarios inicia 100% limpia desde 0.
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_database()
