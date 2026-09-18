from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    document_id: str
    full_name: str
    department: str
    role: Optional[str] = "Colaborador"
    auth_method: Optional[str] = "CARNET" # 'CARNET' o 'ROSTRO'
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    document_id: str
    full_name: str
    department: str
    role: str
    auth_method: str
    avatar_url: Optional[str] = None

class ScanRequest(BaseModel):
    image_data: Optional[str] = None
    auth_mode_requested: str = "CARNET" # 'CARNET' o 'ROSTRO'
    captured_ocr_text: Optional[str] = None

class IdentifyRequest(BaseModel):
    document_id: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    auth_mode_requested: Optional[str] = "CARNET"
    captured_ocr_text: Optional[str] = None

class LoanRequest(BaseModel):
    user_id: int
    item_id: int
    destination: str

class ReturnRequest(BaseModel):
    loan_id: int
    item_id: int
    user_id: int
    physical_condition: Optional[str] = "Buen Estado / Operativo"
    notes: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    department: str
    status: str
    stock: int = 1
    current_holder_id: Optional[int] = None
    current_holder_name: Optional[str] = None
    current_destination: Optional[str] = None
    image_icon: Optional[str] = None
    description: Optional[str] = None

class LedgerEntryResponse(BaseModel):
    block_index: int
    timestamp: str
    event_type: str
    user_name: str
    user_document: str
    item_code: Optional[str]
    item_name: Optional[str]
    details: Optional[str]
    previous_hash: str
    current_hash: str
