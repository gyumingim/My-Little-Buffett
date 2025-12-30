@echo off

REM Backend run script for Windows

echo My Little Buffett Backend Starting...

REM Check virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check .env file
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo WARNING: Please edit .env file to set DATA_PATH
)

REM Run server
echo Starting FastAPI server...
python -m app.main

pause
