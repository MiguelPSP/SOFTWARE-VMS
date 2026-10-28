@echo off
title INTERFACE SOFTWARE VMS - 64 Canais
cd /d "C:\Users\mayla\.gemini\antigravity\scratch\vms_desktop"
echo ===================================================
echo        Iniciando INTERFACE SOFTWARE VMS
echo            (Identidade Preto e Amarelo)
echo ===================================================
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao executar. Verifique se as dependencias estao instaladas.
    pause
)
