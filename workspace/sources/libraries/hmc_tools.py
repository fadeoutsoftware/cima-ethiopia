#!/usr/bin/env python3
"""
hmc_tools.py

Utility functions for managing Hydrological Model Continuum preprocessing

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.0.1
Date: 2025-09-08
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.0.2"
__date__ = "2025-11-21"

import os
import rasterio as rio
import numpy as np
import math
from copy import deepcopy

def writeHMC2Grass(ancillary_path):
    """
    Writes a conversion file used by the HMC model to map HMC flow directions
    to GRASS's format.

    Args:
        ancillary_path (str): Directory where the conversion file will be saved.
    """
    file_path = os.path.join(ancillary_path, "cont2grass.txt")
    with open(file_path, "w") as f:
        lines = [
            "7 = 3\n", "8 = 2\n", "9 = 1\n", "4 = 4\n",
            "6 = 8\n", "1 = 5\n", "2 = 6\n", "3 = 7\n", "*=NULL"
        ]
        f.writelines(lines)
        
def writeGrass2HMC(ancillary_path):
    """
    Writes a conversion file used by the HMC model to map GRASS flow directions
    to HMC's format.

    Args:
        ancillary_path (str): Directory where the conversion file will be saved.
    """
    file_path = os.path.join(ancillary_path, "grass2cont.txt")
    with open(file_path, "w") as f:
        lines = [
            "1 -1=9\n", "2 -2=8\n", "3 -3=7\n", "4 -4=4\n",
            "5 -5=1\n", "6 -6=2\n", "7 -7=3\n", "8 -8=6\n", "*=-9999"
        ]
        f.writelines(lines)

def makeAlphaBeta(basePath, ancillaryPath, domain):
    """
    Compute alpha and beta slope parameters for the Continuum HMC model.

    Alpha = local slope angle (flow direction weighted).
    Beta  = smoothed slope angle for channel cells.

    Args:
        basePath (str): Path to folder with hydrological inputs (.dem.txt, .pnt.txt, etc).
        ancillaryPath (str): Path to write temporary alpha/beta rasters.
        domain (str): Domain name prefix for input files.
    """
    import os, math
    import numpy as np
    import rasterio as rio
    from copy import deepcopy

    print("1/3 Computing alpha ...", flush=True)

    # --- Input raster datasets ---
    Dem_in     = rio.open(os.path.join(basePath, f"{domain}.dem.txt"))
    iPun       = rio.open(os.path.join(basePath, f"{domain}.pnt.txt"))
    iChoice    = rio.open(os.path.join(basePath, f"{domain}.choice.txt"))
    AreaCell   = rio.open(os.path.join(basePath, f"{domain}.areacell.txt"))

    # --- Output paths ---
    a2dAlphaMap = os.path.join(ancillaryPath, "temp_alpha.tif")
    a2dBetaMap  = os.path.join(ancillaryPath, "temp_beta.tif")

    # --- Read and flip arrays (GRASS outputs are upside-down) ---
    a2dDem      = np.flipud(Dem_in.read(1))
    a2iPun      = np.flipud(iPun.read(1))
    a2iChoice   = np.flipud(iChoice.read(1))
    a2dAreaCell = np.flipud(AreaCell.read(1))

    # Mask DEM where pointers are invalid
    a2dDem[a2iPun == -9999] = -9999

    # --- Initialize matrices ---
    shape    = a2dDem.shape
    iRows, iCols = shape
    diff_DD  = np.full(shape, -9999.0)
    LDD      = np.zeros(shape, dtype=float)
    pend     = np.zeros(shape, dtype=float)
    a2dAlpha = np.full(shape, -9999.0)
    a2dBeta  = np.full(shape, -9999.0)

    # --- Average cell resolution (meters) ---
    dDxM = float(np.sqrt(np.nanmean(a2dAreaCell)))
    dDyM = dDxM

    # --- Maximum path length threshold (meters) ---
    dDistanceT = 500
    if 100 <= dDxM < 1000:
        dDistanceT = 2000
    elif 5000 <= dDxM < 20000:
        dDistanceT = 30000

    # --- DEM corrections (avoid negatives except nodata) ---
    a2dDem[(a2dDem <= 0) & (a2dDem > -1000)] = 0.2

    # --- Elevation difference threshold (meters) ---
    DD = 50

    # -------------------------
    # MAIN LOOP: Compute alpha
    # -------------------------
    for i in range(iRows):
        for j in range(iCols):
            a, b = i, j
            if a2dDem[a, b] <= 0:
                continue

            fNumPen = 0  # slope averaging counter

            while a2dDem[a, b] > 0 and diff_DD[a, b] == -9999:
                # Get downstream cell from pointer
                iii = a + (int((a2iPun[a, b] - 1) / 3) - 1)
                jjj = b + a2iPun[a, b] - 5 - 3 * (int((a2iPun[a, b] - 1) / 3) - 1)
                if iii < 0 or jjj < 0 or iii >= iRows or jjj >= iCols:
                    break

                # Initial segment
                LDD[a, b]    = math.sqrt(((a - iii) * dDyM)**2 + ((b - jjj) * dDxM)**2)
                diff_DD[a, b]= a2dDem[a, b] - a2dDem[iii, jjj]

                slope = math.atan2(diff_DD[a, b], LDD[a, b])
                if slope > 0 and diff_DD[a, b] < 9000:
                    fNumPen += 1
                    pend[a, b] += slope

                # Follow path while thresholds are respected
                while (
                    a2dDem[a, b] - a2dDem[iii, jjj] <= DD and
                    0 <= iii < iRows-1 and 0 <= jjj < iCols-1 and
                    a2dDem[iii, jjj] > 0 and
                    LDD[a, b] < dDistanceT
                ):
                    ii = iii + (int((a2iPun[iii, jjj] - 1) / 3) - 1)
                    jj = jjj + a2iPun[iii, jjj] - 5 - 3 * (int((a2iPun[iii, jjj] - 1) / 3) - 1)
                    if 0 <= ii < iRows and 0 <= jj < iCols and a2dDem[a, b] - a2dDem[ii, jj] <= DD:
                        LDD[a, b] += math.sqrt(((ii - iii) * dDyM)**2 + ((jj - jjj) * dDxM)**2)
                        slope = math.atan2(diff_DD[a, b], LDD[a, b])
                        if slope > 0 and diff_DD[a, b] < 9000:
                            if a2iChoice[a, b] == 1 or (a2iChoice[a, b] == 0 and LDD[a, b] < 500):
                                fNumPen += 1
                                pend[a, b] += slope
                    iii, jjj = ii, jj

                # ---- Final path extension (from old version) ----
                if diff_DD[a, b] != -9999:
                    while (
                        a2dDem[a, b] - a2dDem[iii, jjj] <= DD and
                        0 <= iii < iRows-1 and 0 <= jjj < iCols-1 and
                        a2dDem[iii, jjj] > 0 and
                        LDD[a, b] < dDistanceT
                    ):
                        diff_DD[a, b] = a2dDem[a, b] - a2dDem[iii, jjj]
                        ii = iii + (int((a2iPun[iii, jjj] - 1) / 3) - 1)
                        jj = jjj + a2iPun[iii, jjj] - 5 - 3 * (int((a2iPun[iii, jjj] - 1) / 3) - 1)
                        if 0 <= ii < iRows and 0 <= jj < iCols and a2dDem[a, b] - a2dDem[ii, jj] <= DD:
                            LDD[a, b] += math.sqrt(((ii - iii) * dDyM)**2 + ((jj - jjj) * dDxM)**2)
                            slope = math.atan2(diff_DD[a, b], LDD[a, b])
                            if slope > 0 and diff_DD[a, b] < 9000:
                                if a2iChoice[a, b] == 1 or (a2iChoice[a, b] == 0 and LDD[a, b] < 500):
                                    fNumPen += 1
                                    pend[a, b] += slope
                        iii, jjj = ii, jj
                # -----------------------------------------------

                if fNumPen > 0:
                    pend[a, b] /= fNumPen

                # Apply special slope rules
                if diff_DD[a, b] == 0.9 or diff_DD[a, b] > 500:
                    diff_DD[a, b] = 0.9
                if diff_DD[a, b] < 1 and LDD[a, b] < 4 * dDxM:
                    LDD[a, b] = 4 * dDxM

                a2dAlpha[a, b] = math.atan2(diff_DD[a, b], LDD[a, b])

                # Move downstream
                ii = a + (int((a2iPun[a, b] - 1) / 3) - 1)
                jj = b + a2iPun[a, b] - 5 - 3 * (int((a2iPun[a, b] - 1) / 3) - 1)
                if 0 <= ii < iRows and 0 <= jj < iCols and a2dDem[ii, jj] >= 0:
                    a, b = ii, jj
                    fNumPen = 0
                else:
                    break

    print("2/3 Computing beta ...", flush=True)

    # ------------------------
    # Compute beta (smoothed)
    # ------------------------
    a2dBeta = deepcopy(pend)
    pend[a2iChoice < 1] = 0
    pend2 = deepcopy(pend)
    pend.fill(0)

    for i in range(1, iRows-1):
        for j in range(1, iCols-1):
            if a2iChoice[i, j] == 1:
                fn = 0
                for ii in range(i-1, i+2):
                    for jj in range(j-1, j+2):
                        if pend2[ii, jj] > 0:
                            fn += 1
                            pend[i, j] += pend2[ii, jj]
                pend[i, j] /= (fn or 1)

                if LDD[i, j] <= 4 * dDxM and diff_DD[i, j] < 2:
                    pend[i, j] = a2dAlpha[i, j]

                if pend[i, j] > 0:
                    a2dAlpha[i, j] = pend[i, j]
                    a2dBeta[i, j]  = pend[i, j]

    dBmin = max(0.0001, np.min(pend[pend > 0]))
    a2dBeta  = np.where((a2dDem > 0) & (a2dBeta == 0), a2dAlpha, a2dBeta)
    a2dBeta  = np.where((a2dDem > 0) & (a2dBeta < dBmin), dBmin, a2dBeta)
    a2dAlpha = np.where((a2dDem > 0) & (a2dAlpha < 0.0001), 0.0001, a2dAlpha)
    a2dBeta[a2dAlpha == -9999] = -9999

    print("3/3 Writing alpha and beta ...", flush=True)

    # --- Save rasters ---
    profile = Dem_in.profile
    profile.update(driver="GTiff", count=1)
    with rio.open(a2dBetaMap, "w", **profile) as dst:
        dst.write(np.flipud(a2dBeta.astype("float32")), 1)
    with rio.open(a2dAlphaMap, "w", **profile) as dst:
        dst.write(np.flipud(a2dAlpha.astype("float32")), 1)