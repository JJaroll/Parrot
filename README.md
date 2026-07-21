# 🦜 Parrot (Python + FastAPI)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

*🌍 **Español** | [English](README_en.md) | [日本語](README_ja.md)*

**Parrot** es una potente API y Dashboard local para la separación de audio y post-producción. Diseñada para aislar pistas (stems) de una canción o archivo de audio, transcribirlas utilizando Inteligencia Artificial (Whisper) y volver a mezclarlas (Merge) con ajustes profesionales como Ecualización, Noise Gate y Paneo.

Ideal para productores musicales, músicos, creadores de contenido y desarrolladores que necesitan manipular audio programáticamente.

## ✨ Características Principales

* **🌍 Soporte Multi-Idioma:**
    *   Documentación disponible en Español, Inglés y Japonés.
* **🎛️ Separación de Audio Avanzada:**
    *   Extrae stems individuales: Voces, Batería, Bajo, Piano, Guitarra y Otros.
* **🗣️ Transcripción Inteligente (Whisper):**
    *   Transcribe las voces aisladas generando archivos `.srt` y `.txt` automáticamente, ideal para subtítulos.
* **🎧 Mezclador y Post-Producción (Merge):**
    *   Vuelve a unir los stems con control total: Volumen, Paneo, Noise Gate, Ganancia de Bajos, Medios, Altos y Normalización final.
* **✂️ Edición Rápida (Trim):**
    *   Extrae fragmentos específicos de un stem en cuestión de segundos.
* **🧹 Gestión de Espacio:**
    *   Endpoint dedicado para limpiar el espacio de trabajo de manera eficiente, eliminando archivos residuales.

---

## 🛠️ Instalación y Configuración

Parrot incluye un **Smart Launcher** nativo que automatiza por completo la instalación de dependencias y modelos de IA pesados.

### Instalación Rápida (Usuarios)
1. Ve a la pestaña de [Releases](../../releases) en GitHub y descarga la versión para tu sistema operativo.
2. **Windows:** corré `Parrot_Setup_Windows.exe` y seguí el instalador (podés elegir crear acceso directo en el Escritorio). **macOS:** abrí `Parrot.app`. **Linux:** dale permisos de ejecución y corré `Parrot_Linux.AppImage`.
3. El Launcher instalará Python automáticamente (si no lo tienes) y descargará los requerimientos la primera vez. Si detecta una GPU NVIDIA compatible, te va a preguntar si preferís la versión acelerada por CUDA o la versión CPU.
4. ¡Listo! Tu navegador se abrirá con la interfaz de Parrot. Las siguientes veces que lo abras iniciará al instante.

> **⚠️ Nota para usuarios de macOS:**
> Al ser una aplicación de código abierto sin firma de Apple Developer ID, macOS podría impedir su ejecución inicial por seguridad (Gatekeeper). Si el sistema bloquea la app, dirígete a **Ajustes del Sistema > Privacidad y seguridad**, desplázate hasta el apartado de seguridad y haz clic en **"Abrir de todos modos"** para autorizarla. Si en cambio ves un mensaje de que la app "está dañada", abre la Terminal y ejecuta `xattr -cr /ruta/a/Parrot.app` (usualmente en `~/Downloads` o `/Applications`) antes de intentar abrirla de nuevo.

### Instalación Manual (Desarrolladores)
1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/JJaroll/Parrot.git
    cd Parrot
    ```
2.  **Crear un entorno virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows usa: .\venv\Scripts\activate
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Uso

Ejecuta el servidor principal:

```bash
python main.py
```
El servidor iniciará en `http://0.0.0.0:8001`.

*   **Dashboard / UI:** Abre tu navegador y ve a `http://localhost:8001/` para acceder a la interfaz web interactiva.
*   **Documentación API (Swagger):** Ve a `http://localhost:8001/docs` para ver y probar los endpoints.

## 📡 Endpoints Principales

*   `POST /api/v1/separate`: Sube un archivo de audio y lo pone en cola para separar los stems.
*   `GET /api/v1/status/{job_id}`: Consulta el estado de un trabajo de separación.
*   `POST /api/v1/transcribe/{job_id}`: Inicia la transcripción (por defecto 'vocals') usando Whisper.
*   `GET /api/v1/trim/{job_id}`: Recorta un fragmento específico de un stem [start, end].
*   `POST /api/v1/merge/{job_id}`: Mezcla stems con post-producción (EQ, Paneo, Normalización).
*   `POST /api/v1/cleanup`: Limpia los directorios de trabajo y libera espacio.

## 📁 Estructura del Proyecto

* **main.py:** Punto de entrada. Define la API de FastAPI y la interfaz con los servicios.
* **frontend/:** Contiene el código (HTML/JS/CSS) de la interfaz interactiva.
* **services/:**
  * **separator.py:** Lógica de separación de audio.
  * **mixer.py:** Lógica para recorte y re-mezcla (post-producción).
  * **transcriber.py:** Sistema de transcripción de audio (Whisper).
* **workspace/:** Directorio temporal donde se almacenan audios originales y trabajos procesados.

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1.  Haz un **Fork** del proyecto.
2.  Crea una rama (`git checkout -b feature/NuevaFuncion`).
3.  Haz tus cambios y commits.
4.  Haz Push a la rama (`git push origin feature/NuevaFuncion`).
5.  Abre un **Pull Request**.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

Creado con ❤️ por **JJaroll**
