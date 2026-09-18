import hashlib
import json
from datetime import datetime
from database import get_connection

def calculate_hash(block_index: int, timestamp: str, event_type: str, user_document: str, item_code: str, details: str, previous_hash: str) -> str:
    """
    Calcula el hash SHA-256 criptográfico para un bloque del libro mayor de auditoría.
    Garantiza la inmutabilidad al concatenar todos los campos junto con el hash previo.
    """
    raw_payload = f"{block_index}|{timestamp}|{event_type}|{user_document}|{item_code}|{details}|{previous_hash}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

def ensure_genesis_block():
    """
    Verifica si existe el bloque Génesis. Si no, lo crea como ancla criptográfica inicial.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM ledger")
    row = cursor.fetchone()
    
    if row["count"] == 0:
        timestamp = datetime.utcnow().isoformat()
        genesis_prev = "0" * 64
        genesis_hash = calculate_hash(
            block_index=1,
            timestamp=timestamp,
            event_type="GENESIS",
            user_document="SYSTEM",
            item_code="ROOT",
            details="Bloque Génesis - Sistema de Auditoría Criptográfica Inmutable IntelliTrack",
            previous_hash=genesis_prev
        )
        cursor.execute("""
            INSERT INTO ledger (block_index, timestamp, event_type, user_name, user_document, item_code, item_name, details, previous_hash, current_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1, timestamp, "GENESIS", "SISTEMA INTELLITRACK", "SYSTEM", "ROOT", "Bloque Génesis",
            "Inicialización de la cadena de bloques local (Hash Ledger SHA-256)",
            genesis_prev, genesis_hash
        ))
        conn.commit()
    conn.close()

def append_ledger_entry(event_type: str, user_name: str, user_document: str, item_code: str, item_name: str, details: str) -> dict:
    """
    Inserta un nuevo registro inmutable en el Hash Ledger, encadenándolo con el hash anterior.
    """
    ensure_genesis_block()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Obtener el último bloque registrado
    cursor.execute("SELECT block_index, current_hash FROM ledger ORDER BY block_index DESC LIMIT 1")
    last_block = cursor.fetchone()
    
    next_index = (last_block["block_index"] + 1) if last_block else 1
    previous_hash = last_block["current_hash"] if last_block else ("0" * 64)
    timestamp = datetime.utcnow().isoformat()
    
    current_hash = calculate_hash(
        block_index=next_index,
        timestamp=timestamp,
        event_type=event_type,
        user_document=user_document,
        item_code=item_code or "",
        details=details,
        previous_hash=previous_hash
    )
    
    cursor.execute("""
        INSERT INTO ledger (block_index, timestamp, event_type, user_name, user_document, item_code, item_name, details, previous_hash, current_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        next_index, timestamp, event_type, user_name, user_document, item_code, item_name, details, previous_hash, current_hash
    ))
    conn.commit()
    
    # Retornar el bloque recién creado
    cursor.execute("SELECT * FROM ledger WHERE block_index = ?", (next_index,))
    new_entry = dict(cursor.fetchone())
    conn.close()
    return new_entry

def verify_ledger_integrity() -> dict:
    """
    Recorre todos los bloques del ledger desde el génesis y recalcula matemáticamente los hashes.
    Si algún dato en la base de datos fue manipulado de forma ilícita, la cadena se rompe de inmediato.
    """
    ensure_genesis_block()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ledger ORDER BY block_index ASC")
    blocks = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    total_blocks = len(blocks)
    if total_blocks == 0:
        return {"status": "EMPTY", "is_valid": True, "total_blocks": 0, "corrupted_block": None}
    
    previous_expected_hash = "0" * 64
    
    for i, block in enumerate(blocks):
        # 1. Validar enlace de hash anterior
        if block["previous_hash"] != previous_expected_hash:
            return {
                "status": "CORRUPTED_CHAIN",
                "is_valid": False,
                "total_blocks": total_blocks,
                "corrupted_block": block["block_index"],
                "reason": f"El previous_hash del bloque #{block['block_index']} no coincide con el hash del bloque anterior."
            }
        
        # 2. Recalcular hash del bloque actual
        recalculated = calculate_hash(
            block_index=block["block_index"],
            timestamp=block["timestamp"],
            event_type=block["event_type"],
            user_document=block["user_document"],
            item_code=block["item_code"] or "",
            details=block["details"] or "",
            previous_hash=block["previous_hash"]
        )
        
        if recalculated != block["current_hash"]:
            return {
                "status": "CORRUPTED_DATA",
                "is_valid": False,
                "total_blocks": total_blocks,
                "corrupted_block": block["block_index"],
                "reason": f"El hash del bloque #{block['block_index']} fue alterado. Esperado: {recalculated}, Guardado: {block['current_hash']}"
            }
            
        previous_expected_hash = block["current_hash"]
        
    return {
        "status": "VERIFIED_OK",
        "is_valid": True,
        "total_blocks": total_blocks,
        "latest_hash": blocks[-1]["current_hash"],
        "message": "Cadena criptográfica intacta. Todos los sellos SHA-256 coinciden matemáticamente."
    }
