
"""
postprocessing_tool.py

Utility functions for Continuum post-processing:
- load settings & build paths
- load hydrograph, sections, dams, MOWE data
- load grids, gridded files, and aggregate variables
- generic helpers (period restriction, FDC, spatial stats, OSM overlay)
- basic performance metrics (NSE, RMSE, relative bias, KGE)
"""

import os
import json
import gzip

import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import rioxarray as rxr
from rasterio.features import rasterize
import io


# -----------------------------------------------------------------------------
# SETTINGS & PATHS
# -----------------------------------------------------------------------------

def model_results_path(cfg: dict) -> str:
    """Base path for model results of this basin."""
    root = cfg["paths"]["model_results_root"]
    return os.path.join(root, cfg["basin"])


def static_geo_path(cfg: dict) -> str:
    """Base path for static geo data of this basin."""
    root = cfg["paths"]["static_geo_root"]
    return os.path.join(root, cfg["basin"])


def mowe_root_path(cfg: dict) -> str:
    """Root path for MOWE datasets."""
    return cfg["paths"]["mowe_root"]


# -----------------------------------------------------------------------------
# PERIOD
# -----------------------------------------------------------------------------

def restrict_to_period(df: pd.DataFrame, time_col: str, start, end) -> pd.DataFrame:
    """Return df filtered between start and end on time_col."""
    mask = (df[time_col] >= start) & (df[time_col] <= end)
    return df.loc[mask].copy()


# -----------------------------------------------------------------------------
# HYDROGRAPH & SECTIONS
# -----------------------------------------------------------------------------

