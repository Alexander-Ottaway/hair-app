@echo off

call venv\Scripts\activate

start cmd /k "uvicorn auth_service.auth:app --port 8001 --reload"

start cmd /k "uvicorn booking_service.booking:app --port 8002 --reload"

echo Launched both services. Close these windows to stop them.
pause
