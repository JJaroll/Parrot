import os
import logging
import ffmpeg
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AudioMixerService:
    def __init__(self, jobs_dir: str, uploads_dir: str):
        self.jobs_dir = Path(jobs_dir)
        self.uploads_dir = Path(uploads_dir)

    def merge_stems(self, job_id: str, request_data: Dict[str, Any], original_file: Optional[Path] = None) -> Path:
        """
        Merge separated stems using advanced FFmpeg filters.
        applies volume, noise gate, 3-band EQ, and normalization.
        If original_file is a video, muxes the new audio with the original video (stream copy).
        Optimized for Mac M1 using -threads 0.
        """
        job_path = self.jobs_dir / job_id
        stems_dir = job_path / "separated"
        
        if not stems_dir.exists():
            raise FileNotFoundError(f"Stems not found for job {job_id}")
            
        stems = ["vocals", "drums", "bass", "piano", "guitar", "other"]
        inputs = []
        audio_streams = []
        
        # Determine output format and file
        has_video = False
        out_ext = ".wav"
        if original_file and original_file.exists():
            # Check if it has video
            try:
                probe = ffmpeg.probe(str(original_file))
                if any(stream['codec_type'] == 'video' for stream in probe['streams']):
                    has_video = True
                    out_ext = original_file.suffix # e.g. .mp4 or .mkv
            except Exception as e:
                logger.warning(f"Failed to probe original file: {e}")
        
        out_filename = f"mixed{out_ext}"
        out_filepath = job_path / out_filename

        for stem in stems:
            stem_file = stems_dir / f"{stem}.wav"
            if not stem_file.exists():
                logger.warning(f"Stem {stem} missing, skipping.")
                continue
                
            # Input stream
            stream = ffmpeg.input(str(stem_file))
            inputs.append(stream)
            
            # Retrieve stem config or default
            stem_config = request_data.get(stem, {})
            # Read configuration (using attribute dot notation if it's a Pydantic model parsed dict, or dict key)
            if isinstance(stem_config, dict):
                vol = stem_config.get("volume", 1.0)
                noise_gate = stem_config.get("noise_gate", False)
                highpass_freq = stem_config.get("highpass_freq", 0.0)
                bass_gain = stem_config.get("bass_gain", 0.0)
                mid_gain = stem_config.get("mid_gain", 0.0)
                treble_gain = stem_config.get("treble_gain", 0.0)
            else: # assume it has attributes if not a dict
                vol = getattr(stem_config, "volume", 1.0)
                noise_gate = getattr(stem_config, "noise_gate", False)
                highpass_freq = getattr(stem_config, "highpass_freq", 0.0)
                bass_gain = getattr(stem_config, "bass_gain", 0.0)
                mid_gain = getattr(stem_config, "mid_gain", 0.0)
                treble_gain = getattr(stem_config, "treble_gain", 0.0)

            # Apply filters serially
            a_stream = stream.audio

            # 0. High-pass filter: corta retumbe de viento / rumble de baja frecuencia
            # (grabaciones de campo en exteriores) antes del resto de la cadena.
            if highpass_freq and highpass_freq > 0:
                a_stream = a_stream.filter('highpass', f=highpass_freq)

            # 1. Volume
            if vol != 1.0:
                a_stream = a_stream.filter('volume', vol)

            # 2. Noise Gate (mostly for vocals)
            if noise_gate:
                # agate: basic noise gate filter
                a_stream = a_stream.filter('agate', threshold=0.04, ratio=2, attack=20, release=250)
                
            # 3. EQ: Bass, Mid (equalizer), Treble
            if bass_gain != 0.0:
                a_stream = a_stream.filter('bass', g=bass_gain)
            if mid_gain != 0.0:
                # Mid frequencies ~1000Hz, width ~200Hz
                a_stream = a_stream.filter('equalizer', f=1000, width_type='h', w=200, g=mid_gain)
            if treble_gain != 0.0:
                a_stream = a_stream.filter('treble', g=treble_gain)
                
            audio_streams.append(a_stream)
            
        if not audio_streams:
            raise ValueError("No stems found to merge.")

        # Mix all processed audio streams using amix
        mixed_audio = ffmpeg.filter(audio_streams, 'amix', inputs=len(audio_streams), normalize=False)
        
        # Apply Master Normalization if requested
        if request_data.get("normalize", False):
            mixed_audio = mixed_audio.filter('loudnorm')
            
        # Optional: mux with video if present
        try:
            if has_video:
                vid_stream = ffmpeg.input(str(original_file)).video
                out = ffmpeg.output(mixed_audio, vid_stream, str(out_filepath), vcodec='copy', audio_bitrate='320k', threads=0)
            else:
                out = ffmpeg.output(mixed_audio, str(out_filepath), audio_bitrate='320k', threads=0)
                
            out = out.overwrite_output()
            out.run(capture_stdout=True, capture_stderr=True)
            return out_filepath
            
        except ffmpeg.Error as e:
            err_log = e.stderr.decode('utf8') if e.stderr else str(e)
            logger.error(f"FFmpeg error: {err_log}")
            raise RuntimeError(f"FFmpeg merging failed: {err_log}")
