#!/usr/bin/env python3
"""
forcing_tool.py

Utilities to generate hydrological forcing datasets from ERA5 (NetCDF)
and CHIRPS (GeoTIFF), including temporal subsetting, spatial cropping
to a bounding box, and basic downscaling of precipitation.

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.1.0
Date: 2025-11-22
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.1.0"
__date__ = "2025-11-22"

import os
import gc
import calendar
import logging
from glob import glob
from datetime import datetime

import numpy as np
import xarray as xr
import rioxarray as rxr

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------
logger = logging.getLogger(__name__)

if not logger.handlers:
    # Configurazione base: se il modulo è usato come script è comoda,
    # se è importato in un altro progetto, l'utente può sovrascriverla.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

NODATA_VALUE = -9999.0

# ----------------------------------------------------------------------
# HELPER FISICI
# ----------------------------------------------------------------------
def convert_J_to_W(da: xr.DataArray) -> xr.DataArray:
    """
    Convert energy flux from J/m^2 (per hour) to W/m^2.
    Assumes that the input is an hourly-accumulated energy flux (J/m^2).
    """
    return da / 3600.0


def calculate_rh(T_K: xr.DataArray, Tdew_K: xr.DataArray) -> xr.DataArray:
    """
    Compute relative humidity (%) from air temperature and dew-point temperature.
    Args:
        T_K (xr.DataArray): Air temperature in Kelvin.
        Tdew_K (xr.DataArray): Dew-point temperature in Kelvin.
    Returns:
        xr.DataArray: Relative humidity in %, clipped between 0 and 100.
    """
    T_C = T_K - 273.15
    Tdew_C = Tdew_K - 273.15

    es = 6.112 * np.exp((17.67 * T_C) / (T_C + 243.5))
    e = 6.112 * np.exp((17.67 * Tdew_C) / (Tdew_C + 243.5))
    rh = (e / es) * 100.0

    return np.clip(rh, 0.0, 100.0)


# ----------------------------------------------------------------------
# IO ERA5
# ----------------------------------------------------------------------
def load_era5_dataarray(file_path: str, new_var_name: str) -> xr.DataArray:
    """
    Load a single ERA5 NetCDF file as a DataArray, fix coordinates and variable name.
    - Opens the file as DataArray.
    - Renames the data variable to `new_var_name` if needed.
    - Renames coordinates to x (lon) and y (lat) for GIS compatibility.
    """
    try:
        logger.debug(f"Loading ERA5 file: {file_path}")
        da = xr.open_dataarray(file_path, engine="netcdf4", use_cftime=True, chunks={})

        # Ensure the variable has the desired name
        if da.name is None or da.name != new_var_name:
            da = da.rename(new_var_name)

        # Rename longitude to x
        if "longitude" in da.coords:
            da = da.rename({"longitude": "x"})
        elif "lon" in da.coords:
            da = da.rename({"lon": "x"})

        # Rename latitude to y
        if "latitude" in da.coords:
            da = da.rename({"latitude": "y"})
        elif "lat" in da.coords:
            da = da.rename({"lat": "y"})

        return da

    except Exception as exc:
        logger.error(f"Error loading {file_path}: {exc}")
        raise


def assign_raw_data(ds: xr.Dataset, da: xr.DataArray) -> xr.Dataset:
    """
    Assign a DataArray to a Dataset, bypassing alignment issues.
    Uses raw NumPy values to avoid dimension alignment problems;
    falls back to a nearest reindex if dimensions are mismatched.
    """
    var_name = da.name
    logger.debug(f"Assigning variable '{var_name}' to yearly dataset")

    if all(dim in ds.dims for dim in da.dims):
        ds[var_name] = (da.dims, da.values, da.attrs)
    else:
        logger.warning(
            "Dimension mismatch when assigning '%s', using reindex_like(nearest).",
            var_name,
        )
        ds[var_name] = da.reindex_like(ds, method="nearest")

    return ds


# ----------------------------------------------------------------------
# UTILITY TEMPORALI E SPAZIALI
# ----------------------------------------------------------------------
def _month_iter(start_dt: datetime, end_dt: datetime):
    """
    Yield (year, month) pairs between start_dt and end_dt (inclusive).
    """
    cur = datetime(start_dt.year, start_dt.month, 1)
    last = datetime(end_dt.year, end_dt.month, 1)

    while cur <= last:
        yield cur.year, cur.month

        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1)
        else:
            cur = datetime(cur.year, cur.month + 1, 1)


def crop_to_bbox(obj, bbox):
    """
    Crop a Dataset/DataArray to a given bounding box.
    The bounding box is specified as [xmin, ymin, xmax, ymax] in degrees
    (lon/lat) and must be fully contained within the dataset domain.
    """
    xmin, ymin, xmax, ymax = bbox

    if "x" not in obj.coords or "y" not in obj.coords:
        raise ValueError("Cannot apply bbox: 'x' and 'y' coordinates are required.")

    x = obj["x"]
    y = obj["y"]

    x_min = float(x.min().values)
    x_max = float(x.max().values)
    y_min = float(y.min().values)
    y_max = float(y.max().values)

    # Check that the bbox is fully contained in the domain
    if not (x_min <= xmin < xmax <= x_max):
        raise ValueError(
            f"x bbox [{xmin}, {xmax}] outside data domain [{x_min}, {x_max}]"
        )
    if not (y_min <= ymin < ymax <= y_max):
        raise ValueError(
            f"y bbox [{ymin}, {ymax}] outside data domain [{y_min}, {y_max}]"
        )

    # Latitude can be increasing (south→north) or decreasing (north→south)
    if y[0] < y[-1]:
        y_slice = slice(ymin, ymax)
    else:
        y_slice = slice(ymax, ymin)

    x_slice = slice(xmin, xmax)

    return obj.sel(x=x_slice, y=y_slice)


# ----------------------------------------------------------------------
# COMPUTO VARIABILI ERA5 (UNA ALLA VOLTA)
# ----------------------------------------------------------------------
def compute_temperature(ds_month: xr.Dataset) -> xr.DataArray:
    logger.info("    [T] Computing air temperature (degC)...")
    da = ds_month["T"] - 273.15
    da.name = "temperature"
    da.attrs.update(
        {
            "units": "degC",
            "long_name": "Air Temperature at 2m (degC)",
        }
    )
    return da


def compute_solar_radiation(ds_month: xr.Dataset) -> xr.DataArray:
    logger.info("    [R] Computing solar radiation (W/m^2)...")
    da = convert_J_to_W(ds_month["R"])
    da.name = "solar_radiation"
    da.attrs.update(
        {
            "units": "W/m^2",
            "long_name": "Surface Solar Radiation (W/m^2)",
        }
    )
    return da


def compute_wind(ds_month: xr.Dataset) -> xr.DataArray:
    logger.info("    [Ux,Vx] Computing wind speed (m/s)...")
    da = np.sqrt(ds_month["Ux"] ** 2 + ds_month["Vx"] ** 2)
    da.name = "m10_wind"
    da.attrs.update(
        {
            "units": "m/s",
            "long_name": "Wind Speed at 10m (m/s)",
        }
    )
    return da


def compute_relative_humidity(ds_month: xr.Dataset) -> xr.DataArray:
    logger.info("    [T,Tdew] Computing relative humidity (%)...")
    da = calculate_rh(ds_month["T"], ds_month["Tdew"])
    da.name = "relative_humidity"
    da.attrs.update(
        {
            "units": "%",
            "long_name": "Relative Humidity at 2m (%)",
        }
    )
    return da


# ----------------------------------------------------------------------
# FUNZIONE PRINCIPALE
# ----------------------------------------------------------------------
def convert_forcing(
    start_str,
    end_str,
    era5_T_template,
    era5_P_template,
    era5_R_template,
    era5_Ux_template,
    era5_Vx_template,
    era5_Tdew_template,
    chirps_pattern_template,
    output_dir_template,
    bbox=None,
    time_fmt="%d-%m-%Y %H:%M",
):
    """
    Generate hydrological forcings from ERA5 (NetCDF) and CHIRPS (GeoTIFF).

    This function:
      * Loads yearly ERA5 data from template file paths (at most one year in memory).
      * Subsets the requested time window at monthly resolution.
      * Optionally crops all data to a longitude/latitude bounding box.
      * Downscales precipitation from ERA5 to the CHIRPS grid using a
        simple daily-distribution approach.
      * Computes temperature, solar radiation, wind speed, and relative
        humidity on the native ERA5 grid (one variable group at a time).
      * Saves monthly NetCDF files for all variables.
    """
    start_dt = datetime.strptime(start_str, time_fmt)
    end_dt = datetime.strptime(end_str, time_fmt)

    if end_dt < start_dt:
        raise ValueError("end_str must be later than start_str.")

    logger.info("== Forcing conversion from %s to %s ==", start_dt, end_dt)

    # Cache yearly ERA5 datasets by year (max 1 in memoria)
    era5_cache = {}
    prev_year = None

    for year, month in _month_iter(start_dt, end_dt):
        month_year_str = f"{month:02d}{year}"
        logger.info(
            "\n================ %04d-%02d (tag %s) ================",
            year,
            month,
            month_year_str,
        )

        # ------------------------------------------------------------------
        # 0. PULIZIA CACHE ANNO PRECEDENTE (SE CAMBIA ANNO)
        # ------------------------------------------------------------------
        if prev_year is not None and year != prev_year and prev_year in era5_cache:
            logger.info("Releasing ERA5 yearly dataset for %d from cache", prev_year)
            try:
                era5_cache[prev_year].close()
            except Exception:
                # se non è un dataset "apribile", ignore
                pass
            del era5_cache[prev_year]
            gc.collect()

        # ------------------------------------------------------------------
        # 1. YEARLY ERA5 LOADING (WITH OPTIONAL BBOX CROPPING)
        # ------------------------------------------------------------------
        if year not in era5_cache:
            logger.info("Loading ERA5 yearly data for %d...", year)

            ref_dt_year = datetime(year, 1, 1)

            t_file = ref_dt_year.strftime(era5_T_template)
            p_file = ref_dt_year.strftime(era5_P_template)
            r_file = ref_dt_year.strftime(era5_R_template)
            ux_file = ref_dt_year.strftime(era5_Ux_template)
            vx_file = ref_dt_year.strftime(era5_Vx_template)
            tdew_file = ref_dt_year.strftime(era5_Tdew_template)

            logger.info("  ERA5 files:")
            logger.info("    T:     %s", t_file)
            logger.info("    P:     %s", p_file)
            logger.info("    R:     %s", r_file)
            logger.info("    Ux:    %s", ux_file)
            logger.info("    Vx:    %s", vx_file)
            logger.info("    Tdew:  %s", tdew_file)

            da_t = load_era5_dataarray(t_file, "T")
            da_r = load_era5_dataarray(r_file, "R")
            da_ux = load_era5_dataarray(ux_file, "Ux")
            da_vx = load_era5_dataarray(vx_file, "Vx")
            da_tdew = load_era5_dataarray(tdew_file, "Tdew")
            da_p = load_era5_dataarray(p_file, "P_ERA5")

            ds_year = da_t.to_dataset()
            ds_year = assign_raw_data(ds_year, da_r)
            ds_year = assign_raw_data(ds_year, da_ux)
            ds_year = assign_raw_data(ds_year, da_vx)
            ds_year = assign_raw_data(ds_year, da_tdew)
            ds_year = assign_raw_data(ds_year, da_p)

            logger.info(
                "  ERA5 yearly dataset dims: %s | coords: %s",
                ds_year.dims,
                list(ds_year.coords),
            )

            if bbox is not None:
                logger.info("  Applying bbox %s to ERA5 yearly dataset", bbox)
                ds_year = crop_to_bbox(ds_year, bbox)
                logger.info(
                    "  ERA5 yearly dataset after bbox dims: %s", ds_year.dims
                )

            era5_cache[year] = ds_year
            logger.info("ERA5 yearly dataset for %d loaded successfully.", year)

        ds_era5 = era5_cache[year]

        # ------------------------------------------------------------------
        # 2. TEMPORAL SUBSETTING AT MONTHLY SCALE
        # ------------------------------------------------------------------
        last_day = calendar.monthrange(year, month)[1]
        month_start = datetime(year, month, 1, 0, 0)
        month_end = datetime(year, month, last_day, 23, 59)

        effective_start = max(month_start, start_dt)
        effective_end = min(month_end, end_dt)

        if effective_end < effective_start:
            logger.info(
                "  >> Month %04d-%02d outside requested range (%s → %s), skipping.",
                year,
                month,
                start_dt,
                end_dt,
            )
            prev_year = year
            continue

        logger.info(
            "  Time window for this month: %s → %s",
            effective_start,
            effective_end,
        )

        # Use strings to keep compatibility with cftime
        eff_start_str = effective_start.strftime("%Y-%m-%d %H:%M")
        eff_end_str = effective_end.strftime("%Y-%m-%d %H:%M")

        ds_month = ds_era5.sel(time=slice(eff_start_str, eff_end_str))
        if "time" not in ds_month.dims or ds_month.time.size == 0:
            logger.warning(
                "  >> No ERA5 data for %04d-%02d in requested window, skipping.",
                year,
                month,
            )
            prev_year = year
            continue

        logger.info("  ERA5 monthly subset has %d timesteps.", ds_month.time.size)

        ref_dt_month = datetime(year, month, 1)
        output_dir = ref_dt_month.strftime(output_dir_template)
        os.makedirs(output_dir, exist_ok=True)
        logger.info("  Output directory: %s", output_dir)

        # ------------------------------------------------------------------
        # 3. CHIRPS PRECIPITATION AND DOWNSCALING
        # ------------------------------------------------------------------
        logger.info(
            "  [P] Processing Total Precipitation (downscaling to CHIRPS grid)..."
        )

        chirps_glob = ref_dt_month.strftime(chirps_pattern_template)
        chirps_files = sorted(glob(chirps_glob))
        logger.info("  Searching CHIRPS files with pattern: %s", chirps_glob)

        if not chirps_files:
            raise FileNotFoundError(f"No CHIRPS files found for pattern {chirps_glob}")

        logger.info("  Found %d CHIRPS files:", len(chirps_files))
        for fpath in chirps_files:
            logger.info("    - %s", os.path.basename(fpath))

        chirps_list = []
        for fpath in chirps_files:
            # Assumes date is in the last underscore-separated token before '.tif'
            date_str = os.path.basename(fpath).split("_")[-1].replace(".tif", "")
            time_val = datetime.strptime(date_str, "%Y%m%d")

            da = rxr.open_rasterio(fpath, masked=True).squeeze()
            if "band" in da.dims:
                da = da.sel(band=1).drop_vars("band")

            da = da.assign_coords(time=time_val)
            chirps_list.append(da)

        da_chirps_daily = xr.concat(chirps_list, dim="time")
        da_chirps_daily = da_chirps_daily.rename("total_precipitation")

        logger.info(
            "  CHIRPS daily stack shape: %s (time=%d)",
            da_chirps_daily.shape,
            da_chirps_daily.time.size,
        )

        if bbox is not None:
            logger.info("  Applying bbox %s to CHIRPS data", bbox)
            da_chirps_daily = crop_to_bbox(da_chirps_daily, bbox)
            logger.info(
                "  CHIRPS daily stack after bbox shape: %s", da_chirps_daily.shape
            )

        # CHIRPS target grid
        template_grid_chirps = da_chirps_daily.isel(time=0).drop_vars("time")
        template_grid_chirps = template_grid_chirps.rio.write_crs(
            template_grid_chirps.rio.crs
        )

        # ERA5 precipitation in mm (already cropped if bbox was provided)
        p_era5_mm = ds_month["P_ERA5"] * 1000.0
        p_era5_mm = p_era5_mm.rio.set_crs("EPSG:4326")

        logger.info("  Reprojecting ERA5 hourly P to CHIRPS grid...")
        p_era5_hourly_resampled = p_era5_mm.rio.reproject_match(template_grid_chirps)

        logger.info("  Computing daily sums and distribution factors...")
        p_era5_daily_sum_resampled = (
            p_era5_hourly_resampled.resample(time="1D")
            .sum(dim="time", keep_attrs=True)
            .reindex(time=p_era5_mm.time, method="pad")
        )

        distribution_factor = (
            p_era5_hourly_resampled / p_era5_daily_sum_resampled
        ).where(p_era5_daily_sum_resampled != 0, 1.0 / 24.0)
        distribution_factor.attrs = {}

        chirps_hourly_template = da_chirps_daily.reindex(
            time=p_era5_mm.time, method="pad"
        )
        chirps_hourly_template = chirps_hourly_template.rio.set_crs(
            template_grid_chirps.rio.crs
        )

        total_precipitation = chirps_hourly_template * distribution_factor
        total_precipitation.name = "total_precipitation"
        total_precipitation.attrs["units"] = "mm"
        total_precipitation.attrs["long_name"] = "Total Precipitation (mm)"

        logger.info("  Total Precipitation processing complete.")

        # ------------------------------------------------------------------
        # 4. ERA5 VARIABLES ON NATIVE GRID (UNA VARIABILE ALLA VOLTA)
        # ------------------------------------------------------------------
        logger.info("  Processing ERA5 variables on native grid (one by one)...")

        compute_funs = [
            compute_temperature,
            compute_solar_radiation,
            compute_wind,
            compute_relative_humidity,
        ]

        for compute_fun in compute_funs:
            da = compute_fun(ds_month)

            # Pulizia coordinate inutili
            if "spatial_ref" in da.coords:
                da = da.drop_vars("spatial_ref")

            da = da.astype("float32")
            da.attrs["_FillValue"] = NODATA_VALUE

            var_name = da.name
            out_file = os.path.join(output_dir, f"{var_name}_{month_year_str}.nc")

            ds_save = xr.Dataset({var_name: da})
            ds_save.attrs["title"] = f"IWRM Dataset - {var_name}"
            ds_save.attrs["history"] = f"Created on {datetime.now().isoformat()}"

            encoding = {
                var_name: {
                    "dtype": "float32",
                    "zlib": True,
                    "complevel": 4,
                }
            }

            logger.info(
                "  -> Saving %s on ERA5 grid to %s (shape=%s, time=%d)",
                var_name,
                out_file,
                da.shape,
                da.time.size,
            )
            ds_save.to_netcdf(out_file, encoding=encoding)

            # Rilascio esplicito riferimenti
            ds_save.close()
            del ds_save, da

        # ------------------------------------------------------------------
        # 5. NETCDF PRECIPITAZIONE SU GRIGLIA CHIRPS
        # ------------------------------------------------------------------
        da_precip = total_precipitation
        da_precip.name = "total_precipitation"

        if "band" in da_precip.coords:
            da_precip = da_precip.drop_vars("band")
        if "spatial_ref" in da_precip.coords:
            da_precip = da_precip.drop_vars("spatial_ref")

        da_precip = da_precip.astype("float32")
        da_precip.attrs["_FillValue"] = NODATA_VALUE
        da_precip.rio.write_nodata(NODATA_VALUE, inplace=True)

        da_precip.x.attrs.update(
            {
                "standard_name": "longitude",
                "long_name": "longitude",
                "units": "degrees_east",
                "axis": "X",
            }
        )
        da_precip.y.attrs.update(
            {
                "standard_name": "latitude",
                "long_name": "latitude",
                "units": "degrees_north",
                "axis": "Y",
            }
        )
        da_precip.time.attrs.update(
            {
                "standard_name": "time",
                "long_name": "time",
                "axis": "T",
            }
        )

        out_file_precip = os.path.join(
            output_dir, f"{da_precip.name}_{month_year_str}.nc"
        )

        ds_save_precip = da_precip.to_dataset()
        ds_save_precip.attrs[
            "title"
        ] = "IWRM Dataset - Total Precipitation (Downscaled)"
        ds_save_precip.attrs["history"] = f"Created on {datetime.now().isoformat()}"

        encoding_precip = {
            "total_precipitation": {
                "dtype": "float32",
                "zlib": True,
                "complevel": 4,
            }
        }

        logger.info(
            "  -> Saving %s on CHIRPS grid to %s (shape=%s, time=%d)",
            da_precip.name,
            out_file_precip,
            da_precip.shape,
            da_precip.time.size,
        )
        ds_save_precip.to_netcdf(out_file_precip, encoding=encoding_precip)

        ds_save_precip.close()
        del ds_save_precip, da_precip
        del (
            total_precipitation,
            chirps_hourly_template,
            distribution_factor,
            p_era5_daily_sum_resampled,
            p_era5_hourly_resampled,
            p_era5_mm,
            da_chirps_daily,
            chirps_list,
            template_grid_chirps,
        )

        # ------------------------------------------------------------------
        # 6. CLEANUP MENSILE
        # ------------------------------------------------------------------
        del ds_month
        gc.collect()
        logger.debug("  Garbage collection completed for this month.")

        logger.info("--- Finished %04d-%02d ---", year, month)
        prev_year = year

    # Pulizia finale cache
    logger.info("Releasing remaining ERA5 yearly datasets from cache...")
    for y in list(era5_cache.keys()):
        try:
            era5_cache[y].close()
        except Exception:
            pass
        del era5_cache[y]
    gc.collect()

    logger.info("ALL REQUESTED MONTHS COMPLETED")
