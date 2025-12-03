#!/bin/bash
set -e

echo "Starting Agentic Scraper..."

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable is not set!"
    echo "Please set it in the Space settings under 'Repository secrets'"
    exit 1
fi

echo "Starting FastAPI backend..."
cd /app/backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/query/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Backend failed to start within 30 seconds"
        echo "Backend logs:"
        cat /tmp/backend.log
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Start Gradio frontend (foreground - keeps container alive)
echo "Starting Gradio frontend..."
cd /app/frontend
python app.py
