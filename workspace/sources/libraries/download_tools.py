import cdsapi
import tempfile
import xarray as xr
import rioxarray as rxr
import os
from functools import partial
import datetime as dt
import requests

# these are the names that match those in Andrea's script
ERA5_continuum_variables = {
        "10m_u_component_of_wind"          : "Ux"  ,
        "10m_v_component_of_wind"          : "Vy"  ,
        "2m_dewpoint_temperature"          : "Tdew",
        "2m_temperature"                   : "T"   ,
        "total_precipitation"              : "P"   ,
        "surface_solar_radiation_downwards": "R"   ,
    }

def download_era5_data(year, bbox = [90,-180,-90,180], output = '{var}_{year}.nc', ncores = 1, **kwargs):
    """
    Download ERA5 data useful to run the model Continuum (TM) for a given year and bounding box.
    Parameters
    ----------
    year : int
        Year of the data to download.
    bbox : list of float, optional
        Bounding box in the format [North, West, South, East]. Default is global.
    output : str, optional
        Output file pattern where {var} will be replaced by variable names and {year} by the year. Default is '{var}_{year}.nc'.
    ncores : int, optional
        Number of parallel downloads to perform. Default is 1.
    **kwargs :
        Additional keyword arguments to pass to cdsapi.Client (e.g., key, quiet).
    """

    if ncores > len(ERA5_continuum_variables):
        ncores = len(ERA5_continuum_variables)

    if ncores > 1:
        from multiprocessing import Pool
        with Pool(ncores) as p:
            inputs  = [(var, year, bbox, output.format(var = name, year = year)) for var, name in ERA5_continuum_variables.items()]
            func = partial(download_era5_variable, **kwargs)
            p.starmap(func, inputs)
    else:
        for var, name in ERA5_continuum_variables.items():
            download_era5_variable(var, year, bbox, output.format(variable=name, year=year), **kwargs)

def get_era5_variable(variable, year, bbox = [90,-180,-90,180], **kwargs):
    """
    Download a single ERA5 variable useful to run the model Continuum (TM) for a given year and bounding box.
    Parameters
    ----------
    variable : str
        Variable name to download. Must be one of the ERA5_continuum_variables.
    year : int
        Year of the data to download.
    bbox : list of float, optional
        Bounding box in the format [North, West, South, East]. Default is global.
    **kwargs :
        Additional keyword arguments to pass to cdsapi.Client (e.g., key, quiet).

    Returns:
    -------
    xr.DataArray
        The downloaded variable as an xarray DataArray.
        With dimensions time, latitude, longitude.
    """

    if variable not in ERA5_continuum_variables:
        raise ValueError(f"Variable '{variable}' is not in the list of ERA5_continuum_variables: {ERA5_continuum_variables}")

    url = 'https://cds.climate.copernicus.eu/api'
    c = cdsapi.Client(url = url, **kwargs)
    dataset = "reanalysis-era5-single-levels"

    request = {
            'product_type': 'reanalysis',
            'data_format': 'netcdf',
            "download_format": "unarchived",
            'variable': variable,
            'year': str(year),
            'day': [f'{d:02d}' for d in range(1, 32)],
            'time': [f'{h:02d}:00' for h in range(0, 24)],
            'area': bbox,  # North, West, South, East. Default: global
    }
    
    groups = {
    	'1' : ['01', '02', '03', '04'],
    	'2' : ['05', '06', '07', '08'],
    	'3' : ['09', '10', '11', '12']
    }
    	

    # retrieve the file to a temporary folder
    with tempfile.TemporaryDirectory() as tmpdirname:
        all_files = []
        for g,m in groups.items():
            this_request = request.copy()
            this_request['month'] = m
            filepath = f'{tmpdirname}/{variable}_{year}-{g}_data.nc'
            #print(request)
            c.retrieve(dataset, this_request).download(filepath)
            all_files.append(filepath)

        for i, filepath in enumerate(all_files):
            # open the data as a xarray DataArray
            raw_data = xr.open_dataarray(filepath, engine = 'h5netcdf')

            # create a new DataArray with dimensions time, latitude, longitude
            var_da = xr.DataArray(
                raw_data.values,
                coords={
                    'time': raw_data['valid_time'].values,
                    'latitude': raw_data['latitude'].values,
                    'longitude': raw_data['longitude'].values,
                },
                dims=['time', 'latitude', 'longitude'],
                name=raw_data.name,
                attrs={'long_name' : raw_data.attrs.get('long_name'),
                    'units' : raw_data.attrs.get('units')}
            )
            if i == 0:
                data = var_da
            else:
                data = xr.concat([data, var_da], dim='time')
            raw_data.close()

        return data

