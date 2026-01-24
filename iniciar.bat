@echo off
:: Muda para o diretorio do projeto
cd /d "%~dp0"

echo Iniciando Sistema...

:: Verifica se a venv existe
if not exist ".venv" (
    echo ERRO: Pasta .venv nao encontrada!
    echo Execute o arquivo 'instalar.bat' primeiro.
    pause
    exit /b
)

:: Ativa a venv
call .venv\Scripts\activate

:: Executa o programa principal
python main.py

:: Se o programa fechar com erro, pausa para leitura
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro na execucao.
    pause
)