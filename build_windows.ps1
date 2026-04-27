$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$LogFile = Join-Path $ProjectDir "build_windows.log"
"Iniciando build em $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
"Pasta do projeto: $ProjectDir" | Out-File -FilePath $LogFile -Encoding UTF8 -Append

function Write-Step($Message) {
    Write-Host ""
    Write-Host $Message
    $Message | Out-File -FilePath $LogFile -Encoding UTF8 -Append
}

function Run-Logged($Command, $Arguments) {
    Write-Step "$Command $Arguments"
    $process = Start-Process -FilePath $Command -ArgumentList $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$env:TEMP\gal_build_stdout.txt" -RedirectStandardError "$env:TEMP\gal_build_stderr.txt"
    Get-Content "$env:TEMP\gal_build_stdout.txt" | Out-File -FilePath $LogFile -Encoding UTF8 -Append
    Get-Content "$env:TEMP\gal_build_stderr.txt" | Out-File -FilePath $LogFile -Encoding UTF8 -Append
    if ($process.ExitCode -ne 0) {
        throw "Comando falhou com codigo $($process.ExitCode): $Command $Arguments"
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host " GAL - Mapas editaveis | Build para Windows"
Write-Host "============================================================"
Write-Host ""
Write-Host "Log: $LogFile"

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $Python) {
    throw "Python nao encontrado. Instale Python 3.11 ou superior e marque Add python.exe to PATH."
}

if ($Python.Name -eq "py.exe") {
    $PythonCommand = "py"
    $PythonPrefix = "-3"
} else {
    $PythonCommand = "python"
    $PythonPrefix = ""
}

Write-Step "Usando Python"
if ($PythonPrefix) {
    Run-Logged $PythonCommand "$PythonPrefix --version"
    Run-Logged $PythonCommand "$PythonPrefix -m pip install --upgrade pip"
    Run-Logged $PythonCommand "$PythonPrefix -m pip install -r requirements.txt pyinstaller"
} else {
    Run-Logged $PythonCommand "--version"
    Run-Logged $PythonCommand "-m pip install --upgrade pip"
    Run-Logged $PythonCommand "-m pip install -r requirements.txt pyinstaller"
}

Write-Step "Limpando builds anteriores"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Step "Gerando executavel"
$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "GAL_Mapas_Editaveis",
    "--paths", "src",
    "--collect-all", "zxingcpp",
    "src\gui.py"
)

if ($PythonPrefix) {
    Run-Logged $PythonCommand "$PythonPrefix $($PyInstallerArgs -join ' ')"
} else {
    Run-Logged $PythonCommand "$($PyInstallerArgs -join ' ')"
}

$ExePath = Join-Path $ProjectDir "dist\GAL_Mapas_Editaveis\GAL_Mapas_Editaveis.exe"
if (-not (Test-Path $ExePath)) {
    throw "Executavel esperado nao encontrado: $ExePath"
}

Write-Step "Build concluido"
Write-Host ""
Write-Host "Pasta portatil:"
Write-Host "dist\GAL_Mapas_Editaveis"
Write-Host ""
Read-Host "Pressione ENTER para fechar"
