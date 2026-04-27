@echo off
cd /d "%~dp0"
echo Diagnostico executado em %DATE% %TIME% > diagnostico_windows.log
echo Pasta: %CD% >> diagnostico_windows.log
echo.
echo Se voce esta vendo esta janela, arquivos .bat estao executando.
echo Foi criado o arquivo:
echo diagnostico_windows.log
echo.
pause
