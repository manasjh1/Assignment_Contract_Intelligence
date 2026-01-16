# Contract Intelligence API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Render-purple.svg)](https://render.com)

## Overview

The **Contract Intelligence API** is a high-performance, asynchronous backend designed to analyze legal documents automatically. It leverages Large Language Models (Llama 3 via Groq) and Vector Search (Pinecone) to extract metadata, audit risks, and answer natural language questions about uploaded contracts.

This project was specifically engineered for **resource-constrained environments (512MB RAM)**, utilizing advanced memory management techniques, streaming batch processing, and ONNX-quantized embeddings to ensure enterprise-grade stability on free-tier infrastructure.

## System Architecture

The system follows an **event-driven RAG (Retrieval-Augmented Generation) pipeline** optimized for memory efficiency:

### Core Components

#### API Layer (`/api`)
- **endpoints.py**: Defines all REST API routes (`/ingest`, `/ask`, `/audit`, `/extract`, `/healthz`)
- **dependencies.py**: Handles dependency injection and middleware
- **FastAPI Integration**: Async request handling with automatic OpenAPI documentation

#### Core Business Logic (`/core`)
- **rag.py**: Implements the RAG pipeline with Pinecone vector search and Groq LLM integration
- **config.py**: Centralized configuration management for API keys and model settings
- **prompts.py**: Template management for LLM interactions and structured outputs

#### Data Models (`/schemas`)
- **models.py**: Pydantic schemas for request/response validation and serialization
- **Type Safety**: Ensures data integrity across API boundaries

#### Testing Suite (`/tests`)
- **test_api.py**: API integration tests
- **test_endpoints.py**: Individual endpoint testing
- **test_stream.py**: Streaming response validation

### Memory Optimization Strategy

#### Ingestion Layer
- **Streaming Uploads**: Handles large PDF binaries via `shutil` streaming to avoid memory spikes
- **Batch Processing**: Implements a strict 5-page batching strategy with immediate garbage collection

#### Embedding Layer
- **Model**: BAAI/bge-small-en-v1.5 (Quantized ONNX)
- **Optimization**: Runs on ONNX Runtime with `OMP_NUM_THREADS=1` to minimize CPU contention and memory footprint

#### Retrieval & Generation
- **Vector Store**: Pinecone Serverless (Cosine Similarity)
- **LLM**: Llama-3-70b-Versatile (via Groq) for near-instant inference (~300 tokens/sec)

#### Operational Resilience
- **Lazy Loading**: Heavy ML components (Embeddings, LLM Clients) are initialized only upon the first API request, preventing "Cold Start" timeouts
- **Automated Keep-Alive**: A GitHub Actions workflow pings the health endpoint every 14 minutes to prevent the serverless container from idling

## Key Features

- **Smart Ingestion**: Robustly handles large multi-page contracts without OOM (Out-of-Memory) crashes using a proprietary batch-and-GC strategy
- **Semantic Search**: Context-aware Q&A that cites specific contract clauses (e.g., "What is the indemnity cap?")
- **Automated Audit**: Instantly scans contracts for high-risk terms (termination, liability, auto-renewal) and generates a risk report
- **Structured Extraction**: Extract entities (parties, dates, amounts) into strict JSON formats using LLM function calling
- **CI/CD Automation**: Fully automated deployment pipeline with self-healing keep-alive mechanisms

## Tech Stack

| Component | Technology | Reason for Choice |
|-----------|------------|-------------------|
| **Framework** | FastAPI | High-performance, native async support, and auto-generated Swagger UI |
| **LLM** | Groq (Llama 3) | Fastest inference speed on the market, critical for real-time chat |
| **Vector DB** | Pinecone | Serverless architecture eliminates database management overhead |
| **Embeddings** | FastEmbed | CPU-optimized, lightweight (<200MB RAM) alternative to standard PyTorch models |
| **PDF Engine** | PyMuPDF (Fitz) | C++ based parsing offers 10x speed improvement over PyPDF2 |

## Performance Engineering

To deploy this ML-heavy application on a **Free Tier (512MB RAM)** instance, specific optimizations were implemented:

