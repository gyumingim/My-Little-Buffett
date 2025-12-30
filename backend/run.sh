#!/bin/bash

# Backend run script

echo "🐂 My Little Buffett Backend Starting..."

# 가상 환경 확인
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 가상 환경 활성화
source venv/bin/activate

# 패키지 설치
echo "Installing dependencies..."
pip install -r requirements.txt

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️ Please edit .env file to set DATA_PATH"
fi

# 서버 실행
echo "Starting FastAPI server..."
python -m app.main
