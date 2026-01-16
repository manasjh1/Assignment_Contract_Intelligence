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

from app.core.rag import vectorstore, llm
from app.core.prompts import AUDIT_PROMPT
from app.schemas.models import (
    ExtractResponse, 
    AskRequest, 
    AuditResponse, 
    WebhookRequest
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
    """
    Simulates a long-running task and then POSTs data to the user's callback URL.
    """
    logger.info(f"⏳ [Background] Starting task for webhook: {url}")
    
    
    await asyncio.sleep(5)
    
    result_data = {
        "status": "completed",
        "event": "analysis_finished",
        "data": payload
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=result_data, timeout=10.0)
            logger.info(f"[Background] Webhook sent to {url} | Status: {resp.status_code}")
        except Exception as e:
            logger.error(f"[Background] Webhook failed: {str(e)}")

@router.post("/ingest")
async def ingest_pdfs(files: List[UploadFile] = File(...)):
    logger.info(f"Received ingest request for {len(files)} files.")
    processed_files = []
    
    for file in files:
        temp_filename = f"temp_{file.filename}"
        try:
            logger.info(f"Processing file: {file.filename}")
            
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            doc = fitz.open(temp_filename)
            text = "".join([page.get_text() for page in doc])
            doc.close()
            
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = splitter.create_documents([text], metadatas=[{"source": file.filename}])
            
            vectorstore.add_documents(chunks)
            
            METRICS["documents_ingested"] += 1
            processed_files.append(file.filename)
            logger.info(f"Successfully ingested {file.filename} ({len(chunks)} chunks)")
            
        except Exception as e:
            METRICS["errors"] += 1
            logger.error(f"Failed to ingest {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing {file.filename}")
            
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    return {"status": "success", "processed_files": processed_files}

@router.post("/extract", response_model=ExtractResponse)
async def extract_metadata(document_id: str):
    logger.info(f"Extracting metadata for document: {document_id}")
    try:
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 10, "filter": {"source": document_id}}
        )
        docs = retriever.invoke("Extract contract parties, dates, liability, and terms.")
        
        if not docs:
            logger.warning(f"No documents found for ID: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        context_text = "\n\n".join([d.page_content for d in docs])
        
        structured_llm = llm.with_structured_output(ExtractResponse)
        prompt = f"Analyze the contract text below and extract the fields.\nContract Text:\n{context_text}"
        
        result = await structured_llm.ainvoke(prompt)
        logger.info(f"Extraction complete for {document_id}")
        return result

    except Exception as e:
        METRICS["errors"] += 1
        logger.error(f"Extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Extraction failed")

@router.post("/ask")
async def ask_question(req: AskRequest):
    logger.info(f"Received question: {req.question}")
    METRICS["questions_asked"] += 1
    
    try:
        docs = vectorstore.similarity_search(req.question, k=4)
        context_text = "\n\n".join([d.page_content for d in docs])
        
        messages = [
            SystemMessage(content=f"Answer based on this context:\n{context_text}"),
            HumanMessage(content=req.question)
        ]
        
        response = llm.invoke(messages)
        sources = list({doc.metadata.get("source", "unknown") for doc in docs})
        
        logger.info(f"Answered question using sources: {sources}")
        return {"answer": response.content, "citations": sources}

    except Exception as e:
        METRICS["errors"] += 1
        logger.error(f"Q&A failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Q&A processing failed")

@router.get("/ask/stream")
async def stream_question(question: str):
    logger.info(f"Streaming answer for: {question}")
    METRICS["questions_asked"] += 1
    
    try:
        docs = vectorstore.similarity_search(question, k=4)
        context_text = "\n\n".join([d.page_content for d in docs])
        
        async def event_generator():
            messages = [
                SystemMessage(content=f"Answer based on this context:\n{context_text}"),
                HumanMessage(content=question)
            ]
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield f"data: {chunk.content}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Streaming failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Streaming failed")

@router.post("/audit", response_model=AuditResponse)
async def audit_contract(document_id: str):
    logger.info(f"Auditing contract risks for: {document_id}")
    METRICS["risks_audited"] += 1
    
    try:
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 15, "filter": {"source": document_id}}
        )
        docs = retriever.invoke("termination indemnity liability auto-renewal")
        context_text = "\n\n".join([d.page_content for d in docs])
        
        formatted_prompt = AUDIT_PROMPT.format(context=context_text)
        structured_llm = llm.with_structured_output(AuditResponse)
        
        result = await structured_llm.ainvoke(formatted_prompt)
        
        risk_count = len(result.risks) if result.risks else 0
        logger.info(f"Audit complete. Found {risk_count} risks.")
        return result

    except Exception as e:
        METRICS["errors"] += 1
        logger.error(f"Audit failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Audit processing failed")

@router.post("/webhook/events")
async def trigger_webhook_event(req: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Accepts a URL. Starts a background task. Returns immediately.
    """
    METRICS["webhooks_triggered"] += 1
    logger.info(f"Received webhook trigger for: {req.callback_url}")
    
    background_tasks.add_task(
        send_webhook_notification, 
        req.callback_url, 
        {"task": req.task_type, "details": "Analysis complete"}
    )
    
    return {"status": "processing_started", "message": "We will notify your URL when done."}

@router.get("/metrics")
def get_metrics():
    logger.info("Metrics requested")
    return METRICS