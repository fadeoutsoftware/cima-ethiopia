# root image, base on LTS ubuntu
FROM ubuntu:24.04 AS builder

# image labels
# TODO


ARG DEBIAN_FRONTEND=noninteractive


# Setting required environment variables
ENV \
    # set geographical area
    TZ=Europe/Rome \
    # UID of the non-root user 'app'
    APP_UID=1456 \
	# set environment folder(s)
	ENTRYPOINT_DIR=/app/entrypoint/ \
	LIBS_INSTALLER_DIR=/app/library/libs_installer/ \
	LIBS_SYSTEM_DIR=/app/library/libs_system/ \
	#
	# TODO check this
	#
	PACKAGE_HMC_DIR=/app/library/package_hmc/ \ 	
	# set environment filename(s)
	SYSTEM_ENV_FILE=fp_env_system \
	#
	# TODO check if belows ae fine for the converter
	#
	# prepare share folder(s) to mount external repositories
	INPUT_DIR=/app/mnt_in/ \
	OUTPUT_DIR=/app/mnt_out/ \
	INPUT_STATIC_DIR=/app/mnt_in/data_static/ \
	INPUT_DYNAMIC_DIR=/app/mnt_in/data_dynamic/ \
	INPUT_MODEL_RESTART_DIR=/app/mnt_in/model_restart/ \
	OUTPUT_MODEL_RESULTS_DIR=/app/mnt_out/model_results/ \
	OUTPUT_MODEL_STATE_DIR=/app/mnt_out/model_state/

# install system-wide deps 
RUN apt-get update && apt-get install -y \
	git \
	gfortran \
	gcc \
	m4 \
	g++ \
	make \
	mc \
	curl \
	build-essential \
	wget \
	cmake \
	libcurl4-openssl-dev \
	tzdata \
	openjdk-8-jdk \
	bash-completion

# Create a non-root user and group
RUN groupadd \
        --gid=$APP_UID \
        app \
    && useradd -l \
        --uid=$APP_UID \
        --gid=$APP_UID \
        --create-home \
        app  


# activate the application user
WORKDIR /app
RUN chown -R app:app /app
USER app

# create the required folders
RUN mkdir -p ${LIBS_INSTALLER_DIR} \
	&& mkdir -p ${PACKAGE_HMC_DIR} \
	&& mkdir -p ${ENTRYPOINT_DIR} \
	&& mkdir -p ${INPUT_DIR} \
	&& mkdir -p ${OUTPUT_DIR} \
	&& mkdir -p ${INPUT_STATIC_DIR} \
	&& mkdir -p ${INPUT_DYNAMIC_DIR} \
	&& mkdir -p ${INPUT_MODEL_RESTART_DIR} \
	&& mkdir -p ${OUTPUT_MODEL_RESULTS_DIR} \
	&& mkdir -p ${OUTPUT_MODEL_STATE_DIR}



# change default shell (from sh to bash)
SHELL ["/bin/bash", "-c"]


# TODO check if HMC is the right one

# TODO check branches, always replaced with master

# -----------------------------------------------------------------
# INSTALL - DOCKER SYSTEM LIBRARIES
# clone library from github repository
RUN git clone https://github.com/c-hydro/fp-system-library.git --branch main --single-branch /tmp/libs_system/
# copy files from tmp to container folder(s)
RUN cp -r /tmp/libs_system/. ${LIBS_INSTALLER_DIR} 
# start installer script for system libraries
WORKDIR ${LIBS_INSTALLER_DIR}
RUN pwd
RUN ./setup_fp_system_library_hmc.sh ${LIBS_SYSTEM_DIR} ${SYSTEM_ENV_FILE}
# -----------------------------------------------------------------


# -----------------------------------------------------------------
# INSTALL - DOCKER SYSTEM APPS
# clone library from github repository
RUN git clone https://github.com/c-hydro/fp-system-app.git --branch main --single-branch /tmp/app_system/
# copy files from tmp to container folder(s)
RUN cp -rf /tmp/app_system/. ${LIBS_INSTALLER_DIR} 

# start installer script for hmc libraries
WORKDIR ${LIBS_INSTALLER_DIR}
RUN pwd
RUN ./setup_fp_system_app_hmc.sh ${LIBS_SYSTEM_DIR} ${SYSTEM_ENV_FILE} ${PACKAGE_HMC_DIR}

### TODO ADD similar call in the S3M docker image generation

# -----------------------------------------------------------------



# -----------------------------------------------------------------
# Runtime stage

FROM ubuntu:24.04

# Setting required environment variables  [TODO check if needed in multi-layer build]
ENV \
    # set geographical area
    TZ=Europe/Rome \
    # UID of the non-root user 'app'
    APP_UID=1456 \
	# set environment folder(s)
	ENTRYPOINT_DIR=/app/entrypoint/ \
	LIBS_INSTALLER_DIR=/app/library/libs_installer/ \
	LIBS_SYSTEM_DIR=/app/library/libs_system/ \
	#
	# TODO check this
	#
	# Match on PATH_EXEC on new version 
	PACKAGE_HMC_DIR=/app/library/package_hmc/ \ 	
	# set environment filename(s)
	SYSTEM_ENV_FILE=fp_env_system \
	# prepare share folder(s) to mount external repositories
	INPUT_DIR=/app/mnt_in/ \
	OUTPUT_DIR=/app/mnt_out/ \
	INPUT_STATIC_DIR=/app/mnt_in/data_static/ \
	INPUT_DYNAMIC_DIR=/app/mnt_in/data_dynamic/ \
	INPUT_MODEL_RESTART_DIR=/app/mnt_in/model_restart/ \
	OUTPUT_MODEL_RESULTS_DIR=/app/mnt_out/model_results/ \
	OUTPUT_MODEL_STATE_DIR=/app/mnt_out/model_state/

