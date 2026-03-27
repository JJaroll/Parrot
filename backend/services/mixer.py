import os
import subprocess

def apply_custom_mix(job_id: str, stem_dir: str, original_file: str, volumes: dict) -> str:
    """
    Genera el mix aplicando volumen a las 6 pistas con FFmpeg.
    Si el archivo original es video, reemplaza el audio sin re-codificar la imagen.
    """
    stems = ["vocals", "drums", "bass", "other", "piano", "guitar"]
    
    # Averiguar si el original es un video usando la extensión
    _, ext = os.path.splitext(original_file)
    is_video = ext.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm"]

    return _run_ffmpeg_mix(job_id, stem_dir, original_file, volumes, is_video)

def _run_ffmpeg_mix(job_id: str, stem_dir: str, original_file: str, volumes: dict, is_video: bool) -> str:
    stems = ["vocals", "drums", "bass", "other", "piano", "guitar"]
    cmd = ["ffmpeg", "-y"]
    
    if is_video:
        cmd.extend(["-i", original_file])
        offset = 1
    else:
        offset = 0

    filter_complex = ""
    for i, stem in enumerate(stems):
        stem_path = os.path.join(stem_dir, f"{stem}.wav")
        if not os.path.exists(stem_path):
            raise FileNotFoundError(f"Falta el archivo: {stem_path}")
        cmd.extend(["-i", stem_path])
        vol = volumes.get(stem, 1.0)
        filter_complex += f"[{i+offset}:a]volume={vol}[a{i}];"
        
    amix_inputs = "".join([f"[a{i}]" for i in range(len(stems))])
    # amerge o amix. Usamos amix con modo "longest" y quitamos la normalización
    filter_complex += f"{amix_inputs}amix=inputs={len(stems)}:duration=longest:normalize=0[aout]"
    
    cmd.extend(["-filter_complex", filter_complex])
    
    # Mantener el formato/extensión original (ej. .MOV -> .MOV)
    _, ext = os.path.splitext(original_file)
    output_path = f"outputs/{job_id}_mixed{ext}"
    
    if is_video:
        cmd.extend(["-map", "0:v:0"])    # Original video
        cmd.extend(["-map", "[aout]"])   # Mixed audio
        cmd.extend(["-c:v", "copy"])     # Stream copy video
        cmd.extend(["-c:a", "aac", "-b:a", "320k"]) 
    else:
        cmd.extend(["-map", "[aout]"])
        cmd.extend(["-c:a", "aac", "-b:a", "320k"])

    cmd.append(output_path)
    subprocess.run(cmd, check=True)
    
    return output_path
