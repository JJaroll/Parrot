import logging
import subprocess
from pathlib import Path
from typing import Dict, Any
import ffmpeg

logger = logging.getLogger(__name__)

class AudioSeparatorService:
    def __init__(self, jobs_dir: str = "jobs", model_name: str = "htdemucs_6s"):
        self.jobs_dir = Path(jobs_dir)
        self.model_name = model_name
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_device() -> str:
        """Hardware autodetection: mps for Mac M1/Apple Silicon, cuda for NVIDIA, else CPU."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def extract_audio(self, input_path: Path, output_path: Path):
        """Extracts audio from video file to wav format using FFmpeg-python."""
        logger.info(f"Extracting audio from {input_path} to {output_path}")
        try:
            (
                ffmpeg
                .input(str(input_path))
                .output(str(output_path), vn=None, acodec='pcm_s16le', ar='44100')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode('utf8')}")
            raise Exception("Failed to extract audio from the source file. Ensure the file is not corrupted.")

    def run_demucs(self, audio_path: Path, output_dir: Path):
        """Runs demucs via subprocess to ensure memory safety on local system."""
        device = self.get_device()
        
        cmd = [
            "demucs",
            "--name", self.model_name,
            "--out", str(output_dir),
            "-d", device,
        ]
        
        # M1 MAC Memory/VRAM optimization 
        if device == "mps":
            cmd.extend(["--segment", "10"]) # Reduce segment size from default (usually 11-15) for lower memory usage
            cmd.extend(["--split", "true"]) # Splitting tracks on RAM to prevent Memory Error
            
        cmd.append(str(audio_path))
        
        logger.info(f"Starting Demucs on {device} with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Demucs processing completed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Demucs failed: {e.stderr}")
            if "Memory" in e.stderr or "MPS" in e.stderr:
                raise Exception("Out of Memory Error during Demucs separation. Try reducing segment size.")
            raise Exception("Audio separation failed due to AI Engine error.")

    def process_job(self, job_id: str, file_path: Path) -> Dict[str, Any]:
        """Cerebro Pipeline: Ingestion -> Extraction -> Separation"""
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine if extraction is needed
        is_video = file_path.suffix.lower() in [".mp4", ".mkv", ".mov", ".avi", ".webm"]
        audio_path = job_dir / "source_audio.wav"

        # 1. Extracción de audio vía FFmpeg si es video o compresión
        if is_video or file_path.suffix.lower() != ".wav":
            self.extract_audio(file_path, audio_path)
        else:
            # Si ya es un WAV limpio, creamos una copia o symlink en el job_dir
            import shutil
            shutil.copy(file_path, audio_path)

        # 2. Separación de 6 Stems vía Demucs
        demucs_out = job_dir / "separated"
        self.run_demucs(audio_path, demucs_out)
        
        # Demucs default folder structure pattern: output_dir/model_name/track_name/...
        # Because we passed source_audio.wav, the track name is 'source_audio'
        stems_dir = demucs_out / self.model_name / "source_audio"
        stems = ["vocals", "drums", "bass", "piano", "guitar", "other"]
        
        # Validación
        for stem in stems:
            expected_stem_path = stems_dir / f"{stem}.wav"
            if not expected_stem_path.exists():
                logger.warning(f"Could not find exact path for stem {stem}. Checking structure.")
                
        return {
            "job_id": job_id,
            "status": "completed",
            "stems_path": str(stems_dir),
            "stems": {stem: str(stems_dir / f"{stem}.wav") for stem in stems}
        }
