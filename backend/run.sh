#!/bin/bash

# AUTO-V Backend Startup Script

echo "🚀 Starting AUTO-V Backend Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cat > .env << EOF
SUPABASE_URL=https://tsvejnzxrxrrecgquxbq.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ
EOF
fi

# Run the server
echo "✅ Starting server on http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/api/docs"

# Run with uvicorn for development
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