def load_hydrograph(cfg: dict):
    """
    Load aggregated hydrograph:
    - first column = datetime
    - others      = sections
    """
    base = model_results_path(cfg)
    hydro_rel = cfg["model_output"]["hydrograph_file"]
    hydro_path = os.path.join(base, hydro_rel)

    if not os.path.exists(hydro_path):
        raise FileNotFoundError(f"Hydrograph file not found: {hydro_path}")

    df = pd.read_csv(hydro_path, delim_whitespace=True, header=None)
    df.rename(columns={0: "time"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"])

    return df, hydro_path


def load_info_section(cfg: dict):
    """Read info_section file: list of section names in order."""
    static_base = static_geo_path(cfg)
    info_rel = cfg["static_data"]["info_section_file"]
    info_path = os.path.join(static_base, info_rel)

    if not os.path.exists(info_path):
        raise FileNotFoundError(info_path)

    sections = []
    with open(info_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                sections.append(line)

    return sections, info_path


def load_mowe_stations(cfg: dict):
    """Read stations shapefile for observed discharge."""
    mowe_root = mowe_root_path(cfg)
    shp_rel = cfg["mowe"]["stations_shapefile"]
    shp_path = os.path.join(mowe_root, shp_rel)

    if not os.path.exists(shp_path):
        raise FileNotFoundError(shp_path)

    gdf = gpd.read_file(shp_path)
    return gdf, shp_path


def load_observed_discharge_for_section(cfg: dict, section_name: str):
    """
    Returns (obs_df, path). If CSV does not exist, obs_df is None.
    """
    mowe_root = mowe_root_path(cfg)
    series_dir = cfg["mowe"]["river_flow_series_dir"]
    template  = cfg["mowe"]["river_flow_filename_template"]
    date_col  = cfg["mowe"]["river_flow_date_column"]
    val_col   = cfg["mowe"]["river_flow_value_column"]

    filename = template.format(station_code=section_name)
    csv_path = os.path.join(mowe_root, series_dir, filename)

    if not os.path.exists(csv_path):
        return None, csv_path

    df = pd.read_csv(csv_path)
    df[date_col] = pd.to_datetime(df[date_col])
    df.rename(columns={date_col: "time", val_col: "obs"}, inplace=True)
    df = df[["time", "obs"]]
    return df, csv_path


# -----------------------------------------------------------------------------
# DAMS (info_dam + vdam)
# -----------------------------------------------------------------------------

def load_info_dam(cfg: dict):
    """Read info_dam: dams separated by ####, name in first line of each block."""
    static_base = static_geo_path(cfg)
    info_rel = cfg["static_data"]["info_dam_file"]
    info_path = os.path.join(static_base, info_rel)

    if not os.path.exists(info_path):
        return [], info_path

    dams = []
    current_name = None
    with open(info_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("####"):
                current_name = None
                continue
            if current_name is None:
                current_name = line
                dams.append(current_name)
    return dams, info_path


def load_vdam(cfg: dict):
    """Load vdam file: time + dam columns."""
    base = model_results_path(cfg)
    vdam_rel = cfg["model_output"].get("vdam_file", "hmc.vdam.txt")
    vdam_path = os.path.join(base, vdam_rel)

    if not os.path.exists(vdam_path):
        return None, vdam_path

    df = pd.read_csv(vdam_path, delim_whitespace=True, header=None)
    df.rename(columns={0: "time"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"])
    return df, vdam_path


# -----------------------------------------------------------------------------
# GRIDDED FILES & VARIABLES
# -----------------------------------------------------------------------------

def get_nc_var_name(cfg: dict, logical_name: str) -> str:
    """Map logical variable name to NetCDF variable name using cfg."""
    mo = cfg["model_output"]
    if logical_name == "Discharge":
        return mo["discharge_variable_name"]
    elif logical_name == "ET":
        return mo["et_variable_name"]
    elif logical_name == "SM":
        return mo["sm_variable_name"]
    else:
        return logical_name


def discover_gridded_files(cfg: dict) -> list:
    """Find all state-grid .nc.gz files for this basin."""
    base = model_results_path(cfg)
    gridded_rel = cfg["model_output"]["gridded_state_dir"]
    gridded_dir = os.path.join(base, gridded_rel)

    if not os.path.exists(gridded_dir):
        raise FileNotFoundError(gridded_dir)

    all_files = []
    for root, _, files in os.walk(gridded_dir):
        for f in files:
            if f.startswith("hmc.state-grid") and f.endswith(".nc.gz"):
                all_files.append(os.path.join(root, f))
    return sorted(all_files)


def open_single_nc_gz(path: str) -> xr.Dataset:
    """Open a single .nc.gz file as an xarray Dataset."""
    with gzip.open(path, "rb") as f:
        ds = xr.open_dataset(f)
    return ds


def collect_gridded_variable(cfg: dict, logical_name: str, files: list, tqdm=None) -> xr.DataArray:
    """Load a logical variable across all files and concat along time."""
    nc_name = get_nc_var_name(cfg, logical_name)

    iterator = files if tqdm is None else tqdm(files, desc=f"Loading {logical_name}")
    das = []
    for fpath in iterator:
        ds = open_single_nc_gz(fpath)
        if nc_name not in ds:
            raise KeyError(f"Variable '{nc_name}' not found in {fpath}")
        das.append(ds[nc_name])

    out = xr.concat(das, dim="time").sortby("time")
    return out


def aggregate_gridded(da: xr.DataArray, logical_name: str, scale: str,
                      start=None, end=None) -> xr.DataArray:
    """Aggregate in time (hourly / daily)."""
    if start is not None and end is not None:
        da = da.sel(time=slice(start, end))

    if scale == "hourly":
        return da

    if logical_name in ["Discharge", "SM"]:
        return da.resample(time="1D").mean()
    elif logical_name == "ET":
        return da.resample(time="1D").last()
    else:
        return da.resample(time="1D").mean()


# -----------------------------------------------------------------------------
# GRID LAT/LON & NEAREST CELL
# ----------------------------------------------------------------------------

def load_lat_lon_grids(cfg: dict):
    """Load lat/lon grids from static files."""
    static_base = static_geo_path(cfg)
    lat_rel = cfg["static_data"]["lat_file"]
    lon_rel = cfg["static_data"]["lon_file"]
    lat_path = os.path.join(static_base, lat_rel)
    lon_path = os.path.join(static_base, lon_rel)

    if not os.path.exists(lat_path):
        raise FileNotFoundError(lat_path)
    if not os.path.exists(lon_path):
        raise FileNotFoundError(lon_path)

    lat = np.loadtxt(lat_path)
    lon = np.loadtxt(lon_path)
    return lat, lon


def find_nearest_grid_cell(lat_grid: np.ndarray, lon_grid: np.ndarray,
                           lat_pt: float, lon_pt: float):
    """Return (iy, ix) of grid cell nearest to (lat_pt, lon_pt)."""
    dist2 = (lat_grid - lat_pt) ** 2 + (lon_grid - lon_pt) ** 2
    idx = np.unravel_index(np.argmin(dist2), lat_grid.shape)
    return idx


# -----------------------------------------------------------------------------
# SPATIAL STATS & MASKS & MAPS
# -----------------------------------------------------------------------------

def spatial_stat(da: xr.DataArray, mode: str = "mean") -> xr.DataArray:
    """Temporal aggregation along time -> 2D map."""
    if mode == "mean":
        return da.mean(dim="time")
    elif mode == "sum":
        return da.sum(dim="time")
    elif mode == "max":
        return da.max(dim="time")
    elif mode == "min":
        return da.min(dim="time")
    else:
        raise ValueError(mode)


def spatial_mean_timeseries(da: xr.DataArray) -> pd.DataFrame:
    """Domain-mean time series for a gridded variable."""
    ts = da.mean(dim=("y", "x")).to_pandas()
    df = ts.to_frame(name="mean_value").reset_index()
    df.rename(columns={"time": "time"}, inplace=True)
    return df


def mask_from_shapefile(da: xr.DataArray, shp_path: str,
                        burn_value: int = 1, fill_value: int = 0):
    """Create a mask DataArray (y,x) = 1 inside shapefile polygon(s)."""
    gdf = gpd.read_file(shp_path)
    if da.rio.crs is None:
        da = da.rio.write_crs("EPSG:4326")
    gdf = gdf.to_crs(da.rio.crs)

    transform = da.rio.transform()
    out_shape = (da.sizes["y"], da.sizes["x"])
    shapes = [(geom, burn_value) for geom in gdf.geometry]

    mask = rasterize(
        shapes,
        out_shape=out_shape,
        transform=transform,
        fill=fill_value,
        dtype="uint8"
    )

    return xr.DataArray(mask, dims=("y", "x"),
                        coords={"y": da["y"], "x": da["x"]})


def spatial_mean_timeseries_with_mask(da: xr.DataArray, mask_da: xr.DataArray) -> pd.DataFrame:
    """Masked domain mean time series for a gridded variable."""
    masked = da.where(mask_da == 1)
    ts = masked.mean(dim=("y", "x")).to_pandas()
    df = ts.to_frame(name="mean_value").reset_index()
    df.rename(columns={"time": "time"}, inplace=True)
    return df


def plot_spatial_map_folium(da2d: xr.DataArray, title: str = "Map"):
    """
    Convert a 2D DataArray to an image and overlay on OSM using folium.
    Returns a folium.Map object.
    """
    import folium

    if da2d.rio.crs is None:
        da2d = da2d.rio.write_crs("EPSG:4326")

    minx, miny, maxx, maxy = da2d.rio.bounds()

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(da2d.values, origin="upper")
    ax.axis("off")
    ax.set_title(title)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2],
                   zoom_start=7, tiles="OpenStreetMap")

    folium.raster_layers.ImageOverlay(
        image=buf,
        bounds=[[miny, minx], [maxy, maxx]],
        opacity=0.7,
        name=title
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# -----------------------------------------------------------------------------
# FLOW DURATION CURVE (FDC)
# -----------------------------------------------------------------------------

def compute_fdc(series: pd.Series) -> pd.DataFrame:
    """Flow Duration Curve for a discharge series."""
    s = series.dropna().values
    if s.size == 0:
        return pd.DataFrame(columns=["q", "p_exceed"])

    s_sorted = np.sort(s)[::-1]      # descending
    n = len(s_sorted)
    ranks = np.arange(1, n + 1)
    p_exceed = ranks / (n + 1) * 100.0

    return pd.DataFrame({"q": s_sorted, "p_exceed": p_exceed})


# -----------------------------------------------------------------------------
# PERFORMANCE METRICS (NSE, RMSE, bias, KGE)
# -----------------------------------------------------------------------------

def compute_metrics(sim: pd.Series, obs: pd.Series) -> dict:
    """
    Compute basic performance metrics between simulated and observed:
    - NSE (Nash-Sutcliffe)
    - RMSE
    - relative bias
    - KGE (Kling-Gupta Efficiency, 2009)
    """

    df = pd.DataFrame({"sim": sim, "obs": obs}).dropna()
    if len(df) < 2:
        return {"NSE": np.nan, "RMSE": np.nan, "Bias_rel": np.nan, "KGE": np.nan}

    s = df["sim"].values
    o = df["obs"].values

    rmse = np.sqrt(np.mean((s - o) ** 2))

    mean_o = np.mean(o)
    mean_s = np.mean(s)
    if mean_o != 0:
        bias_rel = (mean_s - mean_o) / mean_o
    else:
        bias_rel = np.nan

    denom = np.sum((o - mean_o) ** 2)
    if denom > 0:
        nse = 1.0 - np.sum((s - o) ** 2) / denom
    else:
        nse = np.nan

    if len(df) > 1:
        r = df["sim"].corr(df["obs"])
    else:
        r = np.nan

    std_s = np.std(s, ddof=1)
    std_o = np.std(o, ddof=1)
    alpha = std_s / std_o if std_o != 0 else np.nan
    beta = mean_s / mean_o if mean_o != 0 else np.nan

    if np.any(np.isnan([r, alpha, beta])):
        kge = np.nan
    else:
        kge = 1.0 - np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)

    return {
        "NSE": float(nse),
        "RMSE": float(rmse),
        "Bias_rel": float(bias_rel),
        "KGE": float(kge)
    }
