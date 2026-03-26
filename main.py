import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.separator import AudioSeparatorService

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

# Models
class MergeRequest(BaseModel):
    vocals: float = 1.0
    drums: float = 1.0
    bass: float = 1.0
    piano: float = 1.0
    guitar: float = 1.0
    other: float = 1.0

def process_separation_work(job_id: str, file_path: Path):
    try:
        JOBS_DB[job_id] = {"status": "processing"}
        result = separator_service.process_job(job_id, file_path)
        JOBS_DB[job_id] = result
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        JOBS_DB[job_id] = {"status": "failed", "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the basic HTML Interface for uploading files."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Parrot - Audio Separation</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 2rem; background: #121212; color: #fff;}
            .container { max-width: 600px; margin: 0 auto; background: #1e1e1e; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);}
            h1 { color: #1DB954; }
            input[type="file"] { margin: 1rem 0; color: #fff; }
            button { background: #1DB954; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: bold;}
            button:hover { background: #1ed760; }
            #status { margin-top: 1rem; color: #aaa; padding: 10px; border-radius: 4px; background: #2a2a2a; display: none;}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🦜 Parrot - 6 Stem Separation</h1>
            <p>Sube un archivo de audio o video (.mp3, .wav, .mp4, .mkv) para separar sus 6 pistas: Voces, Batería, Bajo, Piano, Guitarra y Otros.</p>
            <input type="file" id="fileInput" accept=".mp3,.wav,.mp4,.mkv">
            <button onclick="uploadFile()">Separar Audio</button>
            <div id="status"></div>
        </div>
        <script>
            async function uploadFile() {
                const fileInput = document.getElementById('fileInput').files[0];
                if (!fileInput) return alert('Por favor, selecciona un archivo primero.');
                
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.innerText = "Subiendo archivo...";
                
                const formData = new FormData();
                formData.append('file', fileInput);
                
                try {
                    const response = await fetch('/api/v1/separate', { method: 'POST', body: formData });
                    const data = await response.json();
                    
                    if (data.job_id) {
                        statusDiv.innerText = `Procesando (Job ID: ${data.job_id})... Esto puede tardar varios minutos dependiendo del hardware.`;
                        checkStatus(data.job_id);
                    } else {
                        statusDiv.innerText = "Error al iniciar el trabajo.";
                    }
                } catch (e) {
                    statusDiv.innerText = "Error conectando con el servidor.";
                }
            }
            
            async function checkStatus(jobId) {
                const statusDiv = document.getElementById('status');
                const interval = setInterval(async () => {
                    const res = await fetch(`/api/v1/status/${jobId}`);
                    const data = await res.json();
                    if (data.status === 'completed') {
                        statusDiv.innerHTML = `<span style="color: #1DB954; font-weight: bold;">¡Separación Exitosa!</span><br/>Las pistas están listas en la carpeta del servidor: <code>workspace/jobs/${jobId}/separated</code>`;
                        clearInterval(interval);
                    } else if (data.status === 'failed') {
                        statusDiv.innerHTML = `<span style="color: #e74c3c;">Error:</span> ${data.error}`;
                        clearInterval(interval);
                    } else {
                        statusDiv.innerText = `Separando audio mediante IA... (Estado: ${data.status})`;
                    }
                }, 3000);
            }
        </script>
    </body>
    </html>
    """
    return html_content

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
    JOBS_DB[job_id] = {"status": "queued"}
    background_tasks.add_task(process_separation_work, job_id, file_path)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/v1/status/{job_id}")
async def get_status(job_id: str):
    """Returns the current status of the separation job."""
    job = JOBS_DB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/v1/merge/{job_id}")
async def merge_stems(job_id: str, request: MergeRequest):
    """
    Lógica de Re-unión (Merge):
    Recibe niveles de volumen (0.0 a 1.0) para cada pista y genera mix principal o video.
    """
    job = JOBS_DB.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job no está listo para hacer merge")
        
    # TODO: Implementar usando ffmpeg.filter de la librería ffmpeg-python
    # amix filter o complex_filter ajustando volúmenes según request.dict()
    
    return {"message": "Endpoint de Merge listo para implementación FFmpeg", "levels": request.dict()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
