import logging
from pinecone import Pinecone, ServerlessSpec
from langchain_groq import ChatGroq
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings

# Setup Logger
logger = logging.getLogger("contract_api.rag")

try:
    # 1. Initialize Pinecone Client
    logger.info("Connecting to Pinecone...")
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    # Check/Create Index
    existing_indexes = [i.name for i in pc.list_indexes()]
    if settings.PINECONE_INDEX not in existing_indexes:
        logger.info(f"Index '{settings.PINECONE_INDEX}' not found. Creating it...")
        pc.create_index(
            name=settings.PINECONE_INDEX,
            dimension=384, 
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        logger.info(f"Index '{settings.PINECONE_INDEX}' created successfully.")
    else:
        logger.info(f"Found existing index: '{settings.PINECONE_INDEX}'")
        
    # 2. Setup Embeddings
    logger.info(f"Loading FastEmbed model: {settings.EMBEDDING_MODEL}")
    embeddings = FastEmbedEmbeddings(model_name=settings.EMBEDDING_MODEL)

    # 3. Setup Vector Store
    logger.info("Initializing VectorStore...")
    vectorstore = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX, 
        embedding=embeddings,
        pinecone_api_key=settings.PINECONE_API_KEY
    )

    # 4. Setup LLM (Groq)
    logger.info("Initializing Groq LLM...")
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        groq_api_key=settings.GROQ_API_KEY
    )
    logger.info("RAG components initialized successfully.")

except Exception as e:
    logger.critical(f"CRITICAL ERROR initializing RAG components: {str(e)}")
    raise e