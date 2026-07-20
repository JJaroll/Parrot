import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import ffmpeg

logger = logging.getLogger(__name__)

PROGRESS_RE = re.compile(r'(\d+)%\|')

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

    def run_demucs(self, audio_path: Path, output_dir: Path, on_progress: Optional[Callable[[int], None]] = None):
        device = self.get_device()

        import sys
        cmd = [
            sys.executable, "-m", "demucs.separate",
            "--name", self.model_name,
            "--out", str(output_dir),
            "-d", device,
        ]

        # MAC Memory/VRAM optimization
        if device == "mps":
            cmd.extend(["--segment", "7"])
        cmd.append(str(audio_path))

        logger.info(f"Starting Demucs on {device} with command: {' '.join(cmd)}")

        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)
        stderr_tail = []
        buf = ""
        try:
            while True:
                chunk = process.stderr.read(256)
                if not chunk:
                    break
                buf += chunk
                *complete, buf = re.split(r'[\r\n]', buf)
                for piece in complete:
                    piece = piece.strip()
                    if not piece:
                        continue
                    stderr_tail.append(piece)
                    if len(stderr_tail) > 30:
                        stderr_tail.pop(0)
                    if on_progress:
                        match = PROGRESS_RE.search(piece)
                        if match:
                            on_progress(min(99, int(match.group(1))))
        finally:
            process.stderr.close()
            returncode = process.wait()

        if returncode != 0:
            error_details = "\n".join(stderr_tail)
            logger.error(f"Demucs failed: {error_details}")
            if "Memory" in error_details or "MPS" in error_details:
                raise Exception(f"Out of Memory Error during Demucs separation. Try reducing segment size.\nDetails: {error_details}")
            raise Exception(f"Audio separation failed. AI Engine Details: {error_details}")

        logger.info("Demucs processing completed successfully.")
        if on_progress:
            on_progress(100)

    def process_job(self, job_id: str, file_path: Path, on_progress: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        #Cerebro Pipeline: Ingestion -> Extraction -> Separation
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        is_video = file_path.suffix.lower() in [".mp4", ".mkv", ".mov", ".avi", ".webm"]
        audio_path = job_dir / "source_audio.wav"

        if is_video or file_path.suffix.lower() != ".wav":
            self.extract_audio(file_path, audio_path)
        else:
            import shutil
            shutil.copy(file_path, audio_path)

        demucs_out = job_dir / "separated_raw"
        self.run_demucs(audio_path, demucs_out, on_progress=on_progress)
        
        raw_stems_dir = demucs_out / self.model_name / "source_audio"
        stems_dir = job_dir / "separated"
        stems_dir.mkdir(parents=True, exist_ok=True)
        stems = ["vocals", "drums", "bass", "piano", "guitar", "other"]
        
        import shutil
        for stem in stems:
            stem_src = raw_stems_dir / f"{stem}.wav"
            if stem_src.exists():
                shutil.move(str(stem_src), str(stems_dir / f"{stem}.wav"))
                
        if demucs_out.exists():
            shutil.rmtree(demucs_out)
                
        return {
            "job_id": job_id,
            "status": "completed",
            "stems_path": str(stems_dir),
            "stems": {stem: str(stems_dir / f"{stem}.wav") for stem in stems},
            "is_video": is_video,
        }
