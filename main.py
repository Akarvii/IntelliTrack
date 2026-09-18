import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List

from database import get_connection, init_db
from ledger import append_ledger_entry, verify_ledger_integrity, ensure_genesis_block
from models import (
    UserCreate, UserResponse, IdentifyRequest, ScanRequest,
    LoanRequest, ReturnRequest, ItemResponse, LedgerEntryResponse
)
from seed_data import seed_database
from vision import match_candidate_user

app = FastAPI(
    title="IntelliTrack API",
    description="Backend de automatización logística con Visión Artificial y Ledger SHA-256",
    version="1.4.0"
)

@app.on_event("startup")
def startup_event():
    seed_database()

# ================= RUTAS DE USUARIOS =================

@app.get("/api/users", response_model=List[UserResponse])
def get_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return users

@app.post("/api/users", response_model=UserResponse)
def create_or_update_user(user: UserCreate):
    conn = get_connection()
    cursor = conn.cursor()
    
    doc_id = user.document_id.strip()
    full_name = user.full_name.strip()
    dept = user.department.strip()
    auth_meth = (user.auth_method or "CARNET").upper()
    if auth_meth not in ["CARNET", "ROSTRO"]:
        auth_meth = "CARNET"
        
    cursor.execute("SELECT * FROM users WHERE document_id = ?", (doc_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE users 
            SET full_name = ?, department = ?, role = ?, auth_method = ?, avatar_url = COALESCE(?, avatar_url)
            WHERE document_id = ?
        """, (full_name, dept, user.role or "Colaborador", auth_meth, user.avatar_url, doc_id))
        user_id = existing["id"]
    else:
        cursor.execute("""
            INSERT INTO users (document_id, full_name, department, role, auth_method, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_id, full_name, dept, user.role or "Colaborador", auth_meth, user.avatar_url))
        user_id = cursor.lastrowid
        
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    saved_user = dict(cursor.fetchone())
    conn.close()
    return saved_user

# ================= COTEJO Y ANÁLISIS EN VIVO DE CÁMARA =================

@app.post("/api/scan/identify")
def scan_and_identify(req: ScanRequest):
    """
    Recibe la captura en vivo de la cámara, busca entre TODOS los usuarios registrados
    con ese método (CARNET o ROSTRO) y realiza el reconocimiento de vértices/texto.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    all_users = [dict(r) for r in cursor.fetchall()]
    
    match_result = match_candidate_user(
        live_image_b64=req.image_data,
        requested_mode=req.auth_mode_requested,
        users=all_users,
        ocr_text=req.captured_ocr_text
    )
    
    if not match_result["matched"] or not match_result["user"]:
        conn.close()
        return {
            "matched": False,
            "user": None,
            "confidence": 0.0,
            "message": match_result["message"],
            "has_active_loan": False,
            "active_loan": None
        }
        
    user_dict = match_result["user"]
    
    cursor.execute("""
        SELECT l.*, i.name as item_name, i.code as item_code, i.image_icon
        FROM loans l
        JOIN items i ON l.item_id = i.id
        WHERE l.user_id = ? AND l.status = 'ACTIVO'
        ORDER BY l.id DESC LIMIT 1
    """, (user_dict["id"],))
    active_loan = cursor.fetchone()
    conn.close()
    
    return {
        "matched": True,
        "user": user_dict,
        "confidence": match_result["confidence"],
        "message": match_result["message"],
        "has_active_loan": active_loan is not None,
        "active_loan": dict(active_loan) if active_loan else None
    }

# ================= INVENTARIO =================

@app.get("/api/items", response_model=List[ItemResponse])
def get_items(department: Optional[str] = None, status: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    if department and department != "TODOS":
        query += " AND department = ?"
        params.append(department)
        
    if status and status != "TODOS":
        query += " AND status = ?"
        params.append(status)
        
    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return items

# ================= PRÉSTAMOS & DEVOLUCIONES CON CONTROL DE STOCK =================

@app.post("/api/loans")
def register_loan(req: LoanRequest):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (req.user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no existe")
        
    cursor.execute("SELECT * FROM items WHERE id = ?", (req.item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Elemento no existe")
        
    current_stock = item["stock"] if "stock" in item.keys() else 1
    if current_stock <= 0 or item["status"] not in ["Disponible"]:
        conn.close()
        raise HTTPException(status_code=400, detail=f"El elemento '{item['name']}' no tiene stock disponible (Stock: {current_stock})")
        
    cursor.execute("""
        INSERT INTO loans (user_id, item_id, destination, status)
        VALUES (?, ?, ?, 'ACTIVO')
    """, (req.user_id, req.item_id, req.destination))
    loan_id = cursor.lastrowid
    
    new_stock = current_stock - 1
    new_status = "Disponible" if new_stock > 0 else "No Disponible"
    
    cursor.execute("""
        UPDATE items 
        SET stock = ?,
            status = ?,
            current_holder_id = ?,
            current_holder_name = ?,
            current_destination = ?
        WHERE id = ?
    """, (new_stock, new_status, user["id"], user["full_name"], req.destination, req.item_id))
    
    conn.commit()
    conn.close()
    
    details_str = f"Préstamo para '{req.destination}'. Validado con [{user['auth_method']}]. Quedan {new_stock} en stock."
    ledger_entry = append_ledger_entry(
        event_type="PRESTAMO",
        user_name=user["full_name"],
        user_document=user["document_id"],
        item_code=item["code"],
        item_name=item["name"],
        details=details_str
    )
    
    return {
        "status": "SUCCESS",
        "message": f"Préstamo de '{item['name']}' registrado con éxito (Stock restante: {new_stock}).",
        "loan_id": loan_id,
        "ledger_block": ledger_entry
    }

@app.get("/api/loans/active")
def get_active_loans():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, i.name as item_name, i.code as item_code, i.category as item_category, 
               i.image_icon, u.full_name as user_name, u.document_id as user_document, u.department as user_department
        FROM loans l
        JOIN items i ON l.item_id = i.id
        JOIN users u ON l.user_id = u.id
        WHERE l.status = 'ACTIVO'
        ORDER BY l.borrowed_at DESC
    """)
    loans = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return loans

