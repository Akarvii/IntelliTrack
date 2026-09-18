/**
 * IntelliTrack - Aplicación Modular con Reconocimiento de Alta Fidelidad (ORB Vértices + Edge OCR)
 */

let currentUser = null;
let currentActiveLoan = null;
let currentUserLoans = [];
let allItems = [];
let allUsers = [];
let webcamStream = null;
let currentAuthMode = "CARNET"; // 'CARNET' o 'ROSTRO'

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
    initWebcam();
});

async function initApp() {
    await loadAllUsers();
    setAuthMode("CARNET");
}

function setupEventListeners() {
    // 1. Switch de Modo de Autenticación (Carnet vs Rostro) en Pantalla Principal
    document.getElementById("btn-mode-carnet").addEventListener("click", () => setAuthMode("CARNET"));
    document.getElementById("btn-mode-rostro").addEventListener("click", () => setAuthMode("ROSTRO"));

    // 2. Modal de Registro de Usuario & Captura en Vivo
    document.getElementById("btn-open-register-modal").addEventListener("click", openRegisterModal);
    document.getElementById("btn-close-register-modal").addEventListener("click", closeRegisterModal);
    document.getElementById("form-register").addEventListener("submit", handleRegisterSubmit);

    // Controles de cámara dentro del modal
    document.getElementById("btn-modal-capture").addEventListener("click", captureModalSnapshot);
    document.getElementById("btn-modal-retake").addEventListener("click", retakeModalLiveVideo);

    // Selección de radio buttons en el modal de registro
    const radioCarnet = document.getElementById("card-opt-carnet");
    const radioRostro = document.getElementById("card-opt-rostro");
    
    radioCarnet.addEventListener("click", () => {
        radioCarnet.classList.add("selected");
        radioRostro.classList.remove("selected");
        radioCarnet.querySelector("input").checked = true;
        updateModalReticle("CARNET");
    });

    radioRostro.addEventListener("click", () => {
        radioRostro.classList.add("selected");
        radioCarnet.classList.remove("selected");
        radioRostro.querySelector("input").checked = true;
        updateModalReticle("ROSTRO");
    });

    // 3. Botón de Checar y Confirmar Cámara (Análisis de Visión Artificial)
    document.getElementById("btn-scan-and-verify").addEventListener("click", handleCameraScanAndIdentify);

    // 4. Salir al Menú
    document.getElementById("btn-logout").addEventListener("click", showAuthView);

    // 5. Tabs Dashboard
    document.querySelectorAll(".btn-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            switchDashboardTab(btn.dataset.tab);
        });
    });

    // 6. Filtro de Inventario
    document.getElementById("filter-dept").addEventListener("change", (e) => {
        renderInventoryGrid(e.target.value);
    });

    // 7. Modal de Préstamo
    document.getElementById("btn-close-loan-modal").addEventListener("click", () => closeModal("modal-loan"));
    document.getElementById("form-loan").addEventListener("submit", handleLoanSubmit);

    // 8. Pestaña y Modal de Devolución
    const btnRefreshLoans = document.getElementById("btn-refresh-loans");
    if (btnRefreshLoans) {
        btnRefreshLoans.addEventListener("click", () => loadUserActiveLoans(true));
    }
    const btnCloseReturn = document.getElementById("btn-close-return-modal");
    if (btnCloseReturn) {
        btnCloseReturn.addEventListener("click", () => closeModal("modal-return"));
    }
    const formReturn = document.getElementById("form-return");
    if (formReturn) {
        formReturn.addEventListener("submit", handleReturnModalSubmit);
    }

    // 9. Auditoría Criptográfica
    document.getElementById("btn-verify-ledger").addEventListener("click", verifyLedgerIntegrity);

    // 10. Reinicio
    const btnReset = document.getElementById("btn-system-reset");
    if (btnReset) {
        btnReset.addEventListener("click", resetSystem);
    }
}

// ================= GESTIÓN DE WEBCAM =================

async function initWebcam() {
    try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            webcamStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }
            });
            attachStreamToMainVideo();
        }
    } catch (err) {
        console.warn("Cámara no disponible o permiso denegado.", err);
    }
}

