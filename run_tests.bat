@echo off
echo ======================================================================
echo Running Rebound Automated Test Suite (Sections 8.A - 8.E)
echo ======================================================================
echo.
python -m pytest backend/tests/test_sentinel.py backend/tests/test_pipeline.py -v
echo.
pause
