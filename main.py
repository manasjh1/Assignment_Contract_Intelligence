import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Contract Intelligence API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/healthz")
def health():
    return {"status": "ok", "env": "production"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)