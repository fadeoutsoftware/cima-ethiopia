docker run --name hmc-training -d -p 8888:8888 \
 --volume ./data:/home/continuumuser/workdir/data \
 --volume ./workspace:/home/continuumuser/workdir/workspace \
 cima-aircs/hmc-trainig:dev
