"""
Servicio de mezcla y manipulación de streams de audio y video utilizando FFmpeg.
Permite ajustar volumen, pan estéreo, filtros ecualizadores, puertas de ruido y exportar en múltiples formatos.
"""

import os
import logging
import tempfile
import ffmpeg
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

FORMAT_PRESETS = {
    "wav_44100": {"ext": ".wav", "acodec": "pcm_s16le", "ar": 44100},
    "wav_48000": {"ext": ".wav", "acodec": "pcm_s16le", "ar": 48000},
    "mp3_320":   {"ext": ".mp3", "acodec": "libmp3lame", "ar": 44100, "audio_bitrate": "320k"},
    "mp3_192":   {"ext": ".mp3", "acodec": "libmp3lame", "ar": 44100, "audio_bitrate": "192k"},
}

class AudioMixerService:
    def __init__(self, jobs_dir: str, uploads_dir: str):
        self.jobs_dir = Path(jobs_dir)
        self.uploads_dir = Path(uploads_dir)

    def merge_stems(self, job_id: str, request_data: Dict[str, Any], original_file: Optional[Path] = None) -> Path:
        job_path = self.jobs_dir / job_id
        stems_dir = job_path / "separated"

        if not stems_dir.exists():
            raise FileNotFoundError(f"Stems not found for job {job_id}")

        export_mode = request_data.get("export_mode", "mix")

        if export_mode == "video":
            if not (original_file and original_file.exists()):
                raise ValueError("No hay video original para exportar 'solo video'.")
            out_filepath = job_path / f"video_only{original_file.suffix}"
            try:
                vid_stream = ffmpeg.input(str(original_file)).video
                out = ffmpeg.output(vid_stream, str(out_filepath), vcodec='copy', an=None)
                out = out.overwrite_output()
                out.run(capture_stdout=True, capture_stderr=True)
                return out_filepath
            except ffmpeg.Error as e:
                err_log = e.stderr.decode('utf8') if e.stderr else str(e)
                logger.error(f"FFmpeg error: {err_log}")
                raise RuntimeError(f"FFmpeg video-only export failed: {err_log}")

        stems = ["vocals", "drums", "bass", "piano", "guitar", "other"]
        inputs = []
        audio_streams = []

        format_key = request_data.get("output_format", "wav_44100")
        preset = FORMAT_PRESETS.get(format_key, FORMAT_PRESETS["wav_44100"])

        has_video = False
        out_ext = preset["ext"]
        if export_mode != "audio" and original_file and original_file.exists():
            try:
                probe = ffmpeg.probe(str(original_file))
                if any(stream['codec_type'] == 'video' for stream in probe['streams']):
                    has_video = True
                    out_ext = original_file.suffix
            except Exception as e:
                logger.warning(f"Failed to probe original file: {e}")

        out_filename = f"mixed{out_ext}"
        out_filepath = job_path / out_filename

        for stem in stems:
            stem_file = stems_dir / f"{stem}.wav"
            if not stem_file.exists():
                logger.warning(f"Stem {stem} missing, skipping.")
                continue
                
            stream = ffmpeg.input(str(stem_file))
            inputs.append(stream)
            
            stem_config = request_data.get(stem, {})
            if isinstance(stem_config, dict):
                vol = stem_config.get("volume", 1.0)
                pan = stem_config.get("pan", 0.0)
                noise_gate = stem_config.get("noise_gate", False)
                highpass_freq = stem_config.get("highpass_freq", 0.0)
                bass_gain = stem_config.get("bass_gain", 0.0)
                mid_gain = stem_config.get("mid_gain", 0.0)
                treble_gain = stem_config.get("treble_gain", 0.0)
            else:
                vol = getattr(stem_config, "volume", 1.0)
                pan = getattr(stem_config, "pan", 0.0)
                noise_gate = getattr(stem_config, "noise_gate", False)
                highpass_freq = getattr(stem_config, "highpass_freq", 0.0)
                bass_gain = getattr(stem_config, "bass_gain", 0.0)
                mid_gain = getattr(stem_config, "mid_gain", 0.0)
                treble_gain = getattr(stem_config, "treble_gain", 0.0)

            a_stream = stream.audio

            if highpass_freq and highpass_freq > 0:
                a_stream = a_stream.filter('highpass', f=highpass_freq)

            if vol != 1.0:
                a_stream = a_stream.filter('volume', vol)

            if noise_gate:
                a_stream = a_stream.filter('agate', threshold=0.04, ratio=2, attack=20, release=250)
                
            if bass_gain != 0.0:
                a_stream = a_stream.filter('bass', g=bass_gain)
            if mid_gain != 0.0:
                a_stream = a_stream.filter('equalizer', f=1000, width_type='h', w=200, g=mid_gain)
            if treble_gain != 0.0:
                a_stream = a_stream.filter('treble', g=treble_gain)

            if pan and pan != 0.0:
                a_stream = a_stream.filter('stereotools', balance_out=pan)

            audio_streams.append(a_stream)
            
        if not audio_streams:
            raise ValueError("No stems found to merge.")

        mixed_audio = ffmpeg.filter(audio_streams, 'amix', inputs=len(audio_streams), normalize=False)
        
        if request_data.get("normalize", False):
            mixed_audio = mixed_audio.filter('loudnorm')
            
        output_kwargs = {"acodec": preset["acodec"], "ar": preset["ar"], "threads": 0}
        if "audio_bitrate" in preset:
            output_kwargs["audio_bitrate"] = preset["audio_bitrate"]

        try:
            if has_video:
                vid_stream = ffmpeg.input(str(original_file)).video
                out = ffmpeg.output(mixed_audio, vid_stream, str(out_filepath), vcodec='copy', **output_kwargs)
            else:
                out = ffmpeg.output(mixed_audio, str(out_filepath), **output_kwargs)

            out = out.overwrite_output()
            out.run(capture_stdout=True, capture_stderr=True)
            return out_filepath
            
        except ffmpeg.Error as e:
            err_log = e.stderr.decode('utf8') if e.stderr else str(e)
            logger.error(f"FFmpeg error: {err_log}")
            raise RuntimeError(f"FFmpeg merging failed: {err_log}")

    def trim_stem(self, stem_path: Path, start: float, end: float) -> Path:
        if not stem_path.exists():
            raise FileNotFoundError(f"Stem no encontrado: {stem_path}")
        if end <= start or start < 0:
            raise ValueError("Rango de recorte inválido")

        fd, tmp_name = tempfile.mkstemp(suffix=".wav", prefix="parrot_trim_")
        os.close(fd)
        out_path = Path(tmp_name)

        try:
            (
                ffmpeg
                .input(str(stem_path), ss=start, to=end)
                .output(str(out_path), acodec='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return out_path
        except ffmpeg.Error as e:
            err_log = e.stderr.decode('utf8') if e.stderr else str(e)
            logger.error(f"FFmpeg trim error: {err_log}")
            raise RuntimeError(f"FFmpeg trim failed: {err_log}")
