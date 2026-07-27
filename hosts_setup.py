"""
Módulo para administrar y configurar la resolución de nombres local en el archivo hosts del sistema
(/etc/hosts en macOS/Linux o System32/drivers/etc/hosts en Windows) para mapear parrot.local.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOSTNAME = "parrot.local"
TARGET_IP = "127.0.0.1"
HOSTS_ENTRY = f"{TARGET_IP}\t{HOSTNAME}\t# Parrot Audio Studio"


def _hosts_file_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def is_hostname_mapped(hostname: str = HOSTNAME) -> bool:
    try:
        content = _hosts_file_path().read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split("#", 1)[0].split()
        if len(fields) >= 2 and hostname in fields[1:]:
            return True
    return False


def _append_macos() -> bool:
    try:
        shell_cmd = f"echo '{HOSTS_ENTRY}' | tee -a /etc/hosts"
        script = f'do shell script "{shell_cmd}" with administrator privileges'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"[Parrot] No se pudo escribir en /etc/hosts (macOS): {e}")
        return False


def _append_windows() -> bool:
    ps1_path = None
    try:
        hosts_path = _hosts_file_path()
        fd, ps1_path = tempfile.mkstemp(suffix=".ps1", prefix="parrot_hosts_")
        os.close(fd)
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(f'Add-Content -Path "{hosts_path}" -Value "{HOSTS_ENTRY}" -Encoding ASCII\n')

        elevated_cmd = (
            f"Start-Process powershell -ArgumentList "
            f"'-NoProfile -ExecutionPolicy Bypass -File \"{ps1_path}\"' -Verb RunAs -Wait"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", elevated_cmd],
            capture_output=True, text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Parrot] No se pudo escribir en el archivo hosts (Windows): {e}")
        return False
    finally:
        if ps1_path:
            try:
                os.remove(ps1_path)
            except OSError:
                pass


def _append_linux() -> bool:
    hosts_path = str(_hosts_file_path())
    try:
        if shutil.which("pkexec"):
            cmd = ["pkexec", "tee", "-a", hosts_path]
        elif shutil.which("sudo"):
            cmd = ["sudo", "tee", "-a", hosts_path]
        else:
            print("[Parrot] No se encontró pkexec ni sudo para editar el archivo hosts.")
            return False
        result = subprocess.run(cmd, input=HOSTS_ENTRY + "\n", capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"[Parrot] No se pudo escribir en /etc/hosts (Linux): {e}")
        return False


def ensure_local_hostname(on_before_prompt=None) -> bool:
    if is_hostname_mapped():
        return True

    if on_before_prompt:
        try:
            on_before_prompt()
        except Exception:
            pass

    if sys.platform == "darwin":
        ok = _append_macos()
    elif sys.platform == "win32":
        ok = _append_windows()
    else:
        ok = _append_linux()

    if ok:
        ok = is_hostname_mapped()

    if not ok:
        print(f"[Parrot] No se pudo configurar '{HOSTNAME}'. Se usará http://{TARGET_IP} como respaldo.")

    return ok
