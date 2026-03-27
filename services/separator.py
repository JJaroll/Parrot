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
            cmd.extend(["--segment", "7"]) # Max segment for htdemucs_6s is 7.8 (must be int)
        cmd.append(str(audio_path))
        
        logger.info(f"Starting Demucs on {device} with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Demucs processing completed successfully.")
        except subprocess.CalledProcessError as e:
            error_details = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"Demucs failed: {error_details}")
            if e.stderr and ("Memory" in e.stderr or "MPS" in e.stderr):
                raise Exception(f"Out of Memory Error during Demucs separation. Try reducing segment size.\nDetails: {error_details}")
            raise Exception(f"Audio separation failed. AI Engine Details: {error_details}")

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
        demucs_out = job_dir / "separated_raw"
        self.run_demucs(audio_path, demucs_out)
        
        # Demucs default folder structure pattern: output_dir/model_name/track_name/...
        raw_stems_dir = demucs_out / self.model_name / "source_audio"
        stems_dir = job_dir / "separated"
        stems_dir.mkdir(parents=True, exist_ok=True)
        stems = ["vocals", "drums", "bass", "piano", "guitar", "other"]
        
        import shutil
        for stem in stems:
            stem_src = raw_stems_dir / f"{stem}.wav"
            if stem_src.exists():
                shutil.move(str(stem_src), str(stems_dir / f"{stem}.wav"))
                
        # Clean up raw demucs output
        if demucs_out.exists():
            shutil.rmtree(demucs_out)
                
        return {
            "job_id": job_id,
            "status": "completed",
            "stems_path": str(stems_dir),
            "stems": {stem: str(stems_dir / f"{stem}.wav") for stem in stems}
        }
