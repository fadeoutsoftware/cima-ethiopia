@echo off

docker run --name continuum-eth -d -p 8888:8888 --volume ./workspace:/home/continuumuser/workdir continuum-eth:latest

echo Waiting for Jupyter to launch....
timeout /t 3 >nul

echo Oben web browser...
start http://localhost:8888

echo Done!