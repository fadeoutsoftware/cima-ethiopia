#!/bin/bash -e
cd $CONDA_PATH 
cd bin 
source activate shybox_base_libraries
cd /app/shybox/workflow/runner
export PYTHONPATH="${PYTHONPATH}:/app/shybox"


pip install --no-cache-dir \
    numpy==1.23.5 pandas matplotlib \
    notebook==6.5.6 \
    jupyterlab==3.6.6 \
    jupyter_core==5.5.0 \
    jupyter_client==7.4.9 \
    xarray netCDF4 tqdm \
    grass-session rasterio \
    geopandas==0.13.2 shapely>=2.0 pyproj>=3.5 fiona==1.9.6 \
    ipywidgets folium scipy \
    tabulate \
    rioxarray \
    pyresample \
    repurpose

jupyter nbextension install --py widgetsnbextension --sys-prefix \
 && jupyter nbextension enable --py widgetsnbextension --sys-prefix