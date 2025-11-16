#!/usr/bin/env python3
"""
geo_tools.py

Utility functions for geographic operations

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.0.0
Date: 2025-08-07
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.0.0"
__date__ = "2025-08-07"

import math
from rasterio.enums import Resampling
import rasterio
from affine import Affine

def km2deg(km, radius=6371):
    """
    Convert distance from kilometers to degrees on a sphere.

    Args:
        km (float): Distance in kilometers.
        radius (float): Radius of the sphere (default is Earth's average radius in km).

    Returns:
        float: Distance in degrees.
    """
    return km / (2.0 * radius * math.pi / 360.0)


def deg2km(degrees, radius=6371):
    """
    Convert distance from degrees to kilometers on a sphere.

    Args:
        degrees (float): Angular distance in degrees.
        radius (float): Radius of the sphere (default is Earth's average radius in km).

    Returns:
        float: Distance in kilometers.
    """
    return degrees * (2.0 * radius * math.pi / 360.0)


def resample(out: str, inp: str, target_res_deg: float):
    """
    Resample a raster to a new resolution in degrees using cubic interpolation.

    Args:
        out (str): Path to the output raster file.
        inp (str): Path to the input raster file.
        target_res_deg (float): Target spatial resolution in degrees.

    Returns:
        tuple: (output file path, updated raster profile)
    """
    with rasterio.open(inp) as src:
        # Calculate new dimensions based on target resolution
        new_w = int(src.width * src.res[0] / target_res_deg)
        new_h = int(src.height * src.res[1] / target_res_deg)

        # Read data with resampling
        data = src.read(
            out_shape=(src.count, new_h, new_w),
            resampling=Resampling.cubic
        )

        # Create a new affine transform for the target resolution
        transform = Affine(
            target_res_deg, 0, src.bounds.left,
            0, -target_res_deg, src.bounds.top
        )

        # Copy and update the metadata profile
        prof = src.profile.copy()
        prof.update(
            transform=transform,
            width=new_w,
            height=new_h,
            compress='DEFLATE'
        )

        # Write the resampled raster to the output file
        with rasterio.open(out, 'w', **prof) as dst:
            dst.write(data)

    return out, prof




from osgeo import gdal, gdalconst

def rasterize_vector_to_model(
    vector_path, out_raster_path, model_srs,
    burn_value=1, dst_nodata=0, assumed_src_epsg="EPSG:4326"
):
    """
    Rasterize a vector (SHP/GPKG/GeoJSON) onto the DEM grid (same bbox/size/SRS).
    - If the vector has no SRS, assume `assumed_src_epsg` (default: EPSG:4326).
    - Produces a single-band GeoTIFF (uint8) with 1 on features and 0 elsewhere.
    Args:
        vector_path (str): input vector path
        out_raster_path (str): output GeoTIFF path
        model_srs (dict): {proj, geotrans, wide, high, bbox}
        burn_value (int): value to burn on features
        dst_nodata (int): nodata value for output (default 0)
        assumed_src_epsg (str): fallback SRS if missing
    """
    # Open vector
    src_vec = gdal.OpenEx(vector_path, gdal.OF_VECTOR)
    if src_vec is None:
        raise RuntimeError(f"Cannot open vector: {vector_path}")

    # Read/assign SRS
    lyr = src_vec.GetLayer(0)
    src_srs = lyr.GetSpatialRef()
    if src_srs is None:
        tmp_assigned = out_raster_path + ".vec_assigned.gpkg"
        gdal.VectorTranslate(
            tmp_assigned, src_vec,
            dstSRS=assumed_src_epsg,
            options=gdal.VectorTranslateOptions(reproject=True, layerName="layer")
        )
        src_vec = gdal.OpenEx(tmp_assigned, gdal.OF_VECTOR)

    # Reproject to model SRS
    tmp_vec = out_raster_path + ".vec_reproj.gpkg"
    gdal.VectorTranslate(
        tmp_vec, src_vec,
        dstSRS=model_srs["proj"],
        options=gdal.VectorTranslateOptions(reproject=True, layerName="layer")
    )

    # Create target raster
    xmin, xmax, ymin, ymax = model_srs["bbox"]
    gt    = model_srs["geotrans"]
    wide  = model_srs["wide"]
    high  = model_srs["high"]

    drv = gdal.GetDriverByName("GTiff")
    dst = drv.Create(
        out_raster_path, wide, high, 1,
        gdalconst.GDT_Byte,
        options=["TILED=YES", "COMPRESS=DEFLATE"]
    )
    dst.SetGeoTransform(gt)
    dst.SetProjection(model_srs["proj"])
    band = dst.GetRasterBand(1)
    band.Fill(dst_nodata)
    band.SetNoDataValue(dst_nodata)

    # Rasterize (burn=1 on features)
    vec_ds = gdal.OpenEx(tmp_vec, gdal.OF_VECTOR)
    gdal.Rasterize(dst, vec_ds, burnValues=[burn_value])

    band = None
    dst = None

from osgeo import osr

ASSUMED_SRC_EPSG = "EPSG:4326"  # per AAIGrid senza .prj

def ensure_wkt(srs_str: str, fallback_epsg=ASSUMED_SRC_EPSG) -> str:
    """Ritorna sempre WKT valido: se vuoto o EPSG:XXXX converte a WKT."""
    if not srs_str or not srs_str.strip():
        return epsg_to_wkt(fallback_epsg)
    if srs_str.upper().startswith("EPSG:"):
        return epsg_to_wkt(srs_str)
    return srs_str

def ds_extent(ds):
    """(xmin,ymin,xmax,ymax) in SRS del dataset."""
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    x0, y0 = gt[0], gt[3]
    x1 = x0 + w*gt[1] + h*gt[2]
    y1 = y0 + w*gt[4] + h*gt[5]
    xmin, xmax = (x0, x1) if x0 <= x1 else (x1, x0)
    ymin, ymax = (y1, y0) if y1 <= y0 else (y0, y1)
    return xmin, ymin, xmax, ymax

def transform_bbox(bbox, src_wkt, dst_wkt):
    """Trasforma bbox (xmin,ymin,xmax,ymax) da src→dst usando OSR (trasforma i 4 angoli)."""
    s = osr.SpatialReference(); s.ImportFromWkt(src_wkt)
    d = osr.SpatialReference(); d.ImportFromWkt(dst_wkt)
    tx = osr.CoordinateTransformation(s, d)
    xmin, ymin, xmax, ymax = bbox
    pts = [(xmin,ymin),(xmin,ymax),(xmax,ymin),(xmax,ymax)]
    t = [tx.TransformPoint(x,y) for (x,y) in pts]
    xs = [p[0] for p in t]; ys = [p[1] for p in t]
    return (min(xs), min(ys), max(xs), max(ys))

def bboxes_intersect(a, b):
    axmin, aymin, axmax, aymax = a
    bxmin, bymin, bxmax, bymax = b
    return not (axmax < bxmin or bxmax < axmin or aymax < bymin or bymax < aymin)

def regrid_to_model(src_path, dst_path, model_srs,
                    resample_alg=gdalconst.GRA_Bilinear,
                    assumed_src_epsg="EPSG:4326",
                    dst_nodata=-9999.0):
    """
    Regrid via gdal.Warp: bbox/size/SRS del DEM.
    Forza srcSRS (se manca .prj) e imposta src/dst nodata.
    """
    src_ds = gdal.Open(src_path, gdalconst.GA_ReadOnly)
    if src_ds is None:
        raise RuntimeError(f"Cannot open {src_path}")

    # Recupera o assume il SRS
    src_wkt = src_ds.GetProjection()
    if not src_wkt or not src_wkt.strip():
        src_wkt = epsg_to_wkt(assumed_src_epsg)

    # NoData di input
    src_nodata = src_ds.GetRasterBand(1).GetNoDataValue()
    if src_nodata is None:
        src_nodata = -9999.0

    # Bounds corretti dal model_srs
    lon_min, lon_max, lat_min, lat_max = model_srs["bbox"]

    # Opzioni warp
    opts = gdal.WarpOptions(
        format="GTiff",
        outputBounds=(lon_min, lat_min, lon_max, lat_max),  # ordine corretto
        width=model_srs["wide"],
        height=model_srs["high"],
        dstSRS=model_srs["proj"],
        srcSRS=src_wkt,
        srcNodata=src_nodata,
        dstNodata=dst_nodata,
        resampleAlg=resample_alg,
        multithread=True
    )

    # Warp diretto: sovrascrive se già esiste
    gdal.Warp(dst_path, src_ds, options=opts)

    # Imposta NoData nel file di output
    ds = gdal.Open(dst_path, gdalconst.GA_Update)
    ds.GetRasterBand(1).SetNoDataValue(dst_nodata)
    ds = None
