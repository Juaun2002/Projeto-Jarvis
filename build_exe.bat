@echo off
echo ===================================
echo   JARVIS - Criando Executavel
echo ===================================
echo.

REM Limpa builds anteriores
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo [1/3] Gerando executavel...
python -m PyInstaller ^
    --name="JARVIS" ^
    --onefile ^
    --windowed ^
    --icon=NONE ^
    --add-data="piper;piper" ^
    --add-data="vosk-model-small-pt-0.3;vosk-model-small-pt-0.3" ^
    --add-data="config.py;." ^
    --hidden-import="vosk" ^
    --hidden-import="piper" ^
    --hidden-import="sounddevice" ^
    --hidden-import="pyqtgraph" ^
    --hidden-import="psutil" ^
    --hidden-import="ollama" ^
    --collect-all="vosk" ^
    --collect-all="piper" ^
    --collect-all="sounddevice" ^
    --collect-all="pyqtgraph" ^
    main_vosk.py

echo.
echo [2/3] Limpando arquivos temporarios...
rmdir /s /q "build"
del /q "JARVIS.spec"

echo.
echo [3/3] Concluido!
echo.
echo ===================================
echo   Executavel criado em: dist\JARVIS.exe
echo ===================================
echo.
echo Pressione qualquer tecla para sair...
pause > nul
