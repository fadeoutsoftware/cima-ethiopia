#!/bin/bash -e
cd $CONDA_PATH 
cd bin 
source activate shybox_base_libraries
cd /app/shybox/workflow/runner
export PYTHONPATH="${PYTHONPATH}:/app/shybox"


# pip install --no-cache-dir \
#     numpy==1.23.5 pandas matplotlib \
#     notebook==6.5.6 \
#     jupyterlab==3.6.6 \
#     jupyter_core==5.5.0 \
#     jupyter_client==7.4.9 \
#     xarray netCDF4 tqdm \
#     ipywidgets folium scipy \
#     tabulate \
#     pyresample \
#     repurpose \
#     grass-session 
    

# 32.19   - saga-python
# 32.19   - grass
# 32.19   - grass-session
# 32.19   - saga
# conda config --add channels conda-forge
#conda install csdms-stack::grass


##saga saga-python 
# conda install saga-python
# conda install gdal geopandas rasterio rioxarray shapely fiona pyproj

jupyter nbextension install --py widgetsnbextension --sys-prefix \
 && jupyter nbextension enable --py widgetsnbextension --sys-prefix