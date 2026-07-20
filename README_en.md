# 🦜 Parrot (Python + FastAPI)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green)

*[Español](README.md) | 🌍 **English** | [日本語](README_ja.md)*

**Parrot** is a powerful local API and Dashboard for audio separation and post-production. Designed to isolate stems from a song or audio file, transcribe them using Artificial Intelligence (Whisper), and merge them back with professional tweaks like EQ, Noise Gate, and Panning.

Ideal for music producers, musicians, content creators, and developers who need to manipulate audio programmatically.

## ✨ Key Features

* **🌍 Multi-Language Support:**
    *   Documentation available in English, Spanish, and Japanese.
* **🎛️ Advanced Audio Separation:**
    *   Extracts individual stems: Vocals, Drums, Bass, Piano, Guitar, and Other.
* **🗣️ Smart Transcription (Whisper):**
    *   Transcribes isolated vocals generating `.srt` and `.txt` files automatically, perfect for subtitles.
* **🎧 Mixer & Post-Production (Merge):**
    *   Reunite stems with total control: Volume, Panning, Noise Gate, Bass/Mid/Treble Gain, and Final Normalization.
* **✂️ Fast Editing (Trim):**
    *   Extract specific fragments of a stem in a matter of seconds.
* **🧹 Space Management:**
    *   Dedicated endpoint to efficiently clean up the workspace by removing residual files.

---

## 🛠️ Setup and Installation

Parrot includes a native **Smart Launcher** that fully automates the installation of heavy AI models and dependencies.

### Quick Installation (Users)
1. Go to the [Releases](../../releases) tab on GitHub and download the version for your OS.
2. Double-click the executable (`Parrot.exe`, `Parrot.app`, or `Parrot_Linux.AppImage`).
3. The Launcher will automatically install Python (if missing) and download all requirements on the first run.
4. That's it! Your browser will open the Parrot dashboard. Next time you open it, it will launch instantly.

### Manual Installation (Developers)
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/JJaroll/Parrot.git
    cd Parrot
    ```
2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Usage

Run the main server:

```bash
python main.py
```
The server will start at `http://0.0.0.0:8001`.

*   **Dashboard / UI:** Open your browser and go to `http://localhost:8001/` to access the interactive web interface.
*   **API Documentation (Swagger):** Go to `http://localhost:8001/docs` to test and view the endpoints.

## 📡 Main Endpoints

*   `POST /api/v1/separate`: Uploads an audio file and queues stem separation.
*   `GET /api/v1/status/{job_id}`: Checks the status of a separation job.
*   `POST /api/v1/transcribe/{job_id}`: Starts transcription (default is 'vocals') using Whisper.
*   `GET /api/v1/trim/{job_id}`: Trims a specific fragment from a stem [start, end].
*   `POST /api/v1/merge/{job_id}`: Merges stems with post-production features (EQ, Panning, Normalization).
*   `POST /api/v1/cleanup`: Cleans up working directories and frees up space.

## 📁 Project Structure

* **main.py:** Entry point. Defines the FastAPI application and connects with services.
* **frontend/:** Contains the code (HTML/JS/CSS) for the interactive dashboard.
* **services/:**
  * **separator.py:** Audio separation logic.
  * **mixer.py:** Trimming and re-mixing logic (post-production).
  * **transcriber.py:** Audio transcription system (Whisper).
* **workspace/:** Temporary directory storing original audio files and processed jobs.

## 🤝 Contributing

Contributions are welcome!

1.  **Fork** the project.
2.  Create a branch (`git checkout -b feature/NewFeature`).
3.  Commit your changes.
4.  Push the branch (`git push origin feature/NewFeature`).
5.  Open a **Pull Request**.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Made with ❤️ by **JJaroll**
