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

def confirm_msg(title, text):
    """Como show_msg, pero con opción real de Cancelar. Devuelve True si el usuario
    eligió continuar (o si el diálogo se cerró solo por el timeout en macOS, igual que
    antes), False si canceló explícitamente."""
    try:
        if sys.platform == "darwin":
            script = (
                f'display dialog "{text}" with title "{title}" '
                f'buttons {{"Cancelar", "Instalar"}} default button "Instalar" giving up after 30'
            )
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return "button returned:Cancelar" not in result.stdout
        elif sys.platform == "win32":
            import ctypes
            MB_OKCANCEL = 0x1
            MB_ICONINFORMATION = 0x40
            IDOK = 1
            res = ctypes.windll.user32.MessageBoxW(0, text, title, MB_OKCANCEL | MB_ICONINFORMATION)
            return res == IDOK
        else:
            if shutil.which("zenity"):
                res = subprocess.run(["zenity", "--question", "--title", title, "--text", text])
                return res.returncode == 0
            elif shutil.which("kdialog"):
                res = subprocess.run(["kdialog", "--yesno", text, "--title", title])
                return res.returncode == 0
            else:
                print(f"{title}: {text}")
                return True
    except Exception as e:
        print(f"{title}: {text} ({e})")
        return True

def notify_progress(text):
    """Aviso liviano de avance durante la instalación. A diferencia de show_msg, no
    requiere que el usuario haga clic: en macOS es un banner de Notificaciones (la app
    corre sin consola visible, --windowed); en Windows/Linux basta con print() porque
    esas builds sí llevan consola (--console)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{text}" with title "Parrot"'])
        else:
            print(text)
    except Exception:
        print(text)

def find_mac_python():
    """Las apps lanzadas con doble clic en Finder no heredan el PATH completo del shell
    (no leen .zshrc/.bash_profile), así que shutil.which() puede no encontrar un Python
    que en realidad sí está instalado. Buscamos directo en las rutas típicas antes de
    asumir que falta y disparar una reinstalación innecesaria."""
    import glob
    candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3"]
    candidates += sorted(glob.glob("/Library/Frameworks/Python.framework/Versions/3.*/bin/python3"), reverse=True)
    for path in candidates:
        if Path(path).exists():
            return path
    return None

def run_install_with_gui(steps):
    """
    Corre los pasos de instalación (crear venv, actualizar pip, instalar requirements) en
    un hilo de fondo mientras muestra una ventana con barra de progreso y los logs en vivo.
    Usa tkinter (viene con Python, no agrega dependencias pesadas de UI).

    steps: lista de (etiqueta, comando, total_para_progreso_o_None). Cuando se da un total
    (ej. cantidad de paquetes en requirements.txt), el progreso de ese paso se estima
    contando líneas "Collecting ..." que imprime pip; si no, el paso simplemente salta a
    100% al terminar.

    Devuelve (ok: bool, error: str | None). Si tkinter no está disponible (o es una build
    de Tk demasiado vieja para confiar en ella, ver más abajo), corre los pasos igual con
    notify_progress como respaldo y nunca bloquea la instalación por esto.
    """
    def _run_without_gui():
        try:
            for label, cmd, _ in steps:
                notify_progress(label)
                subprocess.run(cmd, check=True)
            return True, None
        except Exception as e:
            return False, str(e)

    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return _run_without_gui()

    # Algunas instalaciones de Python en macOS (la de Xcode Command Line Tools, en
    # particular) traen el Tcl/Tk 8.5 del sistema, deprecado por Apple desde hace años.
    # En macOS recientes, tk.Tk() directamente aborta el proceso entero (SIGABRT, no una
    # excepción de Python capturable) en vez de fallar de forma prolija. Tk 8.6+ (lo que
    # trae cualquier Python instalado desde python.org) no tiene este problema.
    if tk.TkVersion < 8.6:
        return _run_without_gui()

    import threading
    import queue

    root = tk.Tk()
    root.title("Instalando Parrot")
    root.geometry("560x420")
    root.resizable(False, False)

    status_var = tk.StringVar(value="Preparando instalación...")
    tk.Label(root, textvariable=status_var, font=("Helvetica", 12, "bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 4))

    progress = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
    progress.pack(fill="x", padx=16, pady=4)

    pct_var = tk.StringVar(value="0%")
    tk.Label(root, textvariable=pct_var, anchor="e").pack(fill="x", padx=16)

    # El botón está visible y activo desde el arranque (como "Cancelar"); al terminar solo se
    # le cambian texto/comando. Antes se creaba oculto y recién se mostraba con pack() al
    # final, y la ventana quedaba sin responder al hacer clic — mostrarlo desde el principio
    # evita esa clase de problema por completo, además de dar una forma real de cancelar.
    button_frame = tk.Frame(root)
    button_frame.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

    log_text = tk.Text(root, height=16, bg="#111111", fg="#33ff66", font=("Courier", 10))
    log_text.pack(side="top", fill="both", expand=True, padx=16, pady=(8, 8))
    log_text.configure(state="disabled")

    def append_log(line):
        log_text.configure(state="normal")
        log_text.insert("end", line + "\n")
        log_text.see("end")
        log_text.configure(state="disabled")

    log_queue = queue.Queue()
    result = {"ok": True, "error": None}
    cancel_requested = threading.Event()
    current_process = {"proc": None}

    def worker():
        try:
            for label, cmd, req_count in steps:
                if cancel_requested.is_set():
                    break
                log_queue.put(("status", label))
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                current_process["proc"] = process
                ticks = 0
                # pip imprime "Collecting X" de entrada para TODOS los paquetes casi de una
                # (resolución de metadatos), mucho antes de bajar/compilar/instalar nada, así
                # que si solo contáramos eso la barra saltaría a ~100% enseguida y se quedaría
                # pegada ahí durante la parte más lenta. Sumar también "Downloading"/"Using
                # cached"/"Building wheel for" (y duplicar el total esperado, ya que cada
                # paquete típicamente dispara 2 de estas líneas) reparte el avance de forma
                # más pareja a lo largo de todo el proceso, no solo al principio.
                progress_prefixes = ("Collecting ", "Downloading ", "Using cached ", "Building wheel for ")
                for line in process.stdout:
                    if cancel_requested.is_set():
                        process.terminate()
                        break
                    line = line.rstrip()
                    if line:
                        log_queue.put(("log", line))
                    if req_count and line.startswith(progress_prefixes):
                        ticks += 1
                        log_queue.put(("progress", min(95, int(ticks / (req_count * 2) * 100))))
                returncode = process.wait()
                current_process["proc"] = None
                if cancel_requested.is_set():
                    break
                if returncode != 0:
                    raise RuntimeError(f"{label} falló (código {returncode})")
                log_queue.put(("progress", 100))
            else:
                log_queue.put(("done", None))
                return
            log_queue.put(("cancelled", None))
        except Exception as e:
            result["ok"] = False
            result["error"] = str(e)
            log_queue.put(("failed", str(e)))

    def on_finish():
        root.quit()

    def on_cancel():
        cancel_requested.set()
        proc = current_process["proc"]
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        action_btn.configure(state="disabled", text="Cancelando...")

    action_btn = tk.Button(button_frame, text="Cancelar", command=on_cancel)
    action_btn.pack()
    root.protocol("WM_DELETE_WINDOW", on_cancel)

    def poll_queue():
        try:
            while True:
                kind, payload = log_queue.get_nowait()
                if kind == "status":
                    status_var.set(payload)
                elif kind == "log":
                    append_log(payload)
                elif kind == "progress":
                    progress["value"] = payload
                    pct_var.set(f"{payload}%")
                elif kind == "done":
                    status_var.set("Instalación completa.")
                    root.protocol("WM_DELETE_WINDOW", on_finish)
                    action_btn.configure(state="normal", text="Iniciar Parrot", command=on_finish)
                    return  # No reprogramar poll_queue: evita competir con el cierre de la ventana
                elif kind == "failed":
                    status_var.set("Error durante la instalación")
                    root.protocol("WM_DELETE_WINDOW", on_finish)
                    action_btn.configure(state="normal", text="Cerrar", command=on_finish)
                    return
                elif kind == "cancelled":
                    result["ok"] = False
                    result["error"] = "Instalación cancelada por el usuario."
                    status_var.set("Instalación cancelada.")
                    root.protocol("WM_DELETE_WINDOW", on_finish)
                    action_btn.configure(state="normal", text="Cerrar", command=on_finish)
                    return
        except queue.Empty:
            pass
        if root.winfo_exists():
            root.after(100, poll_queue)

    threading.Thread(target=worker, daemon=True).start()
    root.after(100, poll_queue)
    root.mainloop()
    root.destroy()

    return result["ok"], result["error"]

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

            # El instalador no actualiza el PATH de este proceso ya en marcha (y las apps
            # lanzadas con doble clic tienen un PATH mínimo de por sí), así que apuntamos
            # directo a la ruta donde el instalador oficial deja el binario.
            installed_py = Path("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3")
            return str(installed_py) if installed_py.exists() else "python3"
            
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

    # Marca que solo se escribe cuando "pip install -r requirements.txt" termina con éxito.
    # Si solo revisáramos si python_exe existe, una instalación que falló a mitad de camino
    # (venv creado, pero requirements.txt incompleto) se daría por buena en el siguiente
    # arranque y saltaría directo a ejecutar main.py con un entorno roto.
    install_marker = venv_dir / ".install_complete"

    # FASE DE INSTALACIÓN
    if not python_exe.exists() or not install_marker.exists():
        msg = ("Primera ejecución detectada.\n\n"
               "Se configurará el entorno y se descargarán los modelos de IA (PyTorch, Whisper, Demucs). "
               "Esto tomará varios minutos dependiendo de tu conexión a internet.\n\n"
               "La aplicación se abrirá sola al terminar.")
        if not confirm_msg("Instalador de Parrot", msg):
            sys.exit(0)
        
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
            elif sys.platform == "darwin" and find_mac_python():
                system_python = find_mac_python()
            else:
                system_python = install_python()

        req_lines = [l for l in requirements.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
        install_steps = [
            ("Creando entorno virtual...", [system_python, "-m", "venv", str(venv_dir)], None),
            ("Actualizando pip...", [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], None),
            ("Instalando PyTorch, Whisper y Demucs (puede tardar varios minutos)...",
             [str(python_exe), "-m", "pip", "install", "-r", str(requirements)], len(req_lines)),
        ]

        ok, error = run_install_with_gui(install_steps)
        if not ok:
            if error == "Instalación cancelada por el usuario.":
                sys.exit(0)
            show_msg("Error Crítico", f"Falló la instalación.\nAsegúrate de tener Python 3.10+ instalado en tu sistema y agregado al PATH.\n\nDetalles técnicos: {error}")
            sys.exit(1)
        install_marker.touch()

    # FASE DE EJECUCIÓN
    print("Iniciando servidor Parrot...")
    subprocess.Popen([str(python_exe), str(main_py)], cwd=str(app_data_dir))
    print("Parrot quedó corriendo como proceso independiente (ver el ícono de bandeja para cerrarlo).")

    # Terminar el proceso del todo (en vez de quedarse esperando con process.wait()) es la
    # forma confiable de que macOS se saque de encima cualquier resto visual de la ventana de
    # instalación de Tk: si este proceso sigue vivo después de haber mostrado esa ventana, el
    # WindowServer puede dejarla "zombie" en pantalla (cursor de carga infinito) aunque el
    # código ya la haya destruido correctamente, porque nada vuelve a bombear el loop de
    # eventos de Cocoa una vez terminado root.mainloop(). main.py no depende de este proceso
    # (no hereda pipes ni nada por el estilo), así que puede seguir corriendo solo.
    os._exit(0)

if __name__ == "__main__":
    main()
