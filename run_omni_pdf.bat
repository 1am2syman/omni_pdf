@echo off
echo Setting up environment...
call omnipdfenv\Scripts\activate
	

REM Check if packages in requirements.txt are installed using check_requirements.py
echo Checking for required packages...
python check_requirements.py
if errorlevel 1 (
    echo Installing packages from requirements.txt...
    pip install -r requirements.txt
) else (
    echo All required packages are already installed.
)

echo Starting Omni PDF...
python main.py
pause
