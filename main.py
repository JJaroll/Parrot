import os
import shutil
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.separator import AudioSeparatorService
from services.mixer import AudioMixerService
from services.transcriber import TranscriptionService

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Parrot API - Audio Separation", version="1.0")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "workspace" / "uploads"
JOBS_DIR = BASE_DIR / "workspace" / "jobs"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Try to mount static files if structure exists
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Mock In-Memory Job DB
JOBS_DB = {}
separator_service = AudioSeparatorService(jobs_dir=str(JOBS_DIR))
mixer_service = AudioMixerService(jobs_dir=str(JOBS_DIR), uploads_dir=str(UPLOAD_DIR))
transcriber_service = TranscriptionService(jobs_dir=str(JOBS_DIR), model_size="small")

# Expose workspace for file downloading
app.mount("/workspace", StaticFiles(directory="workspace"), name="workspace")

# Models
class StemConfig(BaseModel):
    volume: float = 1.0
    pan: float = 0.0  # -1.0 (izquierda) .. 1.0 (derecha)
    noise_gate: bool = False
    highpass_freq: float = 0.0
    bass_gain: float = 0.0
    mid_gain: float = 0.0
    treble_gain: float = 0.0

class MergeRequest(BaseModel):
    vocals: StemConfig = StemConfig()
    drums: StemConfig = StemConfig()
    bass: StemConfig = StemConfig()
    piano: StemConfig = StemConfig()
    guitar: StemConfig = StemConfig()
    other: StemConfig = StemConfig()
    normalize: bool = False
    output_format: str = "wav_44100"

def process_separation_work(job_id: str, file_path: Path):
    try:
        current_job = JOBS_DB.get(job_id, {})
        current_job["status"] = "processing"
        JOBS_DB[job_id] = current_job
        
        result = separator_service.process_job(job_id, file_path)
        
        current_job.update(result)
        JOBS_DB[job_id] = current_job
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        current_job = JOBS_DB.get(job_id, {})
        current_job.update({"status": "failed", "error": str(e)})
        JOBS_DB[job_id] = current_job

def process_transcription_work(job_id: str, stem: str):
    try:
        job = JOBS_DB.get(job_id, {})
        job["transcription"] = {"status": "processing", "stem": stem}
        JOBS_DB[job_id] = job

        stem_path = Path(job["stems"][stem])
        result = transcriber_service.transcribe(job_id, stem_path)

        job = JOBS_DB.get(job_id, {})
        job["transcription"] = {"status": "completed", "stem": stem, **result}
        JOBS_DB[job_id] = job
    except Exception as e:
        logger.error(f"Transcription failed for job {job_id}: {e}")
        job = JOBS_DB.get(job_id, {})
        job["transcription"] = {"status": "failed", "stem": stem, "error": str(e)}
        JOBS_DB[job_id] = job

@app.get("/", response_class=FileResponse)
async def serve_ui():
    """Serves the Parrot Frontend Dashboard."""
    return FileResponse(BASE_DIR / "frontend" / "index.html")

@app.post("/api/v1/separate")
async def start_separation(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Ingest endpoint: uploads file and queues separation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    job_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    
    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    # Queue processing
    JOBS_DB[job_id] = {"status": "queued", "original_file": str(file_path)}
    background_tasks.add_task(process_separation_work, job_id, file_path)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/v1/status/{job_id}")
async def get_status(job_id: str):
    """Returns the current status of the separation job."""
    job = JOBS_DB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/v1/transcribe/{job_id}")
async def start_transcription(job_id: str, background_tasks: BackgroundTasks, stem: str = "vocals"):
    """Transcribe un stem ya separado (por defecto 'vocals') con Whisper local, generando .srt y .txt."""
    job = JOBS_DB.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job no está listo (separación no completada)")

    stems = job.get("stems", {})
    if stem not in stems:
        raise HTTPException(status_code=400, detail=f"Stem inválido: {stem}")

    job["transcription"] = {"status": "queued", "stem": stem}
    JOBS_DB[job_id] = job
    background_tasks.add_task(process_transcription_work, job_id, stem)

    return {"status": "queued", "stem": stem}

def _dir_size(path: Path) -> int:
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total

def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

@app.post("/api/v1/cleanup")
async def cleanup_workspace():
    """Borra todo lo generado (uploads originales + stems separados + mixes + transcripciones) para liberar espacio."""
    freed_bytes = _dir_size(JOBS_DIR) + _dir_size(UPLOAD_DIR)

    for directory in (JOBS_DIR, UPLOAD_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    JOBS_DB.clear()

    return {"freed_bytes": freed_bytes, "freed_human": _format_size(freed_bytes)}

@app.get("/api/v1/trim/{job_id}")
async def trim_stem(job_id: str, background_tasks: BackgroundTasks, start: float, end: float, stem: str = "vocals"):
    """Descarga solo el fragmento [start, end] (segundos) de un stem ya separado, sin fusionar nada."""
    job = JOBS_DB.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job no está listo (separación no completada)")

    stems = job.get("stems", {})
    if stem not in stems:
        raise HTTPException(status_code=400, detail=f"Stem inválido: {stem}")
    if end <= start or start < 0:
        raise HTTPException(status_code=400, detail="Rango de tiempo inválido")

    try:
        out_path = mixer_service.trim_stem(Path(stems[stem]), start, end)
    except Exception as e:
        logger.error(f"Trim error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(os.remove, out_path)
    filename = f"{stem}_{start:.1f}s-{end:.1f}s.wav"
    return FileResponse(out_path, media_type="audio/wav", filename=filename)

@app.post("/api/v1/merge/{job_id}")
async def merge_stems(job_id: str, request: MergeRequest):
    """
    Lógica de Re-unión (Merge):
    Aplica post-producción (Gate, EQ, Normalización) y re-renderiza el output
    """
    job = JOBS_DB.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job no está listo para hacer merge")
        
    original_file = job.get("original_file")
    orig_path = Path(original_file) if original_file else None
    
    try:
        req_data = request.model_dump() # equivalent to .dict()
        output_path = mixer_service.merge_stems(job_id, req_data, original_file=orig_path)
        return {"message": "Merge completado", "output": str(output_path)}
    except Exception as e:
        logger.error(f"Merge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
