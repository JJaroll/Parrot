import torch
import subprocess

# 1. Verificamos que PyTorch vea tu chip M1
if torch.backends.mps.is_available():
    print("✅ ¡Éxito! Parrot detectó el acelerador del Mac M1.")
else:
    print("⚠️ Parrot usará la CPU (será más lento). Revisa la versión de Torch.")

# 2. Prueba rápida de comando (si tienes un audio a mano)
# demucs -n htdemucs_6s tu_audio.mp3