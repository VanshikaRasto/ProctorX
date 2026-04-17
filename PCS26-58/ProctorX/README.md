# ProctorX — Combined Setup & Run Guide

This README explains how to set up, install, and run the complete ProctorX project (backend + frontend) on Windows (PowerShell). Use the commands below from the repository root: `ProctorX`.

## Repository layout (important paths)
- `proctor-x-backend/` — FastAPI backend (Python)
  - `main.py` — application entrypoint
  - `requirements.txt` — Python dependencies
  - `data/` — runtime data (users, exams, logs, submissions, models, ...)
- `proctor-x-frontend/` — React frontend (npm)
  - `package.json` — frontend scripts and deps

## Prerequisites
- Windows 10/11
- PowerShell (instructions use PowerShell)
- Python 3.13 (the project targets >=3.13)
  - Recommended: install from https://www.python.org/
- Node.js 18+ and npm (for frontend)
  - Recommended: https://nodejs.org/
- (Optional, for AI features) GPU drivers and packages for OpenCV / ultralytics / mediapipe if you want enhanced proctoring.

## Backend setup (FastAPI)
1. Open PowerShell and change to the backend directory:

   cd .\proctor-x-backend

2. Create and activate a virtual environment (recommended):

   python -m venv .venv
   ; .\.venv\Scripts\Activate.ps1

   If PowerShell blocks script execution, run (as admin once):

   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

3. Install Python dependencies:

   pip install --upgrade pip
   pip install -r requirements.txt

   Note: The `requirements.txt` includes many optional and heavy packages (OpenCV, mediapipe, ultralytics, deepface). If you only need the API without AI features, you may install a smaller subset. But the provided file lists the tested packages.

4. Ensure data directories exist (the app creates them, but verify):

   Get-ChildItem -Path .\data -Recurse

5. Run the backend API (development mode):

   # Option A: use the included entrypoint (auto-reload)
   python main.py

   # Option B: run uvicorn directly
   .\.venv\Scripts\uvicorn.exe "main:app" --host 0.0.0.0 --port 8000 --reload

6. Confirm the API is running by visiting in a browser or using curl:

   http://localhost:8000/
   http://localhost:8000/docs  # FastAPI Swagger UI

7. Logs
- Application logs are written to `proctor-x-backend/data/logs/app.log` by default.

## Frontend setup (React)
1. Open a new PowerShell and change to the frontend directory:

   cd .\proctor-x-frontend

2. Install Node dependencies:

   npm install

3. Start the frontend development server:

   npm start

4. The frontend defaults to:

   http://localhost:3000

   The backend CORS allows `http://localhost:3000` by default.

## Running both together
- Start the backend first (port 8000), then start the frontend (port 3000).
- You can open two PowerShell windows/tabs and run the backend and frontend concurrently.

## Environment variables and configuration
- The project uses simple file-based storage in `proctor-x-backend/data/`.
- If you add real authentication or database configuration, store secrets in environment variables or a `.env` file and load them in code (the project currently supports `python-dotenv`).

## Optional: Install only minimal dependencies for API (faster)
If you do not need the AI proctoring features, you can create a smaller requirements file and install the essentials:

- fastapi
- uvicorn
- python-multipart
- pydantic

Example (PowerShell):

   pip install fastapi uvicorn python-multipart pydantic

Then run `python main.py`.

## AI / Computer-vision features (optional)
- The backend detects availability of OpenCV, YOLO (ultralytics), MediaPipe, cvzone, MTCNN and enables AI proctoring when present.
- To enable enhanced AI features, install packages from `requirements.txt` (see `ultralytics`, `opencv-python`, `mediapipe`, `cvzone`, `mtcnn`, `deepface`). Installing those may require more system resources and platform-specific wheels (GPU drivers optional).

## Troubleshooting
- Permission denied when activating venv: run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in an elevated PowerShell once.
- Missing Python package errors: ensure virtualenv is activated and run `pip install -r requirements.txt`.
- If the frontend cannot reach backend: ensure backend is running on port 8000 and CORS origin `http://localhost:3000` matches.
- If AI models fail to initialize, check `proctor-x-backend/data/logs/app.log` for stack traces.

## Useful commands (PowerShell)
- Activate venv: .\.venv\Scripts\Activate.ps1
- Install deps: pip install -r requirements.txt
- Run backend: uvicorn main:app --reload
- Run backend (uvicorn): .\.venv\Scripts\uvicorn.exe "main:app" --reload --port 8000
- Run frontend: npm start (from `proctor-x-frontend`)

## Project notes
- The backend is a FastAPI app with WebSocket support for real-time proctoring in `routers/websocket_proctoring.py`.
- Data is stored in the `data/` folder in the backend and includes exams, submissions, logs, and models.