function attachStreamToMainVideo() {
    const mainVideo = document.getElementById("webcam-video");
    if (webcamStream && mainVideo) {
        mainVideo.srcObject = webcamStream;
        mainVideo.play().catch(e => console.log("Play:", e));
    }
}

function attachStreamToModalVideo() {
    const modalVideo = document.getElementById("modal-webcam-video");
    if (webcamStream && modalVideo) {
        modalVideo.srcObject = webcamStream;
        modalVideo.play().catch(e => console.log("Play modal:", e));
    }
}

function getLiveFrameBase64() {
    const video = document.getElementById("webcam-video");
    if (!video || video.videoWidth === 0 || video.paused) {
        return null;
    }
    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.9);
}

// ================= CAMBIO DE MODO EN PANTALLA PRINCIPAL =================

function setAuthMode(mode) {
    currentAuthMode = mode;
    const btnCarnet = document.getElementById("btn-mode-carnet");
    const btnRostro = document.getElementById("btn-mode-rostro");
    const reticle = document.getElementById("camera-scan-reticle");
    const statusPill = document.getElementById("scan-status-text");
    const iconHeading = document.getElementById("scan-btn-icon");
    const cardHeading = document.getElementById("scan-card-heading");
    const cardDesc = document.getElementById("scan-card-desc");

    document.getElementById("verified-user-summary").style.display = "none";

    if (mode === "CARNET") {
        btnCarnet.classList.add("active");
        btnRostro.classList.remove("active");
        reticle.className = "scan-reticle mode-carnet";
        statusPill.innerText = "Apunta tu carnet o credencial física dentro de la guía óptica";
        statusPill.style.color = "var(--text-main)";
        iconHeading.innerText = "💳";
        cardHeading.innerText = "Verificar Carnet en Cámara (OCR & Vértices)";
        cardDesc.innerText = "Coteja los datos internos, texto impreso y puntos clave del carnet en vivo.";
    } else {
        btnRostro.classList.add("active");
        btnCarnet.classList.remove("active");
        reticle.className = "scan-reticle mode-rostro";
        statusPill.innerText = "Centra tu rostro dentro del óvalo biométrico";
        statusPill.style.color = "#38BDF8";
        iconHeading.innerText = "👤";
        cardHeading.innerText = "Verificar Rostro Único en Cámara (Biometría)";
        cardDesc.innerText = "Coteja los vértices y puntos biométricos faciales de alta fidelidad.";
    }
}

// ================= ANÁLISIS DINÁMICO DE CÁMARA (ALTA FIDELIDAD) =================

