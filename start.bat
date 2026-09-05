@echo off
echo ======================================================================
echo Launching Rebound: AI Revenue Recovery Agent Console
echo Track 3: Razorpay AI Buildathon
echo ======================================================================
echo.
echo Starting FastAPI server with integrated React Operations Console...
echo Open your browser at: http://127.0.0.1:8000
echo API Documentation:   http://127.0.0.1:8000/docs
echo.
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
pause
