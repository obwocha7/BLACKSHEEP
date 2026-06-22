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
C:\Users\Administrator\Desktop\BLACKSHEEP\.venv\Scripts\python.exe -V >>"%ENVLOG%" 2>&1

set "PORT_PID="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
  set "PORT_PID=%%a"
  goto :found_port_pid
)

:found_port_pid
if defined PORT_PID (
  echo PRECHECK_PORT_8080_LISTENER_PID=%PORT_PID%>>"%ENVLOG%"
  tasklist /FI "PID eq %PORT_PID%" | findstr /I "python.exe" >nul
  if not errorlevel 1 (
    echo PRECHECK_ACTION=KILL_EXISTING_8080_PID_%PORT_PID%>>"%ENVLOG%"
    taskkill /PID %PORT_PID% /F >>"%LOG%" 2>>"%ERR%"
    timeout /t 2 /nobreak >nul
  ) else (
    echo PRECHECK_ACTION=ABORT_NON_PYTHON_LISTENER_PID_%PORT_PID%>>"%ENVLOG%"
    echo ABORT: Port 8080 is occupied by non-python process PID %PORT_PID%.>>"%ERR%"
    exit /b 20
  )
) else (
  echo PRECHECK_PORT_8080_LISTENER_PID=NONE>>"%ENVLOG%"
)

set "POSTCHECK_PID="
for /f "tokens=5" %%b in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
  set "POSTCHECK_PID=%%b"
  goto :found_postcheck_pid
)

:found_postcheck_pid
if defined POSTCHECK_PID (
  echo POSTCHECK_ACTION=ABORT_PORT_STILL_OCCUPIED_PID_%POSTCHECK_PID%>>"%ENVLOG%"
  echo ABORT: Port 8080 still occupied after precheck PID cleanup. PID %POSTCHECK_PID%.>>"%ERR%"
  exit /b 21
)

C:\Users\Administrator\Desktop\BLACKSHEEP\.venv\Scripts\python.exe app.py >>"%LOG%" 2>>"%ERR%"
set "RC=%ERRORLEVEL%"

echo EXIT_CODE=%RC% %date% %time%>>"%LOG%"
echo EXIT_CODE=%RC% %date% %time%>>"%ERR%"

exit /b %RC%
