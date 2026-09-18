import base64
import cv2
import numpy as np

# Detector ORB optimizado para micro-detalles en credenciales físicas
orb_detector = cv2.ORB_create(
    nfeatures=3500,
    scaleFactor=1.12,
    nlevels=8,
    edgeThreshold=10,
    scoreType=cv2.ORB_HARRIS_SCORE
)
flann_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

def decode_base64_to_cv2(data_url: str) -> np.ndarray:
    """Decodifica un string base64 / data URL directamente a una matriz BGR de OpenCV."""
    if "," in data_url:
        _, data_str = data_url.split(",", 1)
    else:
        data_str = data_url
    image_bytes = base64.b64decode(data_str)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img_bgr

def normalize_illumination(gray_img: np.ndarray) -> np.ndarray:
    """
    Normaliza variaciones de luz extrema, brillos o sombras sobre el carnet
    usando ecualización adaptativa CLAHE y estiramiento de contraste.
    """
    # 1. Normalización Min-Max para corregir sub/sobreexposición
    norm = cv2.normalize(gray_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    # 2. CLAHE para balancear reflejos y sombras locales
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(norm)
    return enhanced

def isolate_card_region(img_bgr: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Detecta automáticamente el objeto 'Carnet / Tarjeta' en primer plano,
    aislándolo de dedos, personas de fondo y objetos alrededor.
    Retorna (imagen_recortada_del_carnet, fue_aislado_automaticamente).
    """
    h, w, _ = img_bgr.shape
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detección de contornos y bordes del carnet
    edges = cv2.Canny(blurred, 35, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    min_area = (w * h) * 0.08  # Mínimo 8% de la pantalla
    max_area = (w * h) * 0.92  # Máximo 92% de la pantalla
    
    best_crop = None
    best_score = -1.0
    
    center_x, center_y = w / 2.0, h / 2.0
    
    for c in contours:
        area = cv2.contourArea(c)
        if min_area < area < max_area:
            x, y, cw, ch = cv2.boundingRect(c)
            ratio = max(cw, ch) / (min(cw, ch) + 1e-5)
            # El carnet estándar ID-1 tiene proporción entre 1.25 y 1.90
            if 1.20 <= ratio <= 1.95:
                box_cx = x + cw / 2.0
                box_cy = y + ch / 2.0
                dist_to_center = np.hypot(box_cx - center_x, box_cy - center_y)
                # Priorizar contornos centrados y de buen tamaño
                score = area - (dist_to_center * 40.0)
                if score > best_score:
                    best_score = score
                    # Añadir un pequeño margen de seguridad (padding de 2%)
                    pad_x = int(cw * 0.02)
                    pad_y = int(ch * 0.02)
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(w, x + cw + pad_x)
                    y2 = min(h, y + ch + pad_y)
                    best_crop = img_bgr[y1:y2, x1:x2]
                    
    if best_crop is not None and best_crop.shape[0] > 60 and best_crop.shape[1] > 60:
        return best_crop, True
    else:
        # Si no se detectó un contorno cerrado perfecto, recortar el cuadrante guía central
        y1, y2 = int(h * 0.12), int(h * 0.88)
        x1, x2 = int(w * 0.14), int(w * 0.86)
        return img_bgr[y1:y2, x1:x2], False

def check_card_internal_structure(card_bgr: np.ndarray) -> dict:
    """
    Analiza la anatomía interna del carnet:
    1. Presencia de renglones tipográficos y texto.
    2. Presencia de zona de foto o escudo/logo.
    3. Firma cromática del diseño institucional.
    """
    gray = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2GRAY)
    enhanced = normalize_illumination(gray)
    
    # 1. Mapa de texto con gradientes horizontales
    grad_x = cv2.Sobel(enhanced, cv2.CV_32F, 1, 0, ksize=3)
    grad_x = np.absolute(grad_x)
    max_val = grad_x.max()
    if max_val > 0:
        grad_x = np.uint8((grad_x / max_val) * 255)
    else:
        grad_x = np.zeros_like(gray)
        
    kernel_text = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    closed_text = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, kernel_text)
    _, text_thresh = cv2.threshold(closed_text, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    contours, _ = cv2.findContours(text_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    text_blocks = 0
    for c in contours:
        _, _, cw, ch = cv2.boundingRect(c)
        if cw > 15 and 4 < ch < 60:
            text_blocks += 1
            
    # 2. Histograma de color de la credencial
    hsv = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    
    return {
        "text_blocks": text_blocks,
        "enhanced_gray": enhanced,
        "color_hist": hist
    }

def analyze_internal_card_zones(live_warped: np.ndarray, cand_gray: np.ndarray) -> dict:
    """
    Segmenta y compara las zonas internas críticas del carnet:
    1. Zona de Fotografía del Titular (cuadrante izquierdo o derecho según diseño).
    2. Zona de Datos Personales (nombres, código de estudiante/documento, carrera).
    3. Zona de Cabecera / Membrete Institucional.
    """
    target_h, target_w = cand_gray.shape
    
    # Normalizar ambas imágenes
    w_norm = normalize_illumination(live_warped)
    c_norm = normalize_illumination(cand_gray)
    
    # 1. Zona de Foto Izquierda [y: 20%-85%, x: 4%-42%]
    ph_live_l = cv2.resize(w_norm[int(target_h*0.20):int(target_h*0.85), int(target_w*0.04):int(target_w*0.42)], (100, 120))
    ph_cand_l = cv2.resize(c_norm[int(target_h*0.20):int(target_h*0.85), int(target_w*0.04):int(target_w*0.42)], (100, 120))
    photo_corr_l = cv2.matchTemplate(ph_live_l, ph_cand_l, cv2.TM_CCOEFF_NORMED)[0][0]
    photo_corr_l = max(0.0, float(photo_corr_l))
    
    # Zona de Foto Derecha [y: 20%-85%, x: 58%-96%]
    ph_live_r = cv2.resize(w_norm[int(target_h*0.20):int(target_h*0.85), int(target_w*0.58):int(target_w*0.96)], (100, 120))
    ph_cand_r = cv2.resize(c_norm[int(target_h*0.20):int(target_h*0.85), int(target_w*0.58):int(target_w*0.96)], (100, 120))
    photo_corr_r = cv2.matchTemplate(ph_live_r, ph_cand_r, cv2.TM_CCOEFF_NORMED)[0][0]
    photo_corr_r = max(0.0, float(photo_corr_r))
    
    # Tomar la zona de foto más relevante
    photo_score = max(photo_corr_l, photo_corr_r)
    
    # 2. Zona de Texto de Datos [y: 22%-85%, x: 38%-96%]
    txt_live = cv2.resize(w_norm[int(target_h*0.22):int(target_h*0.85), int(target_w*0.38):int(target_w*0.96)], (180, 110))
    txt_cand = cv2.resize(c_norm[int(target_h*0.22):int(target_h*0.85), int(target_w*0.38):int(target_w*0.96)], (180, 110))
    
    txt_corr = cv2.matchTemplate(txt_live, txt_cand, cv2.TM_CCOEFF_NORMED)[0][0]
    txt_corr = max(0.0, float(txt_corr))
    
    # Coincidencia de bordes tipográficos (Canny edge IOU sobre texto de datos)
    e_live = cv2.Canny(txt_live, 40, 130)
    e_cand = cv2.Canny(txt_cand, 40, 130)
    e_inter = np.sum(cv2.bitwise_and(e_live, e_cand))
    e_union = np.sum(cv2.bitwise_or(e_live, e_cand)) + 1e-5
    edge_iou = float(e_inter / e_union)
    
    return {
        "photo_score": photo_score,
        "text_corr": txt_corr,
        "text_edge_iou": edge_iou
    }

def match_card_deep_analysis(live_bgr: np.ndarray, cand_bgr: np.ndarray, cand_user: dict, ocr_text: str = None) -> tuple[bool, float, str]:
    """
    Inspección Fina y Diferenciación de Carnets (Mismo tipo vs Diferente tipo, Mismos datos vs Diferentes datos):
    1. Aislamiento del carnet y normalización de luz/brillos.
    2. Firma cromática y cabecera institucional.
    3. Homografía Planar RANSAC sobre micro-detalles.
    4. Análisis de Zona de Foto del Titular (diferencia usuarios con el mismo carnet institucional).
    5. Análisis de Zona de Texto y Nombres impresos.
    6. Cotejo exacto de Document ID / Nombre por OCR.
    """
    # 1. AISLAR EL OBJETO CARNET DEL ENTORNO
    live_card, _ = isolate_card_region(live_bgr)
    cand_card, _ = isolate_card_region(cand_bgr)

    # 2. EXTRACCIÓN DE ESTRUCTURA Y NORMALIZACIÓN DE LUZ
    live_struct = check_card_internal_structure(live_card)
    cand_struct = check_card_internal_structure(cand_card)

    live_enhanced = live_struct["enhanced_gray"]
    cand_enhanced = cand_struct["enhanced_gray"]

    # 3. FIRMA CROMÁTICA (Diferencia tipos de carnet institucional)
    color_corr = cv2.compareHist(live_struct["color_hist"], cand_struct["color_hist"], cv2.HISTCMP_CORREL)
    color_corr = max(0.0, float(color_corr))

    # 4. PUNTOS CLAVE Y DESCRIPTORES ORB
    live_kps, live_descs = orb_detector.detectAndCompute(live_enhanced, None)
    cand_kps, cand_descs = orb_detector.detectAndCompute(cand_enhanced, None)

    if live_descs is None or cand_descs is None or len(live_kps) < 25 or len(cand_kps) < 25:
        return False, 10.0, "Acerca más el carnet al visor o ajusta la iluminación."

    # 5. EMPAREJAMIENTO DE MICRO-VÉRTICES (LOWE RATIO TEST)
    raw_matches = flann_matcher.knnMatch(live_descs, cand_descs, k=2)
    good_matches = []
    for m_pair in raw_matches:
        if len(m_pair) == 2:
            m, n = m_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

    if len(good_matches) < 16:
        return False, 15.0, f"El contenido interno del carnet no coincide con la credencial registrada ({len(good_matches)} puntos < 16 requeridos)."

    # 6. HOMOGRAFÍA PLANAR RANSAC (Verifica que los puntos pertenezcan al mismo plano de tarjeta)
    src_pts = np.float32([live_kps[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([cand_kps[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    try:
        H, inliers_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)
    except Exception:
        return False, 15.0, "Inconsistencia en la perspectiva del carnet."

    if inliers_mask is None or H is None:
        return False, 15.0, "Los puntos no corresponden a la geometría del carnet."

    inliers_count = int(np.sum(inliers_mask))
    inlier_ratio = inliers_count / float(len(good_matches))

    # 7. PROYECCIÓN DE PERSPECTIVA Y ANÁLISIS DE ZONAS INTERNAS (FOTO + DATOS)
    target_h, target_w = cand_enhanced.shape
    try:
        warped_live = cv2.warpPerspective(live_enhanced, H, (target_w, target_h))
        global_ncc = cv2.matchTemplate(warped_live, cand_enhanced, cv2.TM_CCOEFF_NORMED)[0][0]
        global_ncc = max(0.0, float(global_ncc))
        
        zones = analyze_internal_card_zones(warped_live, cand_enhanced)
        photo_score = zones["photo_score"]
        text_corr = zones["text_corr"]
        edge_iou = zones["text_edge_iou"]
    except Exception:
        global_ncc = 0.0
        photo_score = 0.0
        text_corr = 0.0
        edge_iou = 0.0

    # 8. COTEJO OCR DEL DOCUMENTO Y NOMBRE (DIFERENCIADOR CRÍTICO DE MISMO TIPO DE CARNET)
    ocr_matched = False
    ocr_mismatch = False
    doc_id_clean = str(cand_user.get("document_id", "")).upper().replace(" ", "").replace("-", "")
    name_parts = str(cand_user.get("full_name", "")).upper().split()

    if ocr_text:
        ocr_clean = ocr_text.upper().replace(" ", "").replace("-", "")
        
        if doc_id_clean and len(doc_id_clean) >= 3:
            if doc_id_clean in ocr_clean:
                ocr_matched = True
            else:
                # Si en el OCR aparecen números largos distintos al document_id registrado
                import re
                detected_numbers = re.findall(r'\d{4,}', ocr_clean)
                if detected_numbers and doc_id_clean not in detected_numbers:
                    ocr_mismatch = True

        name_matches = sum(1 for part in name_parts if len(part) >= 4 and part in ocr_clean)
        if name_matches >= 2:
            ocr_matched = True

    # Criterio compuesto para diferenciar:
    # 1. Si son del mismo tipo de carnet pero diferente usuario (Carnet XX vs Carnet XY),
    #    la zona de foto y texto tipográfico/IOU diferirán, o el OCR del Document ID detectará el ID ajeno.
    is_match = False
    if ocr_matched:
        is_match = True
    elif ocr_mismatch:
        is_match = False
    else:
        # Validación de visión multi-zona
        is_match = (
            inliers_count >= 20 and
            inlier_ratio >= 0.38 and
            global_ncc >= 0.38 and
            (photo_score >= 0.45 or text_corr >= 0.45 or edge_iou >= 0.40) and
            color_corr >= 0.35
        )

    # Cálculo ponderado de confianza
    confidence = (
        (inliers_count * 1.2) +
        (inlier_ratio * 15.0) +
        (global_ncc * 20.0) +
        (photo_score * 20.0) +
        (text_corr * 15.0) +
        (color_corr * 10.0)
    )
    if ocr_matched:
        confidence = min(99.9, confidence + 30.0)
    if ocr_mismatch:
        confidence = max(5.0, confidence - 50.0)

    confidence = max(0.0, min(99.8, confidence))

    if is_match:
        return True, confidence, f"Carnet validado ({cand_user['full_name']} • ID: {cand_user['document_id']})."
    else:
        return False, confidence, f"El carnet presentado no coincide con los datos ni foto de {cand_user['full_name']} (Inliers: {inliers_count}/20, Similitud: {round(confidence, 1)}%)."


def match_face_biometric_structure(live_bgr: np.ndarray, cand_bgr: np.ndarray) -> tuple[bool, float, str]:
    """
    Verificación Biométrica de Rostro:
    Compara correlación facial y gradientes Sobel estructurales.
    """
    live_gray = cv2.cvtColor(live_bgr, cv2.COLOR_BGR2GRAY)
    cand_gray = cv2.cvtColor(cand_bgr, cv2.COLOR_BGR2GRAY)

    live_norm_l = normalize_illumination(live_gray)
    cand_norm_l = normalize_illumination(cand_gray)

    h1, w1 = live_gray.shape
    h2, w2 = cand_gray.shape

    live_face = live_norm_l[int(h1 * 0.15):int(h1 * 0.85), int(w1 * 0.2):int(w1 * 0.8)]
    cand_face = cand_norm_l[int(h2 * 0.15):int(h2 * 0.85), int(w2 * 0.2):int(w2 * 0.8)]

    if live_face.size == 0 or cand_face.size == 0:
        return False, 0.0, "Rostro no encuadrado en la retícula."

    live_norm = cv2.resize(live_face, (120, 120))
    cand_norm = cv2.resize(cand_face, (120, 120))

    corr_val = cv2.matchTemplate(live_norm, cand_norm, cv2.TM_CCOEFF_NORMED)[0][0]
    corr_val = max(0.0, float(corr_val))

    sobel_live = cv2.Sobel(live_norm, cv2.CV_64F, 1, 1, ksize=3)
    sobel_cand = cv2.Sobel(cand_norm, cv2.CV_64F, 1, 1, ksize=3)

    grad_diff = np.mean(np.abs(sobel_live - sobel_cand))
    grad_score = max(0.0, 100.0 - (grad_diff / 4.0))

    score = (corr_val * 65.0) + (grad_score * 0.35)
    score = max(0.0, min(99.0, score))

    if corr_val >= 0.55 and score >= 58.0:
        return True, score, f"Rostro verificado correctamente (Correlación: {round(corr_val * 100, 1)}%)."
    else:
        return False, score, f"Los rasgos faciales no coinciden con el usuario registrado (Correlación: {round(corr_val * 100, 1)}% < 55%)."

def match_candidate_user(live_image_b64: str, requested_mode: str, users: list, ocr_text: str = None) -> dict:
    """
    Función de entrada para análisis de alta fidelidad.
    """
    requested_mode = requested_mode.upper()
    candidates = [u for u in users if (u.get("auth_method") or "CARNET").upper() == requested_mode]

    if not candidates:
        return {
            "matched": False,
            "user": None,
            "confidence": 0.0,
            "message": f"No hay usuarios registrados con el método de {requested_mode}. Por favor registra uno primero."
        }

    if not live_image_b64:
        return {
            "matched": False,
            "user": None,
            "confidence": 0.0,
            "message": "No se recibió imagen de la cámara web."
        }

    try:
        live_bgr = decode_base64_to_cv2(live_image_b64)
    except Exception as e:
        return {
            "matched": False,
            "user": None,
            "confidence": 0.0,
            "message": f"Error procesando imagen: {str(e)}"
        }

    best_user = None
    best_score = 0.0
    best_msg = ""

    for candidate in candidates:
        avatar_b64 = candidate.get("avatar_url")
        if not avatar_b64 or len(avatar_b64) < 100:
            continue

        try:
            cand_bgr = decode_base64_to_cv2(avatar_b64)
            if requested_mode == "CARNET":
                is_match, score, msg = match_card_deep_analysis(live_bgr, cand_bgr, candidate, ocr_text)
            else:
                is_match, score, msg = match_face_biometric_structure(live_bgr, cand_bgr)
        except Exception as err:
            is_match = False
            score = 0.0
            msg = str(err)

        if is_match and score > best_score:
            best_score = score
            best_user = candidate
            best_msg = msg
        elif not is_match and score > best_score:
            best_msg = msg

    if best_user is not None:
        return {
            "matched": True,
            "user": best_user,
            "confidence": round(best_score, 1),
            "message": f"Identidad confirmada: {best_user['full_name']} ({best_msg})"
        }
    else:
        return {
            "matched": False,
            "user": None,
            "confidence": round(best_score, 1),
            "message": best_msg if best_msg else f"El {requested_mode.lower()} presentado no coincide con las credenciales registradas."
        }




