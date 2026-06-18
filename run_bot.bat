@echo off
setlocal EnableExtensions
cd /d C:\Users\Administrator\Desktop\BLACKSHEEP

if not exist logs mkdir logs

set "LOG=logs\runner.log"
set "ERR=logs\runner.err.log"
set "ENVLOG=logs\runner.env.log"

set "TG_SESSION_FILE=C:\Users\Administrator\Desktop\BLACKSHEEP\tg_mt5_session"
set "TG_SESSION_DB=%TG_SESSION_FILE%.session"

echo ==== START %date% %time% ====>>"%LOG%"
echo ==== START %date% %time% ====>>"%ERR%"

echo USERNAME=%USERNAME%>"%ENVLOG%"
echo USERPROFILE=%USERPROFILE%>>"%ENVLOG%"
echo CD=%CD%>>"%ENVLOG%"
echo PATH=%PATH%>>"%ENVLOG%"
echo TG_SESSION_FILE=%TG_SESSION_FILE%>>"%ENVLOG%"
echo TG_SESSION_DB=%TG_SESSION_DB%>>"%ENVLOG%"

if exist "%TG_SESSION_DB%" (
  echo SESSION_FILE_EXISTS=1>>"%ENVLOG%"
) else (
  echo SESSION_FILE_EXISTS=0>>"%ENVLOG%"
)

where python >>"%ENVLOG%" 2>&1
where C:\Users\Administrator\Desktop\BLACKSHEEP\.venv\Scripts\python.exe >>"%ENVLOG%" 2>&1
C:\Users\Administrator\Desktop\BLACKSHEEP\.venv\Scripts\python.exe -V >>"%ENVLOG%" 2>&1

C:\Users\Administrator\Desktop\BLACKSHEEP\.venv\Scripts\python.exe app.py >>"%LOG%" 2>>"%ERR%"
set "RC=%ERRORLEVEL%"

echo EXIT_CODE=%RC% %date% %time%>>"%LOG%"
echo EXIT_CODE=%RC% %date% %time%>>"%ERR%"

exit /b %RC%
