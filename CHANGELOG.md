# Historial de Cambios

Todos los cambios notables de este proyecto se documentarán en este archivo.

## [Unreleased]
### Corregido
- El ícono de la app compilada era el genérico de Python: faltaba el flag `--icon` en los comandos de PyInstaller (Windows/macOS).
- macOS mostraba "Parrot.app está dañado y no puede abrirse": el workflow de release modificaba el contenido del `.app` después de que PyInstaller lo firmara (ad-hoc), invalidando la firma. Ahora se vuelve a firmar (`codesign --deep --force --sign -`) al final del paso de empaquetado de macOS.

### Agregado
- Nota en el README sobre cómo abrir la app en macOS si Gatekeeper la bloquea o la marca como dañada.

## [0.1.0] - 2026-07-19
### Agregado
- Separación de audio en 6 stems (voz, batería, bajo, piano, guitarra, otros) con Demucs v4, con barra de progreso real durante el procesamiento.
- Editor de mezcla multipista: volumen, pan, noise gate, filtro pasa-altos y EQ de 3 bandas por pista, con previsualización en vivo y normalización final.
- Recorte (trim) y descarga individual de cada stem.
- Transcripción de la pista de voz con Whisper (local), con exportación a `.srt` y `.txt`.
- Exportación configurable al mezclar: solo audio, solo video o mezcla completa (audio remezclado + video original), en WAV 44.1/48kHz o MP3 192/320kbps.
- Modal de vista previa (Preview) para escuchar o ver el resultado antes de descargarlo.
- Soporte multi-idioma (Español, Inglés, Japonés) y 5 temas de color de acento, con Claro + Naranja como tema por defecto.
- Historial de trabajos persistente en el navegador, con reanudación automática de la sesión si se recarga la página.
- Ícono de bandeja del sistema (tray icon), favicon y logo dinámicos según el color de acento elegido.
- Acceso a la app vía `http://parrot.local:8001` en vez de la IP cruda, mediante una entrada automática en el archivo hosts del sistema (con fallback a la IP si no se puede escribir).
- Smart Launcher multiplataforma (Windows/macOS/Linux) que instala Python y dependencias automáticamente en el primer arranque; arquitectura documentada en `SMART_LAUNCHER.txt`.
- Flujo de compilación y publicación automática vía GitHub Actions para Windows (`.zip`), macOS (`.dmg`) y Linux (`.AppImage`).

### Corregido
- (Hotfix incluido en este release) El workflow de release no empaquetaba `tray_icon.py`, `hosts_setup.py` ni la carpeta `static/`, lo que rompía la app apenas alguien la abría.