@app.get("/api/loans/user/{user_id}")
def get_user_active_loans(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, i.name as item_name, i.code as item_code, i.category as item_category, 
               i.image_icon, i.department as item_department, u.full_name as user_name, u.document_id as user_document
        FROM loans l
        JOIN items i ON l.item_id = i.id
        JOIN users u ON l.user_id = u.id
        WHERE l.user_id = ? AND l.status = 'ACTIVO'
        ORDER BY l.borrowed_at DESC
    """, (user_id,))
    loans = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return loans

@app.post("/api/returns")
def register_return(req: ReturnRequest):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM loans WHERE id = ? AND status = 'ACTIVO'", (req.loan_id,))
    loan = cursor.fetchone()
    if not loan:
        conn.close()
        raise HTTPException(status_code=404, detail="No se encontró un préstamo activo para cerrar")
        
    cursor.execute("SELECT * FROM users WHERE id = ?", (req.user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM items WHERE id = ?", (req.item_id,))
    item = cursor.fetchone()
    
    condition_str = req.physical_condition or "Buen Estado / Operativo"
    
    cursor.execute("""
        UPDATE loans 
        SET status = 'DEVUELTO', 
            returned_at = CURRENT_TIMESTAMP,
            physical_condition_on_return = ?
        WHERE id = ?
    """, (condition_str, req.loan_id))
    
    current_stock = item["stock"] if item and "stock" in item.keys() else 0
    new_stock = current_stock + 1
    
    cursor.execute("""
        UPDATE items 
        SET stock = stock + 1,
            status = 'Disponible',
            current_holder_id = NULL,
            current_holder_name = NULL,
            current_destination = NULL
        WHERE id = ?
    """, (req.item_id,))
    
    conn.commit()
    conn.close()
    
    notes_str = f" | Observaciones: {req.notes.strip()}" if req.notes and req.notes.strip() else ""
    details_str = f"Devolución recibida. Condición: [{condition_str}]{notes_str}. Stock reingresado (+1, total: {new_stock}). Préstamo #{req.loan_id} liquidado."
    
    ledger_entry = append_ledger_entry(
        event_type="DEVOLUCION",
        user_name=user["full_name"] if user else "Colaborador",
        user_document=user["document_id"] if user else "N/A",
        item_code=item["code"] if item else "ITEM",
        item_name=item["name"] if item else "Elemento",
        details=details_str
    )
    
    return {
        "status": "SUCCESS",
        "message": f"Devolución de '{item['name'] if item else 'Elemento'}' completada exitosamente (Stock disponible: {new_stock}).",
        "ledger_block": ledger_entry
    }

# ================= LIBRO MAYOR =================

@app.get("/api/ledger", response_model=List[LedgerEntryResponse])
def get_ledger_history():
    ensure_genesis_block()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ledger ORDER BY block_index DESC")
    entries = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return entries

@app.get("/api/ledger/verify")
def run_ledger_verification():
    return verify_ledger_integrity()

@app.post("/api/system/reset")
def reset_system():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS loans")
    cursor.execute("DROP TABLE IF EXISTS ledger")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()
    
    seed_database()
    return {"status": "SUCCESS", "message": "Sistema reiniciado a estado inicial."}

# ================= ESTÁTICOS =================

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "IntelliTrack Backend Activo"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
