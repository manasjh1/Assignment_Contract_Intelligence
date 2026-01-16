import uvicorn
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("contract_api.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application is starting up...")
    yield
    logger.info("Application is shutting down...")

app = FastAPI(
    title="Contract Intelligence API", 
    version="1.0.0", 
    lifespan=lifespan  # Using the new lifespan parameter
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"Incoming: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        logger.info(f"Completed: {response.status_code} (took {process_time:.2f}ms)")
        return response
        
    except Exception as e:
        logger.error(f"Request Failed: {str(e)}")
        raise e

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/healthz")
def health():
    return {"status": "ok", "env": "production"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)