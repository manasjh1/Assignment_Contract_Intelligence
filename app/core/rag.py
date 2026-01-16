import logging
from pinecone import Pinecone, ServerlessSpec
from langchain_groq import ChatGroq
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings

# Setup Logger
logger = logging.getLogger("contract_api.rag")

# GLOBAL VARIABLES (Initially None)
_vectorstore = None
_llm = None
_embeddings = None

def initialize_rag():
    """
    Lazy loads the RAG components. 
    Only runs when the first request hits the API.
    """
    global _vectorstore, _llm, _embeddings
    
    # If already loaded, return them immediately
    if _vectorstore is not None and _llm is not None:
        return _vectorstore, _llm

    logger.info("Lazy Loading RAG components...")
    
    try:
        # 1. Initialize Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Check/Create Index
        existing_indexes = [i.name for i in pc.list_indexes()]
        if settings.PINECONE_INDEX not in existing_indexes:
            logger.info(f"Creating index: {settings.PINECONE_INDEX}")
            pc.create_index(
                name=settings.PINECONE_INDEX,
                dimension=384, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        # 2. Setup Embeddings (FastEmbed / ONNX)
        logger.info(f"Loading Embedding Model: {settings.EMBEDDING_MODEL}")
        _embeddings = FastEmbedEmbeddings(model_name=settings.EMBEDDING_MODEL)

        # 3. Setup Vector Store
        _vectorstore = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX, 
            embedding=_embeddings,
            pinecone_api_key=settings.PINECONE_API_KEY
        )

        # 4. Setup LLM
        _llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=settings.GROQ_API_KEY
        )
        
        logger.info("RAG components loaded successfully.")
        return _vectorstore, _llm

    except Exception as e:
        logger.critical(f"Failed to load RAG: {str(e)}")
        raise e

def get_vectorstore():
    if _vectorstore is None:
        initialize_rag()
    return _vectorstore

def get_llm():
    if _llm is None:
        initialize_rag()
    return _llm