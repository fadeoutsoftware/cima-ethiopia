@echo off

docker run --name continuum-eth -d -p 8888:8888 --volume ./workspace:/home/continuumuser/workdir continuum-eth:latest

echo Waiting for Jupyter to launch...

:wait_loop
timeout /t 5 /nobreak >nul
echo Checking Jupyter...

REM Try to request the homepage silently
curl http://localhost:8888 >nul 2>&1

IF ERRORLEVEL 1 (
    echo Not ready yet... waiting another 5 seconds.
    goto wait_loop
)

echo Jupyter is running!
echo Opening web browser...
start http://localhost:8888

echo Done!