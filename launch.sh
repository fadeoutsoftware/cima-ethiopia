cp -r ./notebook/*.ipynb ./data/notebook/

docker run -d -p 8888:8888 --volume ./data:/home/continuumuser/workdir cima-aircs/hmc-trainig:dev