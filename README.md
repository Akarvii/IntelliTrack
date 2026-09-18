# 🚀 IntelliTrack (Intelligent Tracker)

> **Plataforma Autónoma de Gestión de Inventario, Autenticación en el Borde (Edge AI / Visión Artificial) y Auditoría Inmutable con Ledger SHA-256.**

---

## 📌 Descripción

**IntelliTrack** es una solución de quiosco inteligente diseñada para automatizar la solicitud, préstamo y devolución de equipos, herramientas e instrumental en laboratorios, almacenes o talleres industriales.

### ✨ Características Principales
* **Autenticación Biométrica y de Credenciales (Edge AI):**
  * Reconocimiento y segmentación de carnets/credenciales con OpenCV (ORB, CLAHE, homografía RANSAC, análisis multi-zona e histogramas cromáticos HSV).
  * Reconocimiento facial biométrico con correlación de gradientes.
  * Extracción de texto y validación OCR (Document ID).
* **Gestión de Inventario en Tiempo Real:** Control dinámico de stock disponible y préstamos activos.
* **Hash Ledger SHA-256:** Registro inmutable tipo Blockchain de cada transacción (préstamo, devolución, reinicio de sistema) con verificación de integridad matemática en un solo clic.
* **Interfaz de Quiosco Táctil Moderna:** Desarrollada con HTML5, Vanilla CSS3 y JavaScript ES6+, lista para pantallas táctiles y cámaras web.

---

## 🛠️ Requisitos Previos

* **Python 3.10 o superior**
* Cámara web funcional (para pruebas de visión por computadora)

---

## ⚡ Instalación y Puesta en Marcha

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/IntelliTrack.git
   cd IntelliTrack
   ```

2. **Crear y activar un entorno virtual (opcional pero recomendado):**
   ```bash
   # En Windows
   python -m venv venv
   .\venv\Scripts\activate

   # En Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar el servidor:**
   ```bash
   python -m uvicorn main:app --reload
   ```

5. **Acceder a la aplicación:**
   * **Aplicación Web:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Documentación Interactiva Swagger / OpenAPI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📂 Estructura del Proyecto

```text
├── database.py         # Configuración y esquemas SQLite
├── models.py           # Modelos de datos Pydantic
├── ledger.py           # Motor criptográfico y validación SHA-256
├── vision.py           # Motor de procesamiento de imágenes y OpenCV
├── main.py             # Servidor y API REST FastAPI
├── seed_data.py        # Inicializador de datos y stock
├── clean_db.py         # Script de restablecimiento rápido
├── requirements.txt    # Dependencias del proyecto
├── .gitignore          # Filtros de exclusión de Git
├── RESUMEN_PROYECTO_INTELLITRACK.md  # Memoria técnica detallada
└── static/
    ├── index.html      # UI del quiosco
    ├── css/
    │   └── styles.css  # Estilos e interfaz Dark Navy
    └── js/
        └── app.js      # Lógica del cliente, webcam y OCR
```

---

## 📖 Documentación Técnica Completa

Para conocer a detalle los algoritmos de visión por computadora, fórmulas matemáticas y arquitectura del sistema, consulta [RESUMEN_PROYECTO_INTELLITRACK.md](RESUMEN_PROYECTO_INTELLITRACK.md).
