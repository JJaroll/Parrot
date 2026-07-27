# 🦜 Parrot (API & Dashboard de Separación de Audio e IA)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Version](https://img.shields.io/badge/Version-1.0.0-blue)

*🌍 **Español** | [English](README_en.md) | [日本語](README_ja.md)*

**Parrot** es una potente API y Dashboard local para la separación de audio y post-producción impulsada por Inteligencia Artificial. Diseñada para aislar pistas (*stems*) de canciones o archivos de audio con Demucs v4, transcribir las voces aisladas con Whisper y volver a mezclarlas (*Merge*) con control total de post-producción como Ecualización de 3 bandas, Noise Gate y Paneo.

Ideal para productores musicales, músicos, creadores de contenido y desarrolladores que necesitan manipular audio programáticamente o a través de una interfaz web moderna.

## ✨ Características Principales

* **🌍 Soporte Multi-Idioma:**
    * Interfaz y documentación disponibles en Español, Inglés y Japonés.
* **🎛️ Separación de Audio Avanzada (Demucs v4):**
    * Extrae hasta 6 stems individuales: **Voces, Batería, Bajo, Piano, Guitarra y Otros**.
* **🗣️ Transcripción Inteligente (Whisper):**
    * Transcribe las voces aisladas generando automáticamente archivos de subtítulos `.srt` y texto plano `.txt`.
* **🎧 Mezclador y Post-Producción (Merge):**
    * Recombina los stems con ecualización de 3 bandas (Bajos, Medios, Altos), control de volumen por pista, Paneo, Noise Gate y Normalización de audio final.
* **✂️ Edición Rápida (Trim):**
    * Extrae fragmentos específicos de cualquier stem en cuestión de segundos determinando marcas de tiempo exactas.
* **🧹 Gestión de Espacio de Trabajo:**
    * Endpoint y herramientas dedicadas para limpiar directorios de trabajo y eliminar archivos temporales de forma eficiente.
* **⚡ Aceleración de Hardware Inteligente:**
    * Autodetección de GPUs NVIDIA (CUDA), Apple Silicon (MPS) o CPU, con instalador guiado para elegir el motor óptimo.
* **🖥️ Smart Launcher Integrado:**
    * Instalador nativo con barra de progreso en vivo, gestión automática de dependencias y binarios estáticos de `ffmpeg`.

---

## 📥 Descargas e Instalación (Binarios)

¡Parrot está disponible de forma nativa para Windows, macOS y Linux! Puedes descargar la versión compilada lista para usar (sin necesidad de configurar Python manualmente):

