@echo off
setlocal

cd /d "%~dp0"
set "LOG_FILE=%~dp0build_windows.log"
set "PYTHON_CMD="

echo.
echo ============================================================
echo  GAL - Mapas editaveis | Build para Windows
echo ============================================================
echo.
echo Pasta do projeto:
echo %CD%
echo.
echo Log do build:
echo %LOG_FILE%
echo.

echo Iniciando build... > "%LOG_FILE%"
echo Pasta do projeto: %CD% >> "%LOG_FILE%"

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    call :fail "Python nao encontrado. Instale o Python 3.11 ou superior e marque Add python.exe to PATH."
    goto :end
)

echo Usando Python:
%PYTHON_CMD% --version >> "%LOG_FILE%" 2>&1
%PYTHON_CMD% --version
if errorlevel 1 (
    call :fail "Falha ao executar Python."
    goto :end
)

echo Instalando dependencias...
echo Instalando dependencias... >> "%LOG_FILE%"
%PYTHON_CMD% -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :fail "Falha ao atualizar pip. Veja build_windows.log."
    goto :end
)

%PYTHON_CMD% -m pip install -r requirements.txt pyinstaller >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :fail "Falha ao instalar dependencias. Veja build_windows.log."
    goto :end
)

echo.
echo Limpando builds anteriores...
echo Limpando builds anteriores... >> "%LOG_FILE%"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Gerando executavel...
echo Gerando executavel... >> "%LOG_FILE%"
%PYTHON_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "GAL_Mapas_Editaveis" ^
    --paths "src" ^
    --collect-all zxingcpp ^
    src\gui.py >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :fail "PyInstaller falhou. Veja build_windows.log."
    goto :end
)

if not exist "dist\GAL_Mapas_Editaveis\GAL_Mapas_Editaveis.exe" (
    call :fail "O PyInstaller terminou, mas o executavel esperado nao foi encontrado."
    goto :end
)

echo.
echo ============================================================
echo  Build concluido.
echo.
echo  Pasta portatil:
echo  dist\GAL_Mapas_Editaveis
echo.
echo  Para usar em outro computador, copie a pasta inteira
echo  GAL_Mapas_Editaveis para o pen drive.
echo ============================================================
echo.
echo Build concluido. >> "%LOG_FILE%"
set "EXIT_CODE=0"
goto :end

:fail
echo.
echo ERRO: %~1
echo ERRO: %~1 >> "%LOG_FILE%"
set "EXIT_CODE=1"
goto :eof

:end
echo.
echo ------------------------------------------------------------
echo Se houve erro, abra este arquivo e copie o conteudo:
echo %LOG_FILE%
echo ------------------------------------------------------------
echo.
pause
exit /b %EXIT_CODE%
