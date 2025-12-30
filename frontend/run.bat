@echo off

REM Frontend run script for Windows

echo My Little Buffett Frontend Starting...

REM Install dependencies
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

REM Run dev server
echo Starting Vite dev server...
call npm run dev

pause