async function handleCameraScanAndIdentify() {
    const statusPill = document.getElementById("scan-status-text");
    const container = document.getElementById("verified-user-summary");
    container.style.display = "none";
    
    const liveFrame = getLiveFrameBase64();
    if (!liveFrame) {
        statusPill.innerText = "⚠️ Enciende o permite el acceso a la cámara para escanear.";
        statusPill.style.color = "var(--accent-crimson)";
        return;
    }

    let ocrExtractedText = null;

    if (currentAuthMode === "CARNET") {
        statusPill.innerText = "🔍 Extrayendo texto y delimitaciones internas del carnet (Edge OCR & ORB)...";
        statusPill.style.color = "#38BDF8";

        // Si Tesseract.js está disponible en el navegador, intentar OCR con timeout no bloqueante
        if (window.Tesseract) {
            try {
                const ocrPromise = Tesseract.recognize(liveFrame, 'eng', {
                    logger: m => {}
                });
                const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error("OCR timeout")), 1800));
                const workerResult = await Promise.race([ocrPromise, timeoutPromise]);
                ocrExtractedText = workerResult && workerResult.data ? workerResult.data.text : null;
                if (ocrExtractedText) {
                    console.log("OCR Detectado en carnet:", ocrExtractedText.trim());
                }
            } catch (err) {
                console.log("Cotejo directo por visión espectral y geométrica ORB.");
            }
        }
    } else {
        statusPill.innerText = "👤 Extrayendo vértices y patrones biométricos faciales (Face Mesh)...";
        statusPill.style.color = "#38BDF8";
    }

    try {
        const res = await fetch("/api/scan/identify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                image_data: liveFrame,
                auth_mode_requested: currentAuthMode,
                captured_ocr_text: ocrExtractedText
            })
        });

        const data = await res.json();
        container.style.display = "block";

        if (data.matched && data.user) {
            currentUser = data.user;
            currentActiveLoan = data.active_loan;

            statusPill.innerText = `✅ ${data.message}`;
            statusPill.style.color = "var(--accent-lime)";

            const methodBadgeClass = currentUser.auth_method === "CARNET" ? "badge-method-pill CARNET" : "badge-method-pill ROSTRO";
            const isCarnet = currentUser.auth_method === "CARNET";

            const thumbnailHtml = currentUser.avatar_url 
                ? `<img src="${currentUser.avatar_url}" class="user-thumbnail-preview ${isCarnet ? 'carnet-aspect' : ''}" alt="Foto registrada">`
                : `<div class="user-avatar-circle" style="width: 44px; height: 44px; font-size: 1.1rem;">${currentUser.full_name.charAt(0).toUpperCase()}</div>`;

            container.innerHTML = `
                <div class="verified-preview-box">
                    ${thumbnailHtml}
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <strong style="color: #FFFFFF; font-size: 0.95rem;">${currentUser.full_name}</strong>
                            <span class="${methodBadgeClass}">${currentUser.auth_method}</span>
                        </div>
                        <p style="font-size: 0.75rem; color: var(--accent-lime); margin-top: 2px;">
                            Carnet: ${currentUser.document_id} • ${currentUser.department}
                        </p>
                        <span style="font-size: 0.7rem; color: #38BDF8; font-family: monospace;">Fidelidad de Puntos: ${data.confidence}%</span>
                    </div>
                </div>
                <button id="btn-enter-dashboard" class="btn-success" style="margin-top: 10px;">
                    🚀 Continuar a Préstamos e Inventario
                </button>
            `;
            document.getElementById("btn-enter-dashboard").addEventListener("click", showDashboardView);
        } else {
            statusPill.innerText = `⚠️ No se validó coincidencia`;
            statusPill.style.color = "var(--accent-crimson)";

            container.innerHTML = `
                <div class="verified-preview-box error-mismatch">
                    <div style="font-size: 1.6rem;">⚠️</div>
                    <div style="flex: 1;">
                        <strong style="color: #F87171; font-size: 0.9rem;">RECHAZO DE IDENTIFICACIÓN</strong>
                        <p style="font-size: 0.78rem; color: #FCA5A5; margin-top: 2px;">
                            ${data.message}
                        </p>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        statusPill.innerText = "❌ Error en análisis";
        statusPill.style.color = "var(--accent-crimson)";
    }
}

// ================= MODAL DE REGISTRO CON CÁMARA EN VIVO =================

function openRegisterModal() {
    const avatarInput = document.getElementById("input-avatar-url");
    avatarInput.value = "";

    document.getElementById("input-user-doc").value = "";
    document.getElementById("input-user-name").value = "";
    document.getElementById("input-user-dept").value = "Ingeniería / Mantenimiento";

    const radioCarnet = document.getElementById("card-opt-carnet");
    const radioRostro = document.getElementById("card-opt-rostro");

    if (currentAuthMode === "ROSTRO") {
        radioRostro.classList.add("selected");
        radioCarnet.classList.remove("selected");
        radioRostro.querySelector("input").checked = true;
        updateModalReticle("ROSTRO");
    } else {
        radioCarnet.classList.add("selected");
        radioRostro.classList.remove("selected");
        radioCarnet.querySelector("input").checked = true;
        updateModalReticle("CARNET");
    }

    retakeModalLiveVideo();
    attachStreamToModalVideo();
    openModal("modal-register");
}

function closeRegisterModal() {
    closeModal("modal-register");
    attachStreamToMainVideo();
}

function updateModalReticle(mode) {
    const modalReticle = document.getElementById("modal-scan-reticle");
    if (mode === "CARNET") {
        modalReticle.className = "scan-reticle mode-carnet";
    } else {
        modalReticle.className = "scan-reticle mode-rostro";
    }
}

function captureModalSnapshot() {
    const modalVideo = document.getElementById("modal-webcam-video");
    const mainVideo = document.getElementById("webcam-video");
    const modalOverlay = document.getElementById("modal-scan-overlay");
    const snapshotImg = document.getElementById("modal-snapshot-img");
    const btnCapture = document.getElementById("btn-modal-capture");
    const btnRetake = document.getElementById("btn-modal-retake");
    const statusText = document.getElementById("modal-cam-status");
    const avatarInput = document.getElementById("input-avatar-url");
    const selectedMode = document.querySelector('input[name="auth_method"]:checked').value;

    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");

    const activeVideo = (modalVideo && modalVideo.videoWidth > 0 && !modalVideo.paused) ? modalVideo : mainVideo;

    if (activeVideo && activeVideo.videoWidth > 0) {
        ctx.drawImage(activeVideo, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.95);
        snapshotImg.src = dataUrl;
        avatarInput.value = dataUrl;
    } else {
        statusText.innerText = "⚠️ Enciende la cámara antes de capturar";
        statusText.style.color = "var(--accent-crimson)";
        return;
    }

    modalVideo.style.display = "none";
    modalOverlay.style.display = "none";
    snapshotImg.style.display = "block";
    btnCapture.style.display = "none";
    btnRetake.style.display = "inline-flex";
    statusText.innerText = `✅ Foto de ${selectedMode} capturada con éxito`;
    statusText.style.color = "var(--accent-lime)";
}

function retakeModalLiveVideo() {
    const modalVideo = document.getElementById("modal-webcam-video");
    const modalOverlay = document.getElementById("modal-scan-overlay");
    const snapshotImg = document.getElementById("modal-snapshot-img");
    const btnCapture = document.getElementById("btn-modal-capture");
    const btnRetake = document.getElementById("btn-modal-retake");
    const statusText = document.getElementById("modal-cam-status");

    modalVideo.style.display = "block";
    modalOverlay.style.display = "flex";
    snapshotImg.style.display = "none";
    btnCapture.style.display = "inline-flex";
    btnRetake.style.display = "none";
    statusText.innerText = "● Cámara en vivo activa";
    statusText.style.color = "var(--accent-lime)";

    attachStreamToModalVideo();
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const doc = document.getElementById("input-user-doc").value.trim();
    const name = document.getElementById("input-user-name").value.trim();
    const dept = document.getElementById("input-user-dept").value.trim();
    const authMethod = document.querySelector('input[name="auth_method"]:checked').value;
    const avatarUrl = document.getElementById("input-avatar-url").value;

    if (!doc || !name) return;

    try {
        const res = await fetch("/api/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                document_id: doc,
                full_name: name,
                department: dept,
                role: "Colaborador",
                auth_method: authMethod,
                avatar_url: avatarUrl || null
            })
        });
        const savedUser = await res.json();
        currentUser = savedUser;
        closeRegisterModal();
        showNotification(`Nuevo usuario ${savedUser.full_name} registrado con éxito.`);
        
        await loadAllUsers();
        setAuthMode(savedUser.auth_method);
    } catch (err) {
        alert("Error al registrar datos.");
    }
}

// ================= NAVEGACIÓN MODULAR =================

function showAuthView() {
    document.getElementById("view-auth").style.display = "flex";
    document.getElementById("view-dashboard").style.display = "none";
    document.getElementById("verified-user-summary").style.display = "none";
    setAuthMode(currentAuthMode);
    attachStreamToMainVideo();
}

function showDashboardView() {
    if (!currentUser) return;
    
    document.getElementById("view-auth").style.display = "none";
    document.getElementById("view-dashboard").style.display = "flex";

    // Actualizar barra de usuario
    document.getElementById("dash-user-name").innerText = currentUser.full_name;
    document.getElementById("dash-user-meta").innerText = `Carnet: ${currentUser.document_id} • ${currentUser.department}`;
    
    const avatarContainer = document.getElementById("dash-user-avatar");
    if (currentUser.avatar_url) {
        avatarContainer.innerHTML = `<img src="${currentUser.avatar_url}" alt="Foto de usuario">`;
    } else {
        avatarContainer.innerHTML = `<span>${currentUser.full_name.charAt(0).toUpperCase()}</span>`;
    }

    const badge = document.getElementById("dash-user-method-badge");
    badge.className = `badge-method-pill ${currentUser.auth_method}`;
    badge.innerText = `MÉTODO: ${currentUser.auth_method}`;

    // Resetear a pestaña inicial (Catálogo)
    switchDashboardTab("catalogo");

    // Cargar inventario, préstamos y badge
    loadInventory();
    renderActiveLoanBanner();
    loadUserActiveLoans(false);
}

// ================= GESTIÓN DE USUARIOS =================

async function loadAllUsers() {
    try {
        const res = await fetch("/api/users");
        allUsers = await res.json();
    } catch (err) {
        console.error("Error cargando usuarios:", err);
    }
}

// ================= INVENTARIO & PRÉSTAMOS =================

async function loadInventory() {
    try {
        const res = await fetch("/api/items");
        allItems = await res.json();
        renderInventoryGrid(document.getElementById("filter-dept").value);
    } catch (err) {
        console.error("Error cargando inventario:", err);
    }
}

function renderInventoryGrid(deptFilter = "TODOS") {
    const grid = document.getElementById("inventory-grid");
    grid.innerHTML = "";

    const filtered = allItems.filter(item => {
        if (deptFilter === "TODOS") return true;
        return item.department === deptFilter;
    });

    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No hay elementos para esta categoría.</div>`;
        return;
    }

    filtered.forEach(item => {
        const card = document.createElement("div");
        const stockQty = (typeof item.stock === 'number') ? item.stock : 1;
        const isAvailable = (item.status === "Disponible" && stockQty > 0);
        const isBorrowed = item.status === "Prestado";
        const isUnavailable = !isAvailable && !isBorrowed;

        card.className = `item-card ${isBorrowed ? 'borrowed' : (isUnavailable ? 'unavailable' : '')}`;
        
        let statusBadge = `<span class="badge-item-status disponible">Disponible</span>`;
        if (isBorrowed) {
            statusBadge = `<span class="badge-item-status prestado">En Préstamo</span>`;
        } else if (isUnavailable || stockQty <= 0) {
            statusBadge = `<span class="badge-item-status nodisponible">Agotado</span>`;
        }

        const stockBadge = isAvailable
            ? `<div class="badge-stock-pill in-stock">📦 Stock: ${stockQty} un.</div>`
            : `<div class="badge-stock-pill out-stock">⚠️ Stock: ${stockQty} un.</div>`;

        card.innerHTML = `
            <div>
                <div class="item-card-top">
                    <div class="item-icon">${item.image_icon || '📦'}</div>
                    ${statusBadge}
                </div>
                <h4 class="item-title">${item.name}</h4>
                <div class="item-code">ID: ${item.code} • ${item.category}</div>
                ${stockBadge}
                <p class="item-desc">${item.description || ''}</p>
                ${isBorrowed ? `
                    <div class="item-holder-info">
                        🔒 Custodio: <strong>${item.current_holder_name}</strong><br>
                        📍 Destino: ${item.current_destination || 'N/A'}
                    </div>
                ` : ''}
            </div>
            <div>
                ${isAvailable ? `
                    <button class="btn-primary" onclick="openLoanModal(${item.id})">
                        ⚡ Retirar / Préstamo
                    </button>
                ` : (isBorrowed ? `
                    <button class="btn-secondary" style="width: 100%; opacity: 0.6; cursor: not-allowed;" disabled>
                        En Custodia
                    </button>
                ` : `
                    <button class="btn-secondary" style="width: 100%; opacity: 0.5; cursor: not-allowed;" disabled>
                        Sin Stock / No Disponible
                    </button>
                `)}
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderActiveLoanBanner() {
    const bannerContainer = document.getElementById("direct-return-container");
    
    if (currentActiveLoan) {
        bannerContainer.innerHTML = `
            <div class="direct-return-banner">
                <div style="display: flex; gap: 14px; align-items: center;">
                    <span style="font-size: 2.2rem;">${currentActiveLoan.image_icon || '⚠️'}</span>
                    <div>
                        <span style="background: var(--accent-amber); color: #FFF; font-weight: 700; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px;">PRÉSTAMO ACTIVO DETECTADO</span>
                        <h3 style="margin-top: 4px; font-size: 1.15rem;">${currentActiveLoan.item_name}</h3>
                        <p style="font-size: 0.8rem; color: #FCD34D;">Destino: ${currentActiveLoan.destination} • Fecha: ${new Date(currentActiveLoan.borrowed_at).toLocaleTimeString()}</p>
                    </div>
                </div>
                <div>
                    <button class="btn-success" onclick="handleDirectReturn(${currentActiveLoan.id}, ${currentActiveLoan.item_id})">
                        📦 Confirmar Devolución Directa
                    </button>
                </div>
            </div>
        `;
    } else {
        bannerContainer.innerHTML = "";
    }
}

function openLoanModal(itemId) {
    const item = allItems.find(i => i.id === itemId);
    if (!item) return;

    document.getElementById("loan-item-id").value = item.id;
    document.getElementById("loan-item-name-display").innerText = `${item.image_icon || '📦'} ${item.name} (${item.code})`;
    document.getElementById("loan-user-name-display").innerText = currentUser.full_name;

    openModal("modal-loan");
}

async function handleLoanSubmit(e) {
    e.preventDefault();
    const itemId = parseInt(document.getElementById("loan-item-id").value);
    const destination = document.getElementById("loan-destination-select").value;

    try {
        const res = await fetch("/api/loans", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser.id,
                item_id: itemId,
                destination: destination
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al procesar préstamo");
        }

        const data = await res.json();
        closeModal("modal-loan");
        
        showNotification(`✅ Préstamo sellado en SHA-256: ${data.ledger_block.current_hash.substring(0, 14)}...`);
        
        // Refrescar
        const scanRes = await fetch("/api/scan/identify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ auth_mode_requested: currentUser.auth_method })
        });
        const refreshed = await scanRes.json();
        currentActiveLoan = refreshed.active_loan;

        await loadInventory();
        renderActiveLoanBanner();
        await loadUserActiveLoans(false);
    } catch (err) {
        alert(err.message);
    }
}

async function handleDirectReturn(loanId, itemId) {
    if (!confirm("¿Deseas confirmar la entrega física del insumo?")) return;

    try {
        const res = await fetch("/api/returns", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                loan_id: loanId,
                item_id: itemId,
                user_id: currentUser.id,
                physical_condition: "Operativo / Buen Estado"
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al registrar devolución");
        }

        const data = await res.json();
        showNotification(`✅ Devolución completada. Bloque SHA-256 registrado.`);
        
        // Refrescar
        const scanRes = await fetch("/api/scan/identify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ auth_mode_requested: currentUser.auth_method })
        });
        const refreshed = await scanRes.json();
        currentActiveLoan = refreshed.active_loan;

        await loadInventory();
        renderActiveLoanBanner();
        await loadUserActiveLoans(true);
    } catch (err) {
        alert(err.message);
    }
}

// ================= GESTIÓN DE PESTAÑA & MODAL DE DEVOLUCIONES =================

function switchDashboardTab(tabName) {
    document.querySelectorAll(".btn-tab").forEach(b => {
        b.classList.toggle("active", b.dataset.tab === tabName);
    });

    const catSec = document.getElementById("dash-section-catalogo");
    const devSec = document.getElementById("dash-section-devoluciones");
    const ledSec = document.getElementById("dash-section-ledger");

    if (catSec) catSec.style.display = (tabName === "catalogo") ? "block" : "none";
    if (devSec) devSec.style.display = (tabName === "devoluciones") ? "block" : "none";
    if (ledSec) ledSec.style.display = (tabName === "ledger") ? "block" : "none";

    if (tabName === "catalogo") {
        renderInventoryGrid(document.getElementById("filter-dept").value);
    } else if (tabName === "devoluciones") {
        loadUserActiveLoans(true);
    } else if (tabName === "ledger") {
        loadLedgerHistory();
    }
}

async function loadUserActiveLoans(renderUI = true) {
    if (!currentUser) return;

    try {
        const res = await fetch(`/api/loans/user/${currentUser.id}`);
        if (!res.ok) throw new Error("Error al obtener préstamos activos del usuario");
        
        currentUserLoans = await res.json();

        // Actualizar badge en la pestaña
        const countBadge = document.getElementById("user-active-loans-count");
        if (countBadge) {
            if (currentUserLoans.length > 0) {
                countBadge.innerText = currentUserLoans.length;
                countBadge.style.display = "inline-flex";
            } else {
                countBadge.style.display = "none";
            }
        }

        if (renderUI) {
            renderUserActiveLoansGrid();
        }
    } catch (err) {
        console.error("Error cargando préstamos del usuario:", err);
    }
}

function renderUserActiveLoansGrid() {
    const listContainer = document.getElementById("user-active-loans-list");
    if (!listContainer) return;

    listContainer.innerHTML = "";

    if (!currentUserLoans || currentUserLoans.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-loans-state">
                <div class="icon">✨</div>
                <h3>¡No tienes préstamos pendientes!</h3>
                <p>Todos tus insumos solicitados han sido devueltos a almacén o no posees ningún registro activo en este momento.</p>
                <button class="btn-primary" style="width: auto; margin-top: 10px;" onclick="switchDashboardTab('catalogo')">
                    📦 Explorar Catálogo de Insumos
                </button>
            </div>
        `;
        return;
    }

    currentUserLoans.forEach(loan => {
        const card = document.createElement("div");
        card.className = "active-loan-card";
        const borrowedDate = new Date(loan.borrowed_at);
        const dateFormatted = borrowedDate.toLocaleDateString() + ' ' + borrowedDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        card.innerHTML = `
            <div>
                <div class="active-loan-header">
                    <div class="active-loan-icon">${loan.image_icon || '📦'}</div>
                    <div class="active-loan-details">
                        <span style="font-size: 0.72rem; font-weight: 700; color: var(--accent-amber); text-transform: uppercase;">Préstamo Activo #${loan.id}</span>
                        <h4>${loan.item_name}</h4>
                        <p>Código: <strong style="color: var(--text-main); font-family: monospace;">${loan.item_code}</strong> • ${loan.item_category || 'Insumo'}</p>
                    </div>
                </div>

                <div class="active-loan-meta" style="margin-top: 14px;">
                    <div><span>📍 Destino:</span> <strong>${loan.destination}</strong></div>
                    <div><span>🕒 Fecha retiro:</span> <strong>${dateFormatted}</strong></div>
                    <div><span>👤 Custodio:</span> <strong>${loan.user_name}</strong></div>
                </div>
            </div>

            <div style="display: flex; gap: 8px; margin-top: 14px;">
                <button class="btn-secondary" style="flex: 1;" onclick="handleDirectReturn(${loan.id}, ${loan.item_id})">
                    ⚡ Rápida
                </button>
                <button class="btn-success" style="flex: 2;" onclick="openReturnModalById(${loan.id})">
                    📦 Registrar Devolución
                </button>
            </div>
        `;
        listContainer.appendChild(card);
    });
}

