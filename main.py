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
from services.mixer import AudioMixerService

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

# Expose workspace for file downloading
app.mount("/workspace", StaticFiles(directory="workspace"), name="workspace")

# Models
class StemConfig(BaseModel):
    volume: float = 1.0
    noise_gate: bool = False
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

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the basic HTML Interface for uploading files."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Parrot - Audio Post-Production</title>
        <script src="https://unpkg.com/wavesurfer.js@7"></script>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 2rem; background: #121212; color: #fff;}
            .container { max-width: 800px; margin: 0 auto; background: #1e1e1e; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);}
            h1 { color: #1DB954; }
            h2 { color: #1DB954; font-size: 1.2rem; margin-top: 1.5rem; border-bottom: 1px solid #333; padding-bottom: 0.5rem;}
            input[type="file"] { margin: 1rem 0; color: #fff; }
            button { background: #1DB954; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 10px;}
            button:hover { background: #1ed760; }
            .stem-control { background: #2a2a2a; margin-bottom: 15px; padding: 15px; border-radius: 6px; border-left: 4px solid #1DB954; }
            .fader-row { display: flex; align-items: center; justify-content: space-between; }
            .fader-row label { font-weight: bold; width: 100px; }
            input[type=range] { flex-grow: 1; margin: 0 15px; accent-color: #1DB954; }
            .adv-options { display: none; margin-top: 15px; padding-top: 15px; border-top: 1px dashed #444; }
            .adv-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; font-size: 0.9em; }
            .adv-row label { display: flex; align-items: center; gap: 8px;}
            .master-control { margin-top: 20px; padding: 15px; background: #222; border-radius: 6px; border: 1px solid #1DB954; }
            #status { margin-top: 1rem; color: #aaa; padding: 10px; border-radius: 4px; background: #2a2a2a; display: none;}
            #waveform { margin-top: 20px; background: #1a1a1a; border-radius: 4px; padding: 10px; display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🦜 Parrot - Advanced Audio</h1>
            <p>Sube un archivo (.mp3, .wav, .mp4, .mkv, .mov) para separar sus 6 pistas y aplicar post-producción con WaveSurfer.js</p>
            <input type="file" id="fileInput" accept=".mp3,.wav,.mp4,.mkv,.mov">
            <button onclick="uploadFile()">1. Separar Audio</button>
            <div id="status"></div>
            
            <div id="mixer-section" style="display:none; margin-top: 2rem;">
                <h2>Mezclador & Post-Producción</h2>
                <div id="stems-container"></div>
                
                <div class="master-control">
                    <h3>Master Buss</h3>
                    <label><input type="checkbox" id="master_normalize"> Normalizar (Loudnorm)</label>
                    <br>
                    <button onclick="mixAudio()" style="width: 100%; margin-top: 15px;">2. Mix & Render</button>
                </div>
                
                <div id="waveform"></div>
                <div id="download-section" style="display:none; margin-top: 1rem;">
                    <a id="download-link" href="#" target="_blank" style="color: #1DB954; text-decoration: none; font-weight: bold;">🔊 Escuchar / Descargar Mix Final</a>
                </div>
            </div>
        </div>
        
        <script>
            let currentJobId = null;
            let wavesurfer = null;
            let finalFileName = null;
            const stems = ["vocals", "drums", "bass", "piano", "guitar", "other"];

            function buildMixerUI() {
                const container = document.getElementById('stems-container');
                stems.forEach(stem => {
                    const html = `
                    <div class="stem-control">
                        <div class="fader-row">
                            <label style="text-transform: capitalize;">${stem}</label>
                            <input type="range" id="vol_${stem}" min="0" max="2" step="0.1" value="1.0">
                            <span id="vol_val_${stem}">1.0</span>
                            <button onclick="toggleAdv('${stem}')" style="background: #444; margin-left:10px; padding: 4px 8px; font-size: 0.8em;">Modo Avanzado</button>
                        </div>
                        <div class="adv-options" id="adv_${stem}">
                            <div class="adv-row">
                                <label><input type="checkbox" id="gate_${stem}"> 🔌 Noise Gate (Eliminar ruido)</label>
                            </div>
                            <div class="adv-row">
                                <label>Bass <input type="range" id="bass_${stem}" min="-20" max="20" value="0" step="1"></label>
                                <label>Mid <input type="range" id="mid_${stem}" min="-20" max="20" value="0" step="1"></label>
                                <label>Treble <input type="range" id="treble_${stem}" min="-20" max="20" value="0" step="1"></label>
                            </div>
                        </div>
                    </div>
                    `;
                    container.innerHTML += html;
                });
                
                stems.forEach(stem => {
                    document.getElementById(`vol_${stem}`).addEventListener('input', (e) => {
                        document.getElementById(`vol_val_${stem}`).innerText = parseFloat(e.target.value).toFixed(1);
                    });
                });
            }
            
            buildMixerUI();

            function toggleAdv(stem) {
                const el = document.getElementById(`adv_${stem}`);
                el.style.display = el.style.display === 'none' || el.style.display === '' ? 'block' : 'none';
            }

            async function uploadFile() {
                const fileInput = document.getElementById('fileInput').files[0];
                if (!fileInput) return alert('Por favor, selecciona un archivo primero.');
                
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.innerText = "Subiendo archivo...";
                document.getElementById('mixer-section').style.display = 'none';
                document.getElementById('waveform').style.display = 'none';
                document.getElementById('download-section').style.display = 'none';
                
                const formData = new FormData();
                formData.append('file', fileInput);
                
                try {
                    const response = await fetch('/api/v1/separate', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (data.job_id) {
                        currentJobId = data.job_id;
                        statusDiv.innerText = `Procesando (Job ID: ${currentJobId})... Esto puede tardar varios minutos dependiendo del hardware.`;
                        checkStatus(currentJobId);
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
                        statusDiv.innerHTML = `<span style="color: #1DB954; font-weight: bold;">¡Separación Exitosa!</span> Pistas listas. Ahora puedes mezclarlas.`;
                        document.getElementById('mixer-section').style.display = 'block';
                        clearInterval(interval);
                    } else if (data.status === 'failed') {
                        statusDiv.innerHTML = `<span style="color: #e74c3c;">Error:</span> ${data.error}`;
                        clearInterval(interval);
                    } else {
                        statusDiv.innerText = `Separando audio mediante IA... (Estado: ${data.status})`;
                    }
                }, 3000);
            }

            async function mixAudio() {
                if (!currentJobId) return alert('No hay job activo.');
                
                const payload = { normalize: document.getElementById('master_normalize').checked };
                stems.forEach(stem => {
                    payload[stem] = {
                        volume: parseFloat(document.getElementById(`vol_${stem}`).value),
                        noise_gate: document.getElementById(`gate_${stem}`).checked,
                        bass_gain: parseFloat(document.getElementById(`bass_${stem}`).value),
                        mid_gain: parseFloat(document.getElementById(`mid_${stem}`).value),
                        treble_gain: parseFloat(document.getElementById(`treble_${stem}`).value),
                    };
                });

                const btn = event.target;
                const oldText = btn.innerText;
                btn.innerText = "Procesando Mix...";
                btn.disabled = true;

                try {
                    const res = await fetch(`/api/v1/merge/${currentJobId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const data = await res.json();
                    
                    if (res.ok) {
                        const pathParts = data.output.split('/');
                        finalFileName = pathParts[pathParts.length - 1];
                        const urlPath = `/workspace/jobs/${currentJobId}/${finalFileName}`;
                        
                        document.getElementById('download-section').style.display = 'block';
                        const a = document.getElementById('download-link');
                        a.href = urlPath;
                        a.innerText = `🔊 Escuchar / Descargar ${finalFileName}`;
                        
                        // Load waveform
                        const wfDiv = document.getElementById('waveform');
                        wfDiv.style.display = 'block';
                        wfDiv.innerHTML = '';
                        
                        if (wavesurfer && wavesurfer.destroy) wavesurfer.destroy();
                        
                        wavesurfer = WaveSurfer.create({
                            container: '#waveform',
                            waveColor: '#1DB954',
                            progressColor: '#1ed760',
                            barWidth: 2,
                            height: 100,
                            url: urlPath,
                            mediaControls: true
                        });
                        
                        wavesurfer.on('interaction', () => wavesurfer.play());
                        
                    } else {
                        alert("Error: " + data.detail);
                    }
                } catch(e) {
                    alert("Error mixing audio");
                } finally {
                    btn.innerText = oldText;
                    btn.disabled = false;
                }
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
