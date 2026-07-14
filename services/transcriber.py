import logging
from pathlib import Path
from typing import Dict, Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class TranscriptionService:
    def __init__(self, jobs_dir: str, model_size: str = "small"):
        self.jobs_dir = Path(jobs_dir)
        self.model_size = model_size
        self._model = None

    def _get_model(self) -> WhisperModel:
        # Carga perezosa: el modelo (y su descarga la primera vez) solo se paga
        # cuando alguien pide transcribir, no en el arranque del servidor.
        if self._model is None:
            logger.info(f"Cargando modelo Whisper '{self.model_size}' (CPU, int8)...")
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, job_id: str, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe un stem de audio ya separado (normalmente 'vocals') y escribe
        transcript.srt + transcript.txt junto al resto de los archivos del job.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"No se encontró el audio a transcribir: {audio_path}")

        model = self._get_model()
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            # En música (voces cantadas, coros repetidos) alimentar el texto previo como
            # contexto hace que Whisper se "atasque" repitiendo la misma frase en loop.
            # Transcribir cada tramo de forma independiente evita ese bucle.
            condition_on_previous_text=False,
        )

        job_path = self.jobs_dir / job_id
        job_path.mkdir(parents=True, exist_ok=True)
        srt_path = job_path / "transcript.srt"
        txt_path = job_path / "transcript.txt"

        srt_blocks = []
        txt_lines = []
        idx = 1
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            txt_lines.append(text)
            srt_blocks.append(
                f"{idx}\n{_srt_timestamp(seg.start)} --> {_srt_timestamp(seg.end)}\n{text}\n"
            )
            idx += 1

        srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
        txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

        return {
            "language": info.language,
            "srt": srt_path.name,
            "txt": txt_path.name,
        }
