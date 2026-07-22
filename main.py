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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Parrot API - Audio Separation", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DATA_DIR = Path.cwd()
UPLOAD_DIR = DATA_DIR / "workspace" / "uploads"
JOBS_DIR = DATA_DIR / "workspace" / "jobs"
WORKSPACE_DIR = DATA_DIR / "workspace"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mock In-Memory Job DB
JOBS_DB = {}
separator_service = AudioSeparatorService(jobs_dir=str(JOBS_DIR))
mixer_service = AudioMixerService(jobs_dir=str(JOBS_DIR), uploads_dir=str(UPLOAD_DIR))
transcriber_service = TranscriptionService(jobs_dir=str(JOBS_DIR), model_size="small")

app.mount("/workspace", StaticFiles(directory=str(WORKSPACE_DIR)), name="workspace")

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
    export_mode: str = "mix"  # "mix" (audio+video), "audio" (solo audio), "video" (solo video, sin audio)

def process_separation_work(job_id: str, file_path: Path):
    try:
        current_job = JOBS_DB.get(job_id, {})
        current_job["status"] = "processing"
        current_job["progress"] = 0
        JOBS_DB[job_id] = current_job

        def on_progress(pct: int):
            job = JOBS_DB.get(job_id, {})
            job["progress"] = pct
            JOBS_DB[job_id] = job

        result = separator_service.process_job(job_id, file_path, on_progress=on_progress)

        current_job = JOBS_DB.get(job_id, {})
        current_job.update(result)
        current_job["progress"] = 100
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
    return FileResponse(BASE_DIR / "frontend" / "index.html")

@app.get("/api/v1/system-info")
async def system_info():
    return {"device": AudioSeparatorService.get_device()}

@app.post("/api/v1/separate")
async def start_separation(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    job_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    
    file_path = UPLOAD_DIR / f"{job_id}{file_ext}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    JOBS_DB[job_id] = {"status": "queued", "original_file": str(file_path)}
    background_tasks.add_task(process_separation_work, job_id, file_path)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/v1/status/{job_id}")
async def get_status(job_id: str):
    job = JOBS_DB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/v1/transcribe/{job_id}")
async def start_transcription(job_id: str, background_tasks: BackgroundTasks, stem: str = "vocals"):
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
    #Borra todo lo generado (uploads originales + stems separados + mixes + transcripciones) para liberar espacio.
    freed_bytes = _dir_size(JOBS_DIR) + _dir_size(UPLOAD_DIR)

    for directory in (JOBS_DIR, UPLOAD_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    JOBS_DB.clear()

    return {"freed_bytes": freed_bytes, "freed_human": _format_size(freed_bytes)}

@app.get("/api/v1/trim/{job_id}")
async def trim_stem(job_id: str, background_tasks: BackgroundTasks, start: float, end: float, stem: str = "vocals"):
    #Descarga solo el fragmento [start, end] (segundos) de un stem ya separado, sin fusionar nada.
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
    job = JOBS_DB.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job no está listo para hacer merge")
        
    original_file = job.get("original_file")
    orig_path = Path(original_file) if original_file else None
    
    try:
        req_data = request.model_dump()
        output_path = mixer_service.merge_stems(job_id, req_data, original_file=orig_path)
        return {"message": "Merge completado", "output": str(output_path)}
    except Exception as e:
        logger.error(f"Merge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import threading
    import uvicorn
    import webbrowser
    from tray_icon import run_tray_icon
    from hosts_setup import ensure_local_hostname, HOSTNAME

    HOST = "127.0.0.1"
    PORT = 8001
    APP_URL = f"http://{HOSTNAME}:{PORT}" if ensure_local_hostname() else f"http://{HOST}:{PORT}"

    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT))
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    def _quit_app():
        os._exit(0)

    threading.Timer(1.0, lambda: webbrowser.open(APP_URL)).start()

    if not run_tray_icon(APP_URL, on_quit=_quit_app):
        server_thread.join()
