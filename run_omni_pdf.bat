@echo off
echo Setting up environment...
call venv\Scripts\activate
pip install -r requirements.txt
echo Starting Omni PDF...
python main.py
pause