def download_era5_variable(variable, year, bbox = [90,-180,-90,180], output = '{variable}_{year}.nc', **kwargs):
    """
    Download a single ERA5 variable useful to run the model Continuum (TM) for a given year and bounding box.
    Parameters
    ----------
    variable : str
        Variable name to download. Must be one of the ERA5_continuum_variables.
    year : int
        Year of the data to download.
    bbox : list of float, optional
        Bounding box in the format [North, West, South, East]. Default is global.
    output : str, optional
        Output file pattern where {variable} will be replaced by variable name and {year} by the year. Default is '{variable}_{year}.nc'.
    **kwargs :
        Additional keyword arguments to pass to cdsapi.Client (e.g., key, quiet).
    """

    var_da = get_era5_variable(variable, year, bbox = bbox, **kwargs)
    # save each variable to its own file
    outfile_name = output.format(variable = variable, year = year)
    if len(os.path.dirname(outfile_name)) > 0:
        os.makedirs(os.path.dirname(outfile_name), exist_ok=True)
    var_da.to_netcdf(outfile_name, engine = 'h5netcdf')
    print(f"Saved {variable} data to {outfile_name}")

def download_chirps_data(year, bbox = [90,-180,-90,180], output = 'Pchirps_{year}{month:02d}{day:02d}.tiff'):
    """
    Download CHIRPS precipitation data for a given year and bounding box.
    Parameters
    ----------
    year : int
        Year of the data to download.
    bbox : list of float, optional
        Bounding box in the format [North, West, South, East]. Default is global.
    output : str, optional
        Output file pattern where {year}, {month}, and {day} will be replaced by the year, month, and day.
        Default is 'CHIRPS_{year}{month:02d}{day:02d}.tif'.
    """
    url = 'https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/{year}/chirps-v3.0.rnl.{year}.{month:02d}.{day:02d}.tif'
    # loop over all days in the year
    date = dt.date(year, 1, 1)
    while date.year == year:
        # format the url
        url = url.format(year=year, month=date.month, day=date.day)
        response = requests.get(url)
        # download the file
        if response.status_code == 200:
            with tempfile.TemporaryDirectory() as tmpdirname:
                temp_filepath = os.path.join(tmpdirname, f'chirps_{year}_{date.month:02d}_{date.day:02d}.tif')
                with open(temp_filepath, 'wb') as f:
                    f.write(response.content)
                
                # open the data as a xarray DataArray
                raw_data = rxr.open_rasterio(temp_filepath)
                # subset the data to the bounding box
                subset_data = raw_data.rio.clip_box(*(bbox[1:] + bbox[:1]))  # West, South, East, North

                # ensure the data is straight-up
                subset_data = subset_data.sortby('y', ascending=False)

                #set nans
                subset_data = subset_data.where(subset_data >= 0, other = float('nan'))
                subset_data.attrs['_FillValue'] = float('nan')

                # set crs and coordinates
                subset_data = subset_data.rio.write_crs("EPSG:4326")
                subset_data = subset_data.rio.set_spatial_dims(x_dim="x", y_dim="y")

                # set attributes
                subset_data.name = 'CHIRPS_daily_precipitation'
                subset_data.attrs['long_name'] = 'CHIRPS Daily Precipitation'
                subset_data.attrs['units'] = 'mm/day'

                # save the subset data to the output file
                filepath = output.format(year=year, month=date.month, day=date.day)
                if len(os.path.dirname(filepath)) > 0:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                subset_data.rio.to_raster(filepath, compress='LZW')
                print(f"Saved CHIRPS data to {filepath}")
        else:
            print(f"CHIRPS data for {date} not found at {url}")
        
        # move to the next day
        date += dt.timedelta(days=1)

if __name__ == '__main__':
    #bbox_ethiopia = [16.00, 31.45, 2.00, 50.50]  # North, West, South, East
    bbox_test = [15.00, 41.45, 13.00, 44.50]  # North, West, South, East
    
    output_era5 = 'output/ERA5/{year}/TEST_{var}_{year}.nc'
    download_era5_data(2022, bbox=bbox_test, output=output_era5, ncores=3, key = '5baf738b-e18d-4702-8556-894362cf20ac')

    output_chirps = 'output/CHIRPS/{year}/{month:02d}/CHIRPS-precip1d_TEST_{year}{month:02d}{day:02d}.tif'
    download_chirps_data(2020, bbox=bbox_test, output=output_chirps)