function openReturnModalById(loanId) {
    const loan = currentUserLoans.find(l => l.id === loanId);
    if (!loan) return;

    document.getElementById("return-loan-id").value = loan.id;
    document.getElementById("return-item-id").value = loan.item_id;
    document.getElementById("return-item-icon-display").innerText = loan.image_icon || '📦';
    document.getElementById("return-item-name-display").innerText = loan.item_name;
    document.getElementById("return-item-meta-display").innerText = `Código: ${loan.item_code} | Área: ${loan.item_department || currentUser.department}`;
    document.getElementById("return-user-name-display").innerText = loan.user_name || currentUser.full_name;
    document.getElementById("return-destination-display").innerText = loan.destination;
    document.getElementById("return-condition-select").value = "Operativo / Excelente Estado";
    document.getElementById("return-notes-input").value = "";

    openModal("modal-return");
}

async function handleReturnModalSubmit(e) {
    e.preventDefault();
    const loanId = parseInt(document.getElementById("return-loan-id").value);
    const itemId = parseInt(document.getElementById("return-item-id").value);
    const physicalCondition = document.getElementById("return-condition-select").value;
    const notes = document.getElementById("return-notes-input").value;

    try {
        const res = await fetch("/api/returns", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                loan_id: loanId,
                item_id: itemId,
                user_id: currentUser.id,
                physical_condition: physicalCondition,
                notes: notes
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Error al registrar la devolución");
        }

        const data = await res.json();
        closeModal("modal-return");

        showNotification(`✅ Devolución sellada en SHA-256: ${data.ledger_block.current_hash.substring(0, 14)}...`);

        // Refrescar estado global
        const scanRes = await fetch("/api/scan/identify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ auth_mode_requested: currentUser.auth_method })
        });
        const refreshed = await scanRes.json();
        currentActiveLoan = refreshed.active_loan;

        await loadInventory();
        renderActiveLoanBanner();
        await loadUserActiveLoans(true);
    } catch (err) {
        alert(err.message);
    }
}

