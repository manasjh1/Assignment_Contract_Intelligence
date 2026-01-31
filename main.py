import uvicorn
import subprocess
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    yield

app = FastAPI(title="Ask-the-docs", version="1.0.0", lifespan=lifespan)

# CORS is critical when running both on one machine to prevent browser blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    # Redirecting to /docs for the API side
    return RedirectResponse(url="/docs")

@app.get("/healthz")
def health():
    return {"status": "ok", "env": "production"}

def run_streamlit():
    """Helper to launch streamlit as a background process"""
    print("Launching Streamlit Frontend...")
    # We use the port 8501 for internal Streamlit or $PORT if it's the main entry
    subprocess.Popen([
        "streamlit", "run", "streamlit_app.py", 
        "--server.port", os.environ.get("PORT", "8501"), 
        "--server.address", "0.0.0.0"
    ])

if __name__ == "__main__":
    # If running locally or via a single-start command:
    # 1. Start Streamlit
    run_streamlit()
    # 2. Start FastAPI on a different internal port (e.g., 8000)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
