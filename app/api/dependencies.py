from app.core.rag import vectorstore, llm

# Simple dependency injection pattern
def get_vectorstore():
    return vectorstore

def get_llm():
    return llm