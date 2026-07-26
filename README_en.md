# 🦜 Parrot (AI Audio Separation API & Dashboard)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Version](https://img.shields.io/badge/Version-0.1.3-blue)

*[Español](README.md) | 🌍 **English** | [日本語](README_ja.md)*

**Parrot** is a powerful local API and Dashboard for AI-driven audio separation and post-production. Designed to isolate individual tracks (*stems*) from songs or audio files using Demucs v4, transcribe isolated vocals with Whisper AI, and merge them back with full post-production controls such as 3-band EQ, Noise Gate, and Panning.

Ideal for music producers, musicians, content creators, and developers who need to manipulate audio programmatically or through a sleek, modern web dashboard.

## ✨ Key Features

* **🌍 Multi-Language Support:**
    * Interface and documentation available in English, Spanish, and Japanese.
* **🎛️ Advanced Audio Separation (Demucs v4):**
    * Extracts up to 6 individual stems: **Vocals, Drums, Bass, Piano, Guitar, and Other**.
* **🗣️ Smart Transcription (Whisper AI):**
    * Transcribes isolated vocals, automatically generating subtitle `.srt` files and plain text `.txt` transcripts.
* **🎧 Mixer & Post-Production (Merge):**
    * Recombines stems with 3-band Equalization (Low, Mid, High), individual track volume control, Panning, Noise Gate, and final audio Normalization.
* **✂️ Fast Editing (Trim):**
    * Extracts specific fragments from any stem in seconds using precise timestamps.
* **🧹 Workspace Management:**
    * Dedicated endpoint and tools to clean up working directories and remove temporary files efficiently.
* **⚡ Smart Hardware Acceleration:**
    * Auto-detects NVIDIA GPUs (CUDA), Apple Silicon (MPS), or CPU, featuring an interactive installer to select the optimal engine.
* **🖥️ Built-in Smart Launcher:**
    * Native installer featuring live progress tracking, automatic dependency management, and static `ffmpeg` binaries.

---

## 📥 Downloads & Installation (Binaries)

Parrot is available natively for Windows, macOS, and Linux! You can download the pre-compiled version ready to use (no manual Python setup required):

### 🍎 macOS
* **Application / Installer:** Download the pre-compiled version from the [Releases](https://github.com/JJaroll/Parrot/releases) section.
  > **⚠️ Note for macOS Users (Gatekeeper):**
  > As an open-source app without Apple Developer ID signing, macOS may block initial execution for security. If blocked, navigate to **System Settings > Privacy & Security**, scroll down to Security, and click **"Open Anyway"**. If you see a message stating the app "is damaged", open Terminal and run:
  > ```bash
  > xattr -cr /path/to/Parrot.app
  > ```

### 🪟 Windows
* **Executable Installer (.exe):** Download `Parrot_Setup_Windows.exe` from [Releases](https://github.com/JJaroll/Parrot/releases).
  > **Installation:** Run the setup wizard. If a compatible NVIDIA GPU is detected, you will be prompted to choose between CUDA-accelerated or CPU mode.

### 🐧 Linux
* **Universal Executable (.AppImage):** Download `Parrot_Linux.AppImage` from [Releases](https://github.com/JJaroll/Parrot/releases).
  > **Installation:** Grant execution permissions to the file (`chmod +x Parrot_Linux.AppImage`) and run it directly.

---

## 🛠️ Build from Source Code

If you are a developer and prefer to run or modify the source code directly:

### Prerequisites
* Python 3.10 or higher.
* `ffmpeg` / `ffprobe` installed on the system (automatically downloaded by the launcher to `~/.parrot_studio/bin` if missing).

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/JJaroll/Parrot.git
   cd Parrot
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

Run the main server or the launcher:

```bash
python main.py
```
*(Or run `python launcher.py` to use the interactive startup assistant).*

The server will launch at `http://localhost:8001`.

* **Web Dashboard:** Open your browser and navigate to `http://localhost:8001/` to access the interactive user interface.
* **API Documentation (Swagger / OpenAPI):** Go to `http://localhost:8001/docs` to explore and test all interactive REST endpoints.

---

## 📡 Main Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/separate` | `POST` | Uploads an audio/video file and queues it for stem separation. |
| `/api/v1/status/{job_id}` | `GET` | Queries real-time processing status and job progress. |
| `/api/v1/transcribe/{job_id}` | `POST` | Starts AI transcription (Whisper) on isolated vocals (`.srt` / `.txt`). |
| `/api/v1/trim/{job_id}` | `GET` | Trims a specific time fragment `[start, end]` from an individual stem. |
| `/api/v1/merge/{job_id}` | `POST` | Merges selected stems applying post-production (EQ, Panning, Normalization). |
| `/api/v1/cleanup` | `POST` | Cleans up temporary working directories and frees disk space. |
| `/api/v1/system-info` | `GET` | Displays detected hardware acceleration engine (`cuda`, `mps`, or `cpu`). |

---

## 📁 Project Structure

| File / Directory | Responsibility |
|---|---|
| `main.py` | Main entry point. FastAPI application, REST endpoints, and static frontend routes. |
| `launcher.py` | Interactive GUI/CLI Smart Launcher that setups venv, dependencies, and environment. |
| `services/separator.py` | Demucs v4-based audio separation engine (6 stems). |
| `services/mixer.py` | Post-production, re-mixing (*merge*), trimming (*trim*), and EQ engine. |
| `services/transcriber.py` | Automatic transcription service powered by Whisper AI. |
| `frontend/` | Interactive web dashboard (HTML5/CSS3/JavaScript). |
| `workspace/` | Local temporary storage for original audio files and processed output. |
| `parrot_installer.iss` | Windows native installer build script (Inno Setup). |

---

## 🔒 Privacy & Security

**Your data stays on your machine.**

Parrot is a 100% local application. Unlike cloud-based audio processing services:
* **Local Processing:** AI models (Demucs & Whisper) run entirely on your local hardware.
* **No Telemetry:** No personal data, telemetry, or audio files are collected or sent to external servers.
* **Absolute Privacy:** Your audio recordings, music tracks, and transcripts never leave your device.

---

## 🤝 Contributing

Contributions are welcome!

1. **Fork** the project.
2. Create a branch (`git checkout -b feature/NewFeature`).
3. Commit your changes.
4. Push to your branch (`git push origin feature/NewFeature`).
5. Open a **Pull Request**.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
*📝 Check the [Terms and Conditions](TERMS.md) and [Third-Party Licenses](THIRD_PARTY_LICENSES.md).*

Made with ❤️ by **JJaroll**
