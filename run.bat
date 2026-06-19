@echo off
if "%1"=="" (
    echo Uzycie: run.bat sciezka\do\scenariusza.txt [--skip-video]
    exit /b 1
)
python main.py %*
