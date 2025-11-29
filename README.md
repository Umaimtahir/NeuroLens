# NeuroLens (Monorepo)

This repository contains the backend (FastAPI) and a placeholder for the Android frontend.

Structure
- `backend/` — FastAPI backend (this folder)
- `android-app/` — place your Android Studio project here (not included)

Quickstart (backend)
1. Create and activate a venv:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` (see `.env.example` or set env vars):
- `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`

4. Run the server:

```powershell
uvicorn main:app --reload
```

Model files
- Trained models should be placed in `models/` (e.g. `models/emotion_model.h5`).
- For large binary model files use Git LFS or external storage.

Android app
- Copy your Android Studio project into `android-app/`.
- Keep `local.properties` and keystores out of git.

CI / Secrets
- Add secrets (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY, Android signing keys) in GitHub repository settings when you create the remote repo.