// ================= LIBRO MAYOR (HASH LEDGER) & AUDITORÍA =================

async function loadLedgerHistory() {
    try {
        const res = await fetch("/api/ledger");
        const entries = await res.json();
        renderLedgerTable(entries);
    } catch (err) {
        console.error("Error al cargar ledger:", err);
    }
}

function renderLedgerTable(entries) {
    const tbody = document.getElementById("ledger-tbody");
    tbody.innerHTML = "";

    entries.forEach(block => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>#${block.block_index}</strong></td>
            <td><span class="badge-event ${block.event_type}">${block.event_type}</span></td>
            <td>${block.user_name} <br><small style="color:var(--text-muted);">${block.user_document}</small></td>
            <td><strong>${block.item_name || 'N/A'}</strong> <br><small style="color:var(--text-muted);">${block.item_code || ''}</small></td>
            <td style="max-width: 200px; font-size: 0.8rem;">${block.details || ''}</td>
            <td><div class="hash-cell">${block.previous_hash.substring(0, 14)}...</div></td>
            <td><div class="hash-cell" style="color: var(--accent-lime);">${block.current_hash.substring(0, 14)}...</div></td>
            <td style="font-size: 0.75rem; color: var(--text-muted);">${new Date(block.timestamp).toLocaleTimeString()}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function verifyLedgerIntegrity() {
    const banner = document.getElementById("integrity-result-card");
    banner.style.display = "flex";
    banner.className = "integrity-card";
    banner.innerHTML = "<span>🔄 Recalculando firmas SHA-256 encadenadas...</span>";

    try {
        const res = await fetch("/api/ledger/verify");
        const result = await res.json();

        if (result.is_valid) {
            banner.innerHTML = `
                <div>
                    <h4 style="color: var(--accent-lime);">🛡️ CADENA CRIPTOGRÁFICA INMUTABLE & VÁLIDA</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
                        ${result.message} (Bloques auditados: <strong>${result.total_blocks}</strong>)
                    </p>
                </div>
                <div class="hash-cell" style="color: var(--accent-lime); font-size: 0.8rem;">
                    Último Hash: ${result.latest_hash.substring(0, 20)}...
                </div>
            `;
        } else {
            banner.className = "integrity-card corrupted";
            banner.innerHTML = `
                <div>
                    <h4 style="color: var(--accent-crimson);">⚠️ ALERTA: CADENA MANIPULADA</h4>
                    <p style="font-size: 0.85rem; color: #FCA5A5;">${result.reason}</p>
                </div>
            `;
        }
    } catch (err) {
        banner.className = "integrity-card corrupted";
        banner.innerHTML = `<span>Error verificando la cadena.</span>`;
    }
}

async function resetSystem() {
    if (!confirm("¿Deseas reiniciar inventario y transacciones para una nueva prueba limpia?")) return;
    try {
        await fetch("/api/system/reset", { method: "POST" });
        showNotification("Sistema reiniciado con éxito.");
        showAuthView();
        await initApp();
    } catch (err) {
        alert("Error al reiniciar sistema");
    }
}

// ================= MODALES & NOTIFICACIONES =================

function openModal(id) {
    document.getElementById(id).classList.add("open");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("open");
}

function showNotification(msg) {
    const notif = document.createElement("div");
    notif.style.position = "fixed";
    notif.style.bottom = "24px";
    notif.style.right = "24px";
    notif.style.background = "#1E293B";
    notif.style.color = "#FFFFFF";
    notif.style.border = "1px solid var(--accent-crimson)";
    notif.style.borderRadius = "10px";
    notif.style.padding = "14px 20px";
    notif.style.boxShadow = "0 10px 25px rgba(0,0,0,0.5)";
    notif.style.zIndex = "999";
    notif.style.fontSize = "0.9rem";
    notif.style.fontWeight = "600";
    notif.style.display = "flex";
    notif.style.alignItems = "center";
    notif.style.gap = "10px";
    notif.innerHTML = `<span>🔔</span> <span>${msg}</span>`;

    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 4000);
}
