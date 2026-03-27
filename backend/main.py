import os
import shutil
import uuid
import time
from typing import Dict
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.services.separator import separate_audio
from backend.services.mixer import apply_custom_mix

app = FastAPI(title="Parrot Audio Separator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("frontend", exist_ok=True)

def cleanup_old_files():
    """Limpia archivos y carpetas temporales que tengan más de 1 hora de antigüedad en uploads/ y outputs/"""
    now = time.time()
    for directory in ["uploads", "outputs"]:
        if not os.path.exists(directory): continue
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            try:
                if os.path.getmtime(path) < now - 3600:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            except Exception:
                pass

jobs: Dict[str, dict] = {}

class MixRequest(BaseModel):
    vocals: float = 1.0
    drums: float = 1.0
    bass: float = 1.0
    other: float = 1.0
    piano: float = 1.0
    guitar: float = 1.0

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Programar auto-limpieza en cada llamada al endpoint
    background_tasks.add_task(cleanup_old_files)
    
    job_id = str(uuid.uuid4())
    file_path = f"uploads/{job_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    jobs[job_id] = {"status": "processing", "file": file_path, "result": None}
    
    def process_task():
        try:
            output_dir = separate_audio(file_path, job_id)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = output_dir
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

    background_tasks.add_task(process_task)
    return {"job_id": job_id, "status": "processing"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.post("/mix/{job_id}")
async def mix_audio(job_id: str, mix: MixRequest):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not ready or not found")
    
    stem_dir = jobs[job_id]["result"]
    original_file = jobs[job_id]["file"]
    
    try:
        mixed_file = apply_custom_mix(job_id, stem_dir, original_file, mix.model_dump())
        return {"status": "success", "file": mixed_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