### 🍎 macOS
* **Aplicación / Instalador:** Descarga la versión compilada desde la sección de [Releases](https://github.com/JJaroll/Parrot/releases).
  > **⚠️ Nota para usuarios de macOS (Gatekeeper):**
  > Al ser una aplicación de código abierto sin firma de Apple Developer ID, macOS podría impedir su ejecución inicial por seguridad. Si el sistema bloquea la app, dirígete a **Ajustes del Sistema > Privacidad y seguridad**, desplázate hasta el apartado de seguridad y haz clic en **"Abrir de todos modos"**. Si ves un mensaje de que la app "está dañada", abre la Terminal y ejecuta:
  > ```bash
  > xattr -cr /ruta/a/Parrot.app
  > ```

### 🪟 Windows
* **Instalador ejecutable (.exe):** Descarga `Parrot_Setup_Windows.exe` desde [Releases](https://github.com/JJaroll/Parrot/releases).
  > **Instalación:** Ejecuta el instalador guiado. Si el sistema detecta una GPU NVIDIA compatible, te ofrecerá elegir entre la versión acelerada por CUDA o la versión CPU.

### 🐧 Linux
* **Ejecutable Universal (.AppImage):** Descarga `Parrot_Linux.AppImage` desde [Releases](https://github.com/JJaroll/Parrot/releases).
  > **Instalación:** Otorga permisos de ejecución al archivo (`chmod +x Parrot_Linux.AppImage`) y ejecútalo directamente.

---

## 🛠️ Compilación desde el Código Fuente

Si eres desarrollador y prefieres correr o modificar el código fuente directamente:

### Requisitos Previos
* Python 3.10 o superior.
* `ffmpeg` / `ffprobe` instalados en el sistema (el launcher los descarga automáticamente en `~/.parrot_studio/bin` si no están presentes).

### Pasos
1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/JJaroll/Parrot.git
   cd Parrot
   ```

2. **Crear un entorno virtual (Recomendado):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Uso

Ejecuta el servidor principal o el launcher:

```bash
python main.py
```
*(O ejecuta `python launcher.py` para utilizar el asistente de inicio interactivo).*

El servidor iniciará en `http://localhost:8001`.

* **Dashboard Web:** Abre tu navegador y ve a `http://localhost:8001/` para acceder a la interfaz interactiva.
* **Documentación de API (Swagger / OpenAPI):** Accede a `http://localhost:8001/docs` para explorar y probar todos los endpoints REST interactivos.

---

## 📡 Endpoints Principales

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/separate` | `POST` | Sube un archivo de audio/video y lo pone en cola para la separación en stems. |
| `/api/v1/status/{job_id}` | `GET` | Consulta el estado y progreso en tiempo real de un trabajo de procesamiento. |
| `/api/v1/transcribe/{job_id}` | `POST` | Inicia la transcripción con IA (Whisper) sobre las voces aisladas (`.srt` / `.txt`). |
| `/api/v1/trim/{job_id}` | `GET` | Recorta un segmento específico de tiempo `[start, end]` de un stem individual. |
| `/api/v1/merge/{job_id}` | `POST` | Mezcla los stems seleccionados aplicando post-producción (EQ, Paneo, Normalización). |
| `/api/v1/cleanup` | `POST` | Limpia los directorios temporales de trabajo y libera espacio en disco. |
| `/api/v1/system-info` | `GET` | Muestra el motor de aceleración detectado (`cuda`, `mps` o `cpu`). |

---

## 📁 Estructura del Proyecto

| Archivo / Directorio | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada. Servidor FastAPI, endpoints REST y rutas estáticas del frontend. |
| `launcher.py` | Smart Launcher interactivo GUI/CLI que prepara el entorno, venv y dependencias. |
| `services/separator.py` | Motor de separación de audio basado en Demucs v4 (6 stems). |
| `services/mixer.py` | Motor de post-producción, re-mezcla (*merge*), edición (*trim*) y ecualización. |
| `services/transcriber.py` | Servicio de transcripción automática impulsado por Whisper. |
| `frontend/` | Interfaz web interactiva (Dashboard HTML5/CSS3/JavaScript). |
| `workspace/` | Almacenamiento local temporal de audios originales y resultados procesados. |
| `parrot_installer.iss` | Script de compilación de instaladores nativos para Windows (Inno Setup). |

---

## 🔒 Privacidad y Seguridad

**Tus datos se quedan en tu máquina.**

Parrot es una aplicación completamente local. A diferencia de otros servicios en la nube:
* **Procesamiento Local:** Los modelos de IA (Demucs y Whisper) se ejecutan 100% en tu hardware.
* **Sin Telemetría:** No se recopilan ni envían datos personales, telemetría ni archivos de audio a servidores externos.
* **Privacidad Absoluta:** Tus grabaciones, canciones y transcripciones nunca salen de tu dispositivo.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. Haz un **Fork** del proyecto.
2. Crea una rama (`git checkout -b feature/NuevaFuncion`).
3. Haz tus cambios y commits.
4. Haz Push a tu rama (`git push origin feature/NuevaFuncion`).
5. Abre un **Pull Request**.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.
*📝 Consulta los [Términos y Condiciones](TERMS.md) y [Licencias de Terceros](THIRD_PARTY_LICENSES.md).*

Creado con ❤️ por **JJaroll**
