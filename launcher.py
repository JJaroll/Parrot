import os
import sys
import subprocess
from pathlib import Path
import shutil
import urllib.request
import tempfile

def show_msg(title, text):
    #Muestra un cuadro de diálogo nativo según el sistema operativo.
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display dialog "{text}" with title "{title}" buttons {{"OK"}} default button "OK" giving up after 10'])
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
        else:
            # Intenta usar zenity o kdialog en Linux
            if shutil.which("zenity"):
                subprocess.run(["zenity", "--info", "--title", title, "--text", text])
            elif shutil.which("kdialog"):
                subprocess.run(["kdialog", "--msgbox", text, "--title", title])
            else:
                print(f"{title}: {text}")
    except Exception as e:
        print(f"{title}: {text}")

def get_source_dir():
    #Detecta dónde está el código fuente (main.py y requirements.txt)
    if getattr(sys, 'frozen', False):
        exec_dir = Path(sys.executable).parent
        
        # Modo macOS: El ejecutable está dentro de Parrot.app/Contents/MacOS
        if sys.platform == "darwin" and "Contents/MacOS" in str(exec_dir):
            return exec_dir.parent / "Resources" / "src"
            
        # Modo Linux: AppImage monta un directorio temporal de solo lectura
        if sys.platform == "linux" and "APPIMAGE" in os.environ:
            appdir = os.environ.get("APPDIR")
            if appdir:
                return Path(appdir) / "usr" / "src"
                
        # Modo Windows: Ejecutable y código fuente están en la misma carpeta ZIP extraída
        return exec_dir
    else:
        # Ejecutando como script normal
        return Path(__file__).parent

def install_python():
    if sys.platform == "win32":
        url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
        installer_name = "python-installer.exe"
    elif sys.platform == "darwin":
        url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg"
        installer_name = "python-installer.pkg"
    else:
        show_msg("Requisito Faltante", "Parrot necesita Python 3. Por favor, instálalo (ej. sudo apt install python3 python3-venv) y vuelve a intentar.")
        sys.exit(1)

    msg = ("Parrot necesita Python 3 para funcionar, pero no se encontró en tu sistema.\n\n"
           "A continuación se descargará e instalará de forma completamente automática en segundo plano.\n"
           "En macOS, es posible que se te solicite tu contraseña para proceder.\n\n"
           "Por favor, dale a OK y espera. Esto tomará un par de minutos.")
    show_msg("Instalación Automática de Python", msg)

    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, installer_name)
    
    try:
        print(f"Descargando Python desde {url}...")
        urllib.request.urlretrieve(url, installer_path)
        
        print("Instalando de forma silenciosa. Por favor espera...")
        if sys.platform == "win32":
            # Instalación silenciosa por usuario
            subprocess.run([installer_path, "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0"], check=True)
            
            # El Python local se instala en %LocalAppData%\Programs\Python\Python311\python.exe
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            possible_py = Path(local_appdata) / "Programs" / "Python" / "Python311" / "python.exe"
            if possible_py.exists():
                return str(possible_py)
            return "python" # fallback
            
        elif sys.platform == "darwin":
            # Instalación en macOS (requiere credenciales, osascript muestra el popup nativo del sistema)
            script = f'do shell script "installer -pkg {installer_path} -target /" with administrator privileges'
            subprocess.run(["osascript", "-e", script], check=True)
            return "python3"
            
    except Exception as e:
        show_msg("Error", f"Falló la instalación automática de Python. Detalles: {e}\nPor favor instálalo manualmente desde python.org")
        sys.exit(1)

def main():
    source_dir = get_source_dir()
    main_py = source_dir / "main.py"
    requirements = source_dir / "requirements.txt"
    
    if not main_py.exists():
        show_msg("Error", f"No se encontró main.py en {source_dir}. Asegúrate de extraer todos los archivos del ZIP.")
        sys.exit(1)

    # El entorno virtual y los archivos generados vivirán en el directorio del usuario
    home = Path.home()
    app_data_dir = home / ".parrot_studio"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    
    venv_dir = app_data_dir / "venv"
    
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"

    # FASE DE INSTALACIÓN
    if not python_exe.exists():
        msg = ("Primera ejecución detectada.\n\n"
               "Se configurará el entorno y se descargarán los modelos de IA (PyTorch, Whisper, Demucs). "
               "Esto tomará varios minutos dependiendo de tu conexión a internet.\n\n"
               "La aplicación se abrirá sola al terminar. Dale a OK para comenzar.")
        show_msg("Instalador de Parrot", msg)
        
        # Encontrar el ejecutable de python del sistema para crear el venv
        system_python = sys.executable if not getattr(sys, 'frozen', False) else "python3"
        if sys.platform == "win32" and getattr(sys, 'frozen', False):
             system_python = "python"
             
        # Verificar si python está instalado y disponible
        if not shutil.which(system_python):
            if sys.platform == "win32" and shutil.which("py"):
                system_python = "py"
            elif sys.platform == "win32" and shutil.which("python3"):
                system_python = "python3"
            else:
                system_python = install_python()
             
        try:
            # 1. Crear entorno virtual
            subprocess.run([system_python, "-m", "venv", str(venv_dir)], check=True)
            # 2. Actualizar pip
            subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)
            # 3. Instalar requerimientos apuntando a la ruta origen
            subprocess.run([str(python_exe), "-m", "pip", "install", "-r", str(requirements)], check=True)
        except Exception as e:
            show_msg("Error Crítico", f"Falló la instalación.\nAsegúrate de tener Python 3.10+ instalado en tu sistema y agregado al PATH.\n\nDetalles técnicos: {e}")
            sys.exit(1)

    # FASE DE EJECUCIÓN
    print("Iniciando servidor Parrot...")
    process = subprocess.Popen([str(python_exe), str(main_py)], cwd=str(app_data_dir))

    print("Servidor en ejecución. Cierra esta ventana/terminal para apagar Parrot.")
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()

if __name__ == "__main__":
    main()
