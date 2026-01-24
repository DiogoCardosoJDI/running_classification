@echo off
:: Muda para o diretorio onde o arquivo .bat esta salvo
cd /d "%~dp0"

echo ==========================================
echo   CONFIGURANDO AMBIENTE DE CRONOMETRAGEM
echo ==========================================

:: Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale o Python e marque "Add to PATH".
    pause
    exit /b
)

:: Cria a virtualenv se nao existir
if not exist ".venv" (
    echo [+] Criando ambiente virtual (.venv)...
    python -m venv .venv
) else (
    echo [i] Ambiente virtual ja existe.
)

:: Ativa o ambiente
echo [+] Ativando ambiente...
call .venv\Scripts\activate

:: Atualiza o pip e instala dependencias
echo [+] Instalando bibliotecas do requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ==========================================
echo      INSTALACAO CONCLUIDA COM SUCESSO
echo ==========================================
pause