1. **Quantized Embeddings**: Replaced all-MiniLM-L6-v2 (PyTorch) with BAAI/bge-small-en-v1.5 (ONNX), reducing model memory usage by ~60%
2. **Lazy Initialization Pattern**: Global variables for VectorStore and LLM are initialized inside a singleton pattern (`initialize_rag`), ensuring the server boots instantly (<1s)
3. **Aggressive Garbage Collection**: Intermediate objects (chunks, splitters) are explicitly deleted (`del`) and garbage collected (`gc.collect()`) after every 5-page batch to maintain a flat memory profile during large file uploads

## Getting Started

### Prerequisites

- Python 3.12
- Pinecone API Key
- Groq API Key

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/BACKEND-CONTRACT-API.git
cd BACKEND-CONTRACT-API
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=gsk_...
PINECONE_API_KEY=pc_...
PINECONE_INDEX=contract-intelligence
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

### 4. Run Locally

```bash
uvicorn main:app --reload --port 8000
```

Visit [https://assignment-contract-intelligence.onrender.com/docs](https://assignment-contract-intelligence.onrender.com/docs) to interact with the API Swagger UI.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Upload PDF contracts (Streaming Batch Process) |
| `POST` | `/ask` | Q&A with RAG context and source citations |
| `GET` | `/ask/stream` | Streaming response for long-form answers |
| `POST` | `/audit` | Risk assessment against standard legal clauses |
| `POST` | `/extract` | Structured JSON extraction of metadata |
| `GET` | `/healthz` | Health check probe for keep-alive bots |

### Example Usage

#### Upload a Contract
```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contract.pdf"
```

#### Ask Questions
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the termination clause?"}'
```

#### Audit Contract
```bash
curl -X POST "http://localhost:8000/audit" \
  -H "Content-Type: application/json" \
  -d '{"contract_id": "contract_123"}'
```

## Deployment

### Render Configuration

- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 10000 --workers 1`

### Environment Variables
```env
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
FASTEMBED_CACHE_PATH=/opt/render/project/src/fastembed_cache
```

### Keep-Alive Automation

The project includes a GitHub Actions workflow that automatically pings the health endpoint every 14 minutes to prevent serverless containers from idling:

```yaml
# .github/workflows/keep-alive.yml
name: Keep Alive
on:
  schedule:
    - cron: '*/14 * * * *'  # Every 14 minutes
  workflow_dispatch:
jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping API
        run: curl -f ${{ secrets.API_URL }}/healthz
```

## Performance Metrics

- **Memory Usage**: <512MB RAM (Free Tier Compatible)
- **Startup Time**: <1 second (Lazy Loading)
- **Inference Speed**: ~300 tokens/sec (Groq)
- **Embedding Speed**: ~50 pages/minute (ONNX)
- **Batch Processing**: 5 pages per batch (Memory Safe)

## Security Features

- Input validation for all file uploads
- Rate limiting on API endpoints
- Secure environment variable management
- PDF content sanitization
- Memory leak prevention

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/

# Code formatting (if using)
black .
flake8 .
```

### Project Structure

```
BACKEND-CONTRACT-API/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Dependencies
├── .env                      # Environment variables
├── .gitignore               # Git ignore rules
├── app/
│   └── __pycache__/         # Compiled Python files
├── api/                     # API layer
│   ├── __init__.py
│   ├── dependencies.py      # Dependency injection
│   └── endpoints.py         # API route definitions
├── core/                    # Core business logic
│   ├── __pycache__/
│   ├── config.py           # Configuration management
│   ├── prompts.py          # LLM prompt templates
│   └── rag.py              # RAG implementation
├── schemas/                 # Pydantic models
│   ├── __pycache__/
│   ├── __init__.py
│   └── models.py           # Data models and validation
└── tests/                   # Test suite
    ├── __pycache__/
    ├── test_api.py         # API endpoint tests
    ├── test_endpoints.py   # Endpoint-specific tests
    └── test_stream.py      # Streaming functionality tests
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Manas Jha**  
Backend Engineer | AI Systems

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue.svg)](https://linkedin.com/in/your-profile)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black.svg)](https://github.com/your-username)

---

**Star this repository if you found it helpful!**

## Roadmap

- [ ] Multi-language contract support
- [ ] Advanced risk scoring algorithms
- [ ] Real-time collaborative editing
- [ ] Integration with legal databases
- [ ] Mobile app companion
- [ ] Enterprise SSO integration

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/your-username/BACKEND-CONTRACT-API/issues) page
2. Create a new issue with detailed description
3. Contact: [your-email@example.com](mailto:your-email@example.com)

---

**Built with dedication for the legal tech community**
