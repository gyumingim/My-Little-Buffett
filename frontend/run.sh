#!/bin/bash

# Frontend run script

echo "🎨 My Little Buffett Frontend Starting..."

# 패키지 설치
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# 개발 서버 실행
echo "Starting Vite dev server..."
npm run dev
