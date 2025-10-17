### ETHIOPIA - CIMA - HMC Trainings
Repository to create a portable docker environment to be used during trainings hel by CIMA's staff in Ethiopia.

### Project structure 
[TODO]


## Useful commands 

Launch build from the /docker folder:
```
cd docker
docker build . -t cima-trainings
```

Execute the jupyter lab 
```
docker run -p 8888:8888 --volume ./data:/home/continuumuser/workdir cima-trainings
```


