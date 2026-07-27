"""
Lanzador e instalador ejecutable de escritorio para Parrot Audio Studio.
Se encarga de verificar el entorno, instalar dependencias (Python, PyTorch, Whisper, Demucs, FFmpeg),
manejar la interfaz gráfica de instalación (Tkinter) y ejecutar la aplicación FastAPI en segundo plano.
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
import shutil
import urllib.request
import tempfile

if sys.stdout is None or sys.stderr is None:
    _log_dir = Path.home() / ".parrot_studio"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file = open(_log_dir / "launcher.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = _log_file
    sys.stderr = _log_file

def show_msg(title, text):
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display dialog "{text}" with title "{title}" buttons {{"OK"}} default button "OK" giving up after 10'])
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
        else:
            if shutil.which("zenity"):
                subprocess.run(["zenity", "--info", "--title", title, "--text", text])
            elif shutil.which("kdialog"):
                subprocess.run(["kdialog", "--msgbox", text, "--title", title])
            else:
                print(f"{title}: {text}")
    except Exception as e:
        print(f"{title}: {text}")

def confirm_msg(title, text, yes_label="Instalar", no_label="Cancelar"):
    try:
        if sys.platform == "darwin":
            script = (
                f'display dialog "{text}" with title "{title}" '
                f'buttons {{"{no_label}", "{yes_label}"}} default button "{yes_label}" giving up after 30'
            )
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return f"button returned:{no_label}" not in result.stdout
        elif sys.platform == "win32":
            import ctypes
            MB_YESNO = 0x4
            MB_ICONQUESTION = 0x20
            IDYES = 6
            full_text = f"{text}\n\n[Sí] = {yes_label}\n[No] = {no_label}"
            res = ctypes.windll.user32.MessageBoxW(0, full_text, title, MB_YESNO | MB_ICONQUESTION)
            return res == IDYES
        else:
            if shutil.which("zenity"):
                res = subprocess.run(["zenity", "--question", "--title", title, "--text", text,
                                       "--ok-label", yes_label, "--cancel-label", no_label])
                return res.returncode == 0
            elif shutil.which("kdialog"):
                res = subprocess.run(["kdialog", "--yesno", text, "--title", title,
                                       "--yes-label", yes_label, "--no-label", no_label])
                return res.returncode == 0
            else:
                print(f"{title}: {text}")
                return True
    except Exception as e:
        print(f"{title}: {text} ({e})")
        return True

def notify_progress(text):
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{text}" with title "Parrot"'])
        else:
            print(text)
    except Exception:
        print(text)

def find_mac_python():
    import glob
    candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3"]
    candidates += sorted(glob.glob("/Library/Frameworks/Python.framework/Versions/3.*/bin/python3"), reverse=True)
    for path in candidates:
        if Path(path).exists():
            return path
    return None

MIN_PYTHON_VERSION = (3, 10)
MAX_PYTHON_VERSION = (3, 13)


def get_python_version(python_cmd):
    try:
        result = subprocess.run(
            [python_cmd, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            capture_output=True, text=True, timeout=10,
        )
        major, minor = (int(x) for x in result.stdout.strip().split("."))
        return (major, minor)
    except Exception:
        return None


def is_supported_python(python_cmd):
    version = get_python_version(python_cmd)
    return version is not None and MIN_PYTHON_VERSION <= version <= MAX_PYTHON_VERSION

FFMPEG_WIN_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip"
FFMPEG_LINUX_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-lgpl.tar.xz"
PARROT_FFMPEG_MACOS_URL = "https://github.com/JJaroll/Parrot/releases/latest/download/Parrot_ffmpeg_macos_arm64_lgpl.zip"


def _extract_named_binaries(archive_path, wanted_names, dest_dir):
    found = set()
    if str(archive_path).endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.namelist():
                base = Path(member).name
                if base in wanted_names and base not in found:
                    with zf.open(member) as src, open(dest_dir / base, "wb") as dst:
                        dst.write(src.read())
                    found.add(base)
    else:
        import tarfile
        with tarfile.open(archive_path, "r:xz") as tf:
            for member in tf.getmembers():
                base = Path(member.name).name
                if member.isfile() and base in wanted_names and base not in found:
                    extracted = tf.extractfile(member)
                    if extracted:
                        with open(dest_dir / base, "wb") as dst:
                            dst.write(extracted.read())
                    found.add(base)
    return found


def _fetch_evermeet_url(tool_name):
    with urllib.request.urlopen(f"https://evermeet.cx/ffmpeg/info/{tool_name}/release", timeout=15) as r:
        data = json.load(r)
    return data["download"]["zip"]["url"]


def ensure_ffmpeg():
    exe_suffix = ".exe" if sys.platform == "win32" else ""
    wanted = {f"ffmpeg{exe_suffix}", f"ffprobe{exe_suffix}"}

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return None

    bin_dir = Path.home() / ".parrot_studio" / "bin"
    if all((bin_dir / name).exists() for name in wanted):
        return str(bin_dir)

    bin_dir.mkdir(parents=True, exist_ok=True)
    notify_progress("Descargando ffmpeg (una sola vez, puede tardar un minuto)...")

    try:
        if sys.platform == "win32":
            archive_urls = [FFMPEG_WIN_URL]
        elif sys.platform == "darwin":
            try:
                archive_path = bin_dir / Path(PARROT_FFMPEG_MACOS_URL).name
                urllib.request.urlretrieve(PARROT_FFMPEG_MACOS_URL, archive_path)
                _extract_named_binaries(archive_path, wanted, bin_dir)
                archive_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"[Parrot] Build propia de ffmpeg no disponible ({e}), usando evermeet.cx como respaldo.")
            archive_urls = [] if all((bin_dir / name).exists() for name in wanted) else [
                _fetch_evermeet_url("ffmpeg"), _fetch_evermeet_url("ffprobe")
            ]
        else:
            archive_urls = [FFMPEG_LINUX_URL]

        for url in archive_urls:
            archive_path = bin_dir / Path(url).name
            urllib.request.urlretrieve(url, archive_path)
            _extract_named_binaries(archive_path, wanted, bin_dir)
            archive_path.unlink(missing_ok=True)

        if sys.platform != "win32":
            for name in wanted:
                path = bin_dir / name
                if path.exists():
                    os.chmod(path, 0o755)

        if all((bin_dir / name).exists() for name in wanted):
            return str(bin_dir)
        print("[Parrot] No se pudo obtener ffmpeg/ffprobe del paquete descargado.")
    except Exception as e:
        print(f"[Parrot] No se pudo descargar ffmpeg automáticamente: {e}")

    return None

TORCH_CUDA_INDEXES = [((12, 9), "cu129"), ((12, 8), "cu128"), ((12, 6), "cu126")]


def detect_cuda_index():
    if sys.platform == "darwin" or not shutil.which("nvidia-smi"):
        return None
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        match = re.search(r"CUDA Version:\s*([\d.]+)", result.stdout)
        if not match:
            return None
        driver_cuda = tuple(int(x) for x in match.group(1).split("."))
    except Exception:
        return None

    for min_version, index_name in TORCH_CUDA_INDEXES:
        if driver_cuda >= min_version:
            return index_name
    return None

def run_install_with_gui(steps):
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

    if tk.TkVersion < 8.6:
        return _run_without_gui()

    import threading
    import queue

    try:
        root = tk.Tk()
    except Exception:
        return _run_without_gui()
    root.title("Instalando Parrot")
    root.geometry("560x420")
    root.resizable(False, False)

    status_var = tk.StringVar(value="Preparando instalación...")
    tk.Label(root, textvariable=status_var, font=("Helvetica", 12, "bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 4))

    progress = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
    progress.pack(fill="x", padx=16, pady=4)

    pct_var = tk.StringVar(value="0%")
    tk.Label(root, textvariable=pct_var, anchor="e").pack(fill="x", padx=16)

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
                    return
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
    if getattr(sys, 'frozen', False):
        exec_dir = Path(sys.executable).parent
        
        if sys.platform == "darwin" and "Contents/MacOS" in str(exec_dir):
            return exec_dir.parent / "Resources" / "src"
            
        if sys.platform == "linux" and "APPIMAGE" in os.environ:
            appdir = os.environ.get("APPDIR")
            if appdir:
                return Path(appdir) / "usr" / "src"
                
        return exec_dir
    else:
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
            subprocess.run([installer_path, "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0"], check=True)
            
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            possible_py = Path(local_appdata) / "Programs" / "Python" / "Python311" / "python.exe"
            if possible_py.exists():
                return str(possible_py)
            return "python"
            
        elif sys.platform == "darwin":
            script = f'do shell script "installer -pkg {installer_path} -target /" with administrator privileges'
            subprocess.run(["osascript", "-e", script], check=True)

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

    home = Path.home()
    app_data_dir = home / ".parrot_studio"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    
    venv_dir = app_data_dir / "venv"
    
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"

    install_marker = venv_dir / ".install_complete"

    if not python_exe.exists() or not install_marker.exists():
        msg = ("Primera ejecución detectada.\n\n"
               "Se configurará el entorno y se descargarán los modelos de IA (PyTorch, Whisper, Demucs). "
               "Esto tomará varios minutos dependiendo de tu conexión a internet.\n\n"
               "La aplicación se abrirá sola al terminar.")
        if not confirm_msg("Instalador de Parrot", msg):
            sys.exit(0)
        
        system_python = sys.executable if not getattr(sys, 'frozen', False) else "python3"
        if sys.platform == "win32" and getattr(sys, 'frozen', False):
             system_python = "python"
             
        if not shutil.which(system_python):
            if sys.platform == "win32" and shutil.which("py"):
                system_python = "py"
            elif sys.platform == "win32" and shutil.which("python3"):
                system_python = "python3"
            elif sys.platform == "darwin" and find_mac_python():
                system_python = find_mac_python()
            else:
                system_python = install_python()

        if sys.platform in ("win32", "darwin") and not is_supported_python(system_python):
            print(f"[Parrot] Python del sistema ({system_python}) no está en el rango soportado "
                  f"({MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}-{MAX_PYTHON_VERSION[0]}.{MAX_PYTHON_VERSION[1]}); "
                  "descargando una versión compatible...")
            system_python = install_python()

        req_lines = [l for l in requirements.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]

        cuda_index = detect_cuda_index()
        use_cuda = False
        if cuda_index:
            use_cuda = confirm_msg(
                "GPU NVIDIA detectada",
                "Se detectó una GPU NVIDIA compatible con CUDA en este equipo.\n\n"
                "La versión CUDA usa la GPU para acelerar varias veces la separación de audio, "
                "pero descarga varios GB adicionales. La versión CPU es más liviana pero más lenta.",
                yes_label="Instalar versión CUDA",
                no_label="Instalar versión CPU",
            )

        install_steps = [
            ("Creando entorno virtual...", [system_python, "-m", "venv", str(venv_dir)], None),
            ("Actualizando pip...", [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], None),
        ]

        if use_cuda:
            install_steps.append((
                f"Instalando PyTorch con soporte CUDA ({cuda_index})...",
                [str(python_exe), "-m", "pip", "install", "torch==2.8.0", "torchaudio==2.8.0",
                 "--index-url", f"https://download.pytorch.org/whl/{cuda_index}"],
                2,
            ))
            req_lines = [l for l in req_lines if not l.lower().startswith(("torch==", "torchaudio=="))]

        install_steps.append((
            "Instalando PyTorch, Whisper y Demucs (puede tardar varios minutos)...",
            [str(python_exe), "-m", "pip", "install"] + req_lines,
            len(req_lines),
        ))

        ok, error = run_install_with_gui(install_steps)
        if not ok:
            if error == "Instalación cancelada por el usuario.":
                sys.exit(0)
            show_msg("Error Crítico", f"Falló la instalación.\nAsegúrate de tener Python 3.10+ instalado en tu sistema y agregado al PATH.\n\nDetalles técnicos: {error}")
            sys.exit(1)
        install_marker.touch()

    print("Iniciando servidor Parrot...")

    ffmpeg_bin_dir = ensure_ffmpeg()
    env = os.environ.copy()
    if ffmpeg_bin_dir:
        env["PATH"] = ffmpeg_bin_dir + os.pathsep + env.get("PATH", "")

    server_log = open(app_data_dir / "parrot_server.log", "a", encoding="utf-8", buffering=1)
    popen_kwargs = {"cwd": str(app_data_dir), "env": env, "stdout": server_log, "stderr": server_log}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen([str(python_exe), str(main_py)], **popen_kwargs)
    print("Parrot quedó corriendo como proceso independiente (ver el ícono de bandeja para cerrarlo).")

    if sys.platform == "linux":
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
        return
    os._exit(0)

if __name__ == "__main__":
    main()
