# ETHIOPIA - CIMA - HMC Trainings
Repository to create a portable docker environment to be used during trainings held by CIMA's staff in Ethiopia.

# Project structure 
### Docker dir 
The directory contains a docker file and scripts to setup the docker environment.
### Data dir 
This directory, excluded from versioning, must contains the data passed by CIMA, the first archive shared.
DOCs can be dropped.

## Useful commands 

Launch build from the /docker folder:
```
cd docker
docker build . -t ethiopia
```

Execute the jupyter lab 
```
docker run -d -p 8888:8888 --volume ../data:/home/continuumuser/workdir ethiopia
```


