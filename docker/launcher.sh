#!/bin/bash -e
cd /app/shybox 
source .venv/bin/activate

export PYTHONPATH="${PYTHONPATH}:/app/shybox"

#export PROJ_LIB=/usr/share/proj

cd /home/continuumuser/workdir

jupyter notebook \
     --ip=0.0.0.0 \
     --port=8888 \
     --no-browser \
     --NotebookApp.token='' \
     --NotebookApp.notebook_dir=/home/continuumuser/workdir