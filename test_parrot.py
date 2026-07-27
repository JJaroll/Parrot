"""
Script de verificación para comprobar la detección del acelerador de hardware MPS (Metal Performance Shaders) en Apple Silicon.
"""

import torch
import subprocess

if torch.backends.mps.is_available():
    print("✅ ¡Éxito! Parrot detectó el acelerador del Mac M1.")
else:
    print("⚠️ Parrot usará la CPU (será más lento). Revisa la versión de Torch.")