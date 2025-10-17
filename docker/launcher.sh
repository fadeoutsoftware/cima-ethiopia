#!/bin/bash -e
cd $CONDA_PATH 
cd bin 
source activate shybox_base_libraries

export PYTHONPATH="${PYTHONPATH}:/app/shybox"

#export PROJ_LIB=/usr/share/proj

cd /home/continuumuser/workdir

jupyter notebook \
     --ip=0.0.0.0 \
     --port=8888 \
     --no-browser \
     --NotebookApp.token='' \
     --NotebookApp.notebook_dir=/home/continuumuser/workdir