# install system-wide deps  <-> added to try to solve missing dependecies 
# on startup of HMC_Model_V3_\$RUN.x 
# Missing libgfortran.so.5: cannot open shared object file: No such file or directory 
# Solved with apt install apt-get install libgfortran5
# Missing
RUN apt-get update && apt-get install -y \
	git \
	gfortran \
	gcc \
	m4 \
	g++ \
	make \
	mc \
	curl \
	build-essential \
	wget \
	cmake \
	libcurl4-openssl-dev \
	tzdata \
	openjdk-8-jdk \
	bash-completion \ 
    python3 python3-dev python3-pip python3.12-venv\
    git build-essential curl nano wget unzip \
	grass grass-dev grass-doc \
    gdal-bin python3-gdal \
    libgdal-dev python3-gi


# Create a non-root user and group
RUN groupadd \
	--gid=$APP_UID \
	app \
	&& useradd -l \
	--uid=$APP_UID \
	--gid=$APP_UID \
	--create-home \
	app  

# activate the application user
WORKDIR /app
RUN chown -R app:app /app
USER app

# create the required folders
RUN mkdir -p ${LIBS_INSTALLER_DIR} \
	&& mkdir -p ${PACKAGE_HMC_DIR} \
	&& mkdir -p ${ENTRYPOINT_DIR} \
	&& mkdir -p ${INPUT_DIR} \
	&& mkdir -p ${OUTPUT_DIR} \
	&& mkdir -p ${INPUT_STATIC_DIR} \
	&& mkdir -p ${INPUT_DYNAMIC_DIR} \
	&& mkdir -p ${INPUT_MODEL_RESTART_DIR} \
	&& mkdir -p ${OUTPUT_MODEL_RESULTS_DIR} \
	&& mkdir -p ${OUTPUT_MODEL_STATE_DIR} \
	&& mkdir -p /app/shybox \
	&& mkdir -p /app/exec



# change default shell (from sh to bash)
#SHELL ["/bin/bash", "-c"]


COPY --from=builder ${LIBS_SYSTEM_DIR} ${LIBS_SYSTEM_DIR}
COPY --from=builder ${PACKAGE_HMC_DIR} ${PACKAGE_HMC_DIR}
COPY --from=builder ${ENTRYPOINT_DIR} ${ENTRYPOINT_DIR} 

#Required for point netcdf libs
ENV LD_LIBRARY_PATH="/app/library/libs_system:/app/library/libs_system/source/nc4_fortran/fortran/.libs/"

# set environmental variable(s) appending in .bashrc
RUN echo "source ${LIBS_SYSTEM_DIR}/${SYSTEM_ENV_FILE}" >> /home/app/.bashrc


# set environmental variable(s) appending in .profile
RUN echo "source ${LIBS_SYSTEM_DIR}/${SYSTEM_ENV_FILE}" >> /home/app/.profile

### New repository SHYBOX

WORKDIR /app/shybox
RUN git clone https://github.com/c-hydro/shybox.git --branch itwater --single-branch /app/shybox/

COPY requirements_aics_iwrm.txt /app/shybox
COPY requirements.sh /app/shybox

RUN /app/shybox/requirements.sh

USER root
RUN useradd -ms /bin/bash --gid=app \
		continuumuser

# ----------------------------------------
# 5) As root: create GRASS location, loosen perms, install addons
# ----------------------------------------


# 5a) Create the WGS84 location
RUN mkdir -p /home/continuumuser/grassdata \
 && grass -c EPSG:4326 /home/continuumuser/grassdata/WGS84 \
      --exec echo "GRASS WGS84 created"

RUN chown -R continuumuser:app /home/continuumuser/grassdata
RUN chmod -R a+rwx /home/continuumuser/grassdata/WGS84/PERMANENT
USER continuumuser
ENV HOME=/home/continuumuser

# 5c) Compile & install the two addons
RUN grass --text /home/continuumuser/grassdata/WGS84/PERMANENT \
      --exec g.extension extension=r.stream.basins operation=add \
        --quiet \
 && grass --text /home/continuumuser/grassdata/WGS84/PERMANENT \
      --exec g.extension extension=r.accumulate operation=add \
     --quiet

#ENV PATH="/usr/lib/grass78/bin:${PATH}"
 
# 5d) Restore ownership and tighten perms again
#RUN chown -R continuumuser:continuumuser /home/continuumuser/grassdata \
# && rm -rf /root/.grass7/addons \
# && chmod -R go-w /home/continuumuser/grassdata/WGS84/PERMANENT

# ----------------------------------------
# 6) Switch back to non-root
# ----------------------------------------
USER continuumuser

# ----------------------------------------
# 7) Set up your workspace and PYTHONPATH
# ----------------------------------------
WORKDIR /home/continuumuser/workdir
ENV PYTHONPATH=/home/continuumuser/workdir/sources/libraries:${PYTHONPATH}


# ----------------------------------------
# 8) Expose Jupyter port & default command
# ----------------------------------------
#EXPOSE 8888
COPY launcher.sh /home/continuumuser
ENTRYPOINT ["/home/continuumuser/launcher.sh"]

