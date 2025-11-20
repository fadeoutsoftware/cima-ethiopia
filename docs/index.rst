Cima Etiopia User Guide
===========================================

The following documentation reports all the 

Software setup
---------------------------------------------
Before starting the training a setup is required in order to have the correct tools.
In particular the software required are :

- A recent web browser 
- Docker
- WSL, in case the host machine has Windows installed


To install Docker you can follows official instruction from docker website:
- Docker for windows 
- Docker for Linux 

Loading Runtime for the training
----------------------------------------------

Check setup
_____________________________________________
Please open a terminal and check docker installation dy raising the following command::
    
    docker status

If the setup is correct you should obtain some details like::
    
    Client:
        Version:           28.4.0
        API version:       1.51
        Go version:        go1.24.7
        Git commit:        d8eb465
        Built:             Wed Sep  3 20:59:40 2025
        OS/Arch:           windows/amd64
        Context:           desktop-linux

        Server: Docker Desktop 4.46.0 (204649)
        Engine:
        Version:          28.4.0
        API version:      1.51 (minimum version 1.24)
        Go version:       go1.24.7
        Git commit:       249d679
        Built:            Wed Sep  3 20:57:37 2025
        OS/Arch:          linux/amd64
        Experimental:     false
        containerd:
        Version:          1.7.27
        GitCommit:        05044ec0a9a75232cad458027ca83437aae3f4da
        runc:
        Version:          1.2.5
        GitCommit:        v1.2.5-0-g59923ef
        docker-init:
        Version:          0.19.0
        GitCommit:        de40ad0

Load the runtime environment
__________________________________________
The instructor has provided all students a tar archive, containing the runtime setup 
for the exercise.
To load such assets please raise the following command::

    docker load -i hmc-training.tar

after the process is complete you should see the following message ::
    
    Loaded image: cima-aircs/hmc-trainig:dev

In order to check the actual loading use the following command::

    docker image ls

From the list you should see now a new image named **cima-aircs/hmc-trainig**

Start the container
____________________________________________
To start the training you can now raise the following command::

    docker run --name hmc-training -d -p 8888:8888 \
     --volume ./data:/home/continuumuser/workdir/data \
    --volume ./workspace:/home/continuumuser/workdir/workspace \
    cima-aircs/hmc-trainig:dev


Open a web browser and navigate to http://localhost:[port]

You should now see a notebook python served by the container:

[IMG NB Python ]

The setup is up and running, keep attention high and enjoy the training! 

_______________________

Troubleshooting
---------------------------------------

Something something dark side
_________________________________


Something something darker side
_________________________________
