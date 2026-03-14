::@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   CONFIGURANDO AMBIENTE DE CRONOMETRAGEM
echo ==========================================

:: 1. Define o comando do Python
set PY_CMD=py
py --version >nul 2>&1
if %errorlevel% neq 0 set PY_CMD=python

:: 2. Verifica se o Python existe
%PY_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale e marque "Add to PATH".
    pause
    exit /b
)

echo [i] Usando comando: %PY_CMD%

:: 3. Cria a venv (Sem blocos de parenteses longos)
if exist ".venv" goto :VENV_EXISTS
echo [+] Criando ambiente virtual (.venv)...
%PY_CMD% -m venv .venv
if %errorlevel% neq 0 goto :ERRO_VENV
goto :VENV_DONE

:VENV_EXISTS
echo [i] Ambiente virtual ja existe.

:VENV_DONE
:: 4. Ativa e instala dependencias
echo [+] Ativando ambiente e instalando bibliotecas...
call .venv\Scripts\activate.bat

echo [+] Atualizando PIP...
python -m pip install --upgrade pip

if not exist "requirements.txt" goto :NO_REQ
echo [+] Instalando dependencias do projeto...
pip install -r requirements.txt
goto :FIM

:NO_REQ
echo [AVISO] requirements.txt nao encontrado. Instalando bibliotecas base...
pip install pandas openpyxl reportlab
goto :FIM

:ERRO_VENV
echo [ERRO] Falha ao criar a venv. Tente rodar como Administrador.
pause
exit /b

:FIM
echo ==========================================
echo      INSTALACAO CONCLUIDA COM SUCESSO
echo ==========================================
pause