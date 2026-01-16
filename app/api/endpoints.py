import shutil
import os
import logging
import asyncio
import httpx
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import SystemMessage, HumanMessage
import fitz  
from app.core.rag import get_vectorstore, get_llm
from app.core.prompts import AUDIT_PROMPT
from app.schemas.models import (
    ExtractResponse, 
    AskRequest, 
    AuditResponse, 
    WebhookRequest
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contract_api")

router = APIRouter()

METRICS = {
    "documents_ingested": 0,
    "questions_asked": 0,
    "risks_audited": 0,
    "webhooks_triggered": 0,
    "errors": 0
}

async def send_webhook_notification(url: str, payload: dict):
    await asyncio.sleep(5)
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={"status": "completed", "data": payload}, timeout=10.0)
        except Exception as e:
            logger.error(f"Webhook failed: {e}")

@router.post("/ingest")
async def ingest_pdfs(files: List[UploadFile] = File(...)):
    processed_files = []
    
    try:
        vs = get_vectorstore()

        for file in files:
            temp_filename = f"temp_{file.filename}"
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"Processing file: {file.filename}")
            
            doc = fitz.open(temp_filename)
            total_pages = len(doc)
            
            BATCH_SIZE = 10
            batch_text = ""
            
            for i, page in enumerate(doc):
                batch_text += page.get_text() + "\n"
                
                # If batch is full OR last page
                if (i + 1) % BATCH_SIZE == 0 or (i + 1) == total_pages:
                    logger.info(f"Uploading batch: Pages {i-BATCH_SIZE+2} to {i+1}")
                    
                    if batch_text.strip():
                        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                        chunks = splitter.create_documents([batch_text], metadatas=[{"source": file.filename}])
                        vs.add_documents(chunks)
                    
                    batch_text = "" # FREE MEMORY
            
            doc.close()
            
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            
            processed_files.append(file.filename)
            METRICS["documents_ingested"] += 1

        return {"status": "success", "processed_files": processed_files}

    except Exception as e:
        METRICS["errors"] += 1
        # Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        logger.error(f"Ingest failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract", response_model=ExtractResponse)
async def extract_metadata(document_id: str):
    try:
        vs = get_vectorstore()
        llm = get_llm()

        retriever = vs.as_retriever(search_kwargs={"k": 10, "filter": {"source": document_id}})
        docs = retriever.invoke("Extract contract parties, dates, liability, and terms.")
        
        if not docs:
            raise HTTPException(status_code=404, detail="Document not found")

        context = "\n\n".join([d.page_content for d in docs])
        structured_llm = llm.with_structured_output(ExtractResponse)
        return await structured_llm.ainvoke(f"Extract fields from:\n{context}")

    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_question(req: AskRequest):
    METRICS["questions_asked"] += 1
    try:
        vs = get_vectorstore()
        llm = get_llm()

        docs = vs.similarity_search(req.question, k=4)
        context = "\n\n".join([d.page_content for d in docs])
        
        messages = [
            SystemMessage(content=f"Answer based on:\n{context}"),
            HumanMessage(content=req.question)
        ]
        
        response = llm.invoke(messages)
        sources = list({doc.metadata.get("source", "unknown") for doc in docs})
        return {"answer": response.content, "citations": sources}

    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ask/stream")
async def stream_question(question: str):
    try:
        vs = get_vectorstore()
        llm = get_llm()

        docs = vs.similarity_search(question, k=4)
        context = "\n\n".join([d.page_content for d in docs])
        
        async def event_generator():
            messages = [
                SystemMessage(content=f"Answer based on:\n{context}"),
                HumanMessage(content=question)
            ]
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield f"data: {chunk.content}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audit", response_model=AuditResponse)
async def audit_contract(document_id: str):
    METRICS["risks_audited"] += 1
    try:
        vs = get_vectorstore()
        llm = get_llm()

        retriever = vs.as_retriever(search_kwargs={"k": 15, "filter": {"source": document_id}})
        docs = retriever.invoke("termination indemnity liability auto-renewal")
        context = "\n\n".join([d.page_content for d in docs])
        
        structured_llm = llm.with_structured_output(AuditResponse)
        return await structured_llm.ainvoke(AUDIT_PROMPT.format(context=context))

    except Exception as e:
        METRICS["errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/events")
async def trigger_webhook_event(req: WebhookRequest, background_tasks: BackgroundTasks):
    METRICS["webhooks_triggered"] += 1
    background_tasks.add_task(send_webhook_notification, req.callback_url, {"task": req.task_type})
    return {"status": "processing_started"}

@router.get("/metrics")
def get_metrics():
    return METRICS