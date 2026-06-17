Session Recap — Internship Tracker: Project Skeleton
Date: June 16, 2026

Time spent: ~1 hour

WHAT
Built the complete project skeleton for the Internship Tracker app — a full-stack web application with a React frontend, FastAPI backend, and a working health endpoint pushed to GitHub.

WHY

Every real software project needs a solid foundation before any features are built. Rushing into features without structure leads to messy, hard-to-maintain code
Setting up the skeleton first means every future session has a clean, organized place to add code
Pushing to GitHub immediately means your work is never lost and employers can see your progress from day one
Doing this yourself (not copying a template) means you understand every file in your project


HOW
Step 1 — Verified tools were installed
bashnode --version    # v20.10.0
npm --version     # 10.2.3
python --version  # 3.14.5
These three tools power everything — Node/npm for React, Python for FastAPI.
Step 2 — Created the folder structure
bashmkdir internship-tracker
cd internship-tracker
mkdir backend
mkdir frontend
Separating backend and frontend keeps concerns clean — two separate "worlds" that talk to each other through APIs.
Step 3 — Set up the React frontend
bashcd frontend
npx create-react-app frontend
npm start
React runs on http://localhost:3000. The spinning logo confirmed it was alive.
Step 4 — Set up the FastAPI backend
bashcd backend
python -m venv venv       # created isolated Python environment
venv\Scripts\activate     # activated it (saw "(venv)" appear)
pip install fastapi uvicorn
pip freeze > requirements.txt
The virtual environment is like a separate Python "room" just for this project — keeps dependencies isolated and professional.
Step 5 — Created backend/main.py
pythonfrom fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, ...)

@app.get("/health")
def health_check():
    return {"status": "ok"}

FastAPI() creates the app
CORSMiddleware gives React permission to talk to FastAPI
/health endpoint confirms the server is alive

Step 6 — Ran the backend server
bashuvicorn main:app --reload
Confirmed working at:

http://localhost:8000/health → {"status": "ok"}
http://localhost:8000/docs → auto-generated API docs (free with FastAPI!)

Step 7 — Created .gitignore at root
venv/
__pycache__/
node_modules/
frontend/build/
.env
.vscode/
Prevents large/sensitive folders from being uploaded to GitHub.
Step 8 — Pushed to GitHub
bashgit init
git add .
git commit -m "initial project skeleton: React frontend + FastAPI backend"
git branch -M main
git remote add origin https://github.com/justinllai/internship-tracker.git
git push -u origin main

KEY CONCEPTS LEARNED
ConceptWhat it means in plain EnglishVirtual environmentA separate Python "room" so packages don't conflict between projectsCORSA browser security rule — middleware gives React permission to talk to FastAPIPortAn address on your computer — React uses 3000, FastAPI uses 8000200 OKHTTP status code meaning "success"404 Not FoundHTTP status code meaning "that URL doesn't exist".gitignoreA list of files/folders Git should never uploadrequirements.txtA list of all Python packages this project needs--reload flagTells Uvicorn to restart automatically when you save a file

DECISIONS MADE
DecisionWhat we choseWhyFrontendReactIndustry standard, shows up in every job postingBackendFastAPIYou already know Python, same patterns as NBA appDatabaseSQLiteReal persistent storage, no setup complexity for V1AuthUser accountsMost impressive for portfolio — shows real engineeringRepo visibilityPublicEmployers can