@echo off
chcp 65001 >nul
title Painel do Trader

rem  Abre o Painel do Trader no seu computador, sem depender da internet
rem  para funcionar (so para buscar os dados).
rem
rem  E so dar DOIS CLIQUES neste arquivo.
rem
rem  O que ele faz, nesta ordem:
rem    1. busca os dados do dia nas fontes publicas
rem    2. liga o painel no seu computador
rem    3. abre o navegador
rem
rem  Para fechar o painel: feche esta janela preta.

cd /d "%~dp0"

echo.
echo   ================================================
echo     PAINEL DO TRADER
echo   ================================================
echo.

rem --- Procura o Python ---
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

if not defined PY (
  echo   [X] Nao encontrei o Python neste computador.
  echo.
  echo   O Python e o programa que busca os dados. Instale em:
  echo     https://www.python.org/downloads/
  echo.
  echo   Na tela de instalacao, MARQUE a caixa
  echo   "Add Python to PATH" antes de clicar em Install.
  echo.
  pause
  exit /b 1
)

rem --- Passo 1: buscar os dados ---
echo   [1/3] Buscando os dados do dia...
echo.
pushd pipeline
%PY% atualizar.py
set "ERRO=%ERRORLEVEL%"
popd
echo.

if not "%ERRO%"=="0" (
  echo   [!] Alguma fonte nao respondeu.
  echo       O painel vai abrir com os ultimos dados validos,
  echo       e a tela avisa a data de cada numero.
  echo.
)

rem --- Passo 2 e 3: ligar o painel e abrir o navegador ---
echo   [2/3] Ligando o painel...
echo   [3/3] Abrindo o navegador...
echo.
echo   ------------------------------------------------
echo     Painel aberto em:  http://localhost:8787
echo.
echo     Para FECHAR o painel, feche esta janela.
echo   ------------------------------------------------
echo.

start "" http://localhost:8787
%PY% pipeline\servidor.py 8787

rem Se o servidor cair sozinho, a janela nao some antes de voce ler o erro.
echo.
echo   O painel foi encerrado.
pause
