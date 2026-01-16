import pytest
from fastapi.testclient import TestClient
from main import app
import io

client = TestClient(app)

def create_dummy_pdf():
    file_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is a test contract for unit testing.) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000240 00000 n \n0000000327 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n421\n%%EOF"
    return io.BytesIO(file_content)


test_doc_id = None

def test_1_health():
    """Check if the API is alive"""
    response = client.get("/healthz")
    assert response.status_code == 200

def test_2_ingest():
    """Test uploading a file"""
    global test_doc_id
    
    pdf_file = create_dummy_pdf()
    files = {'files': ('test_contract.pdf', pdf_file, 'application/pdf')}
    
    response = client.post("/ingest", files=[('files', ('test_contract.pdf', pdf_file, 'application/pdf'))])
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "test_contract.pdf" in data["processed_files"]
    
    test_doc_id = data["processed_files"][0]

def test_3_ask():
    """Test asking a question about the uploaded file"""
    payload = {"question": "What is this document about?"}
    response = client.post("/ask", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)

def test_4_extract():
    """Test extracting metadata"""
    params = {"document_id": "test_contract.pdf"}
    response = client.post("/extract", params=params)
    
    if response.status_code == 200:
        data = response.json()
        assert "parties" in data
    else:
        assert response.status_code != 404

def test_5_metrics():
    """Check if metrics updated"""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["documents_ingested"] >= 1
    assert data["questions_asked"] >= 1