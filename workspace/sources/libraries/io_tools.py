#!/usr/bin/env python3
"""
io_tools.py

Utility functions for basis I/O operations

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.0.0
Date: 2025-08-07
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.0.0"
__date__ = "2025-08-07"

import os
import subprocess
from osgeo import gdal, gdalconst


def convertAIIGrid(inFile, outFile, outType, precision=2):
    """
    Converts a raster file to AAIGrid (ASCII) format with optional precision and type settings.
    Removes intermediate files and fixes known no-data representation issues for Int16 grids.

    Args:
        inFile (str): Path to the input raster file.
        outFile (str): Path to the output ASCII grid (.txt).
        outType (str): Output data type (e.g., 'Int16', 'Float32').
        precision (int, optional): Decimal precision for float output (default is 2).

    Returns:
        str: Path to the converted ASCII grid file.
    """
    # Build gdal_translate command
    translate_cmd = [
        "gdal_translate",
        "-co", "FORCE_CELLSIZE=YES",
        "--config", "GDAL_PAM_ENABLED", "NO",
        "-q",
        "-co", f"DECIMAL_PRECISION={precision}",
        "-ot", outType,
        "-a_nodata", "-9999.0",
        "-of", "AAIGrid",
        inFile,
        outFile
    ]

    # Run conversion
    subprocess.run(translate_cmd, check=True)

    # Remove original input file
    if os.path.exists(inFile):
        os.remove(inFile)

    # Remove auxiliary files created by GDAL
    prj = outFile.replace('.txt', '.prj')
    auxxml = outFile + '.aux.xml'

    for f in [prj, auxxml]:
        if os.path.exists(f):
            os.remove(f)

    # Fix AAIGrid no-data values for Int16 (32768 → 9999)
    if outType == 'Int16':
        subprocess.run(["sed", "-i", "s/32768/9999/g", outFile], check=True)

    return outFile

def write_tif_from_grid(src_proj_wkt, model_srs, src_filename, dst_filename, resample_type, file_type=gdalconst.GDT_Float32):
    src = gdal.Open(src_filename, gdalconst.GA_ReadOnly)
    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, model_srs['wide'], model_srs['high'], 1, file_type)
    dst.SetGeoTransform(model_srs['geotrans'])
    dst.SetProjection(model_srs['proj'])
    gdal.ReprojectImage(src, dst, src_proj_wkt, model_srs['proj'], resample_type)

