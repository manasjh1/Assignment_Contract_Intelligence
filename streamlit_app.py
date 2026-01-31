import streamlit as st
import requests
import os

# Set the API URL. On Render, set the API_URL environment variable to your backend URL.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Contract QA", layout="centered")

st.title("📄 Contract Intelligence")
st.markdown("Upload a PDF to index it, then ask questions about its content.")

# --- SECTION 1: Upload ---
st.header("1. Upload & Index")
uploaded_file = st.file_uploader("Choose a PDF document", type=["pdf"])

if uploaded_file is not None:
    if st.button("Index Document"):
        with st.spinner("Processing PDF and updating vector store..."):
            try:
                # Matches your backend: @router.post("/ingest") 
                # Expects a list of files on the "files" key
                files = [("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf"))]
                
                response = requests.post(f"{API_URL}/ingest", files=files)
                
                if response.status_code == 200:
                    st.success(f"✅ Successfully indexed: {uploaded_file.name}")
                else:
                    st.error(f"❌ Upload Failed: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

st.divider()

# --- SECTION 2: Query ---
st.header("2. Ask a Question")
query = st.text_input("Enter your question about the uploaded document:")

if st.button("Search"):
    if query:
        with st.spinner("Searching document and generating answer..."):
            try:
                # Matches your backend: @router.post("/ask")
                # Expects AskRequest schema: {"question": "string"}
                payload = {"question": query}
                response = requests.post(f"{API_URL}/ask", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    st.markdown("### Answer")
                    st.info(data['answer'])
                    
                    # Display citations if available
                    if data.get('citations'):
                        with st.expander("View Sources"):
                            for source in data['citations']:
                                st.write(f"📍 Source: {source}")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
    else:
        st.warning("Please enter a question.")
