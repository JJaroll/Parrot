import os
import subprocess
import torch

def separate_audio(file_path: str, job_id: str) -> str:
    """
    Ejecuta Demucs para separar el audio en 6 stems.
    Fuerza 'mps' si está en Apple Silicon, sino 'cuda' o 'cpu'.
    """
    output_dir = f"outputs/{job_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    device = "cpu"
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
        
    import sys
    
    # Usando el modelo htdemucs_6s que saca 6 pistas
    cmd = [
        sys.executable, "-m", "demucs.separate",
        "-n", "htdemucs_6s",
        "-d", device,
        "-o", output_dir,
        file_path
    ]
    
    subprocess.run(cmd, check=True)
    
    model_dir = os.path.join(output_dir, "htdemucs_6s")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    stem_dir = os.path.join(model_dir, base_name)
    
    return stem_dir
