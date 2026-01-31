#!/bin/bash

# 1. Start FastAPI in the background on port 8000
uvicorn main:app --host 0.0.0.0 --port 8000 &

# 2. Start Streamlit in the foreground on the Render $PORT
# This ensures Render detects the service is "Live"
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
