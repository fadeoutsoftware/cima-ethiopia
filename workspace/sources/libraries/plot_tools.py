#!/usr/bin/env python3
"""
plot_tools.py

Utility functions for plotting operations

Author: Andrea Libertino (andrea.libertino@cimafoundation.org)
Version: 1.0.1
Date: 2025-11-04
License: EUPL
"""

__author__ = "Andrea Libertino"
__email__ = "andrea.libertino@cimafoundation.org"
__version__ = "1.0.0"
__date__ = "2025-08-07"

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from IPython.display import display

def single_plot(map, title, figsize=(7, 5), cmap='viridis', force_stretch=True):
    """
    Displays a 2D array using matplotlib, with safe handling for boolean arrays.

    Args:
        map (ndarray): 2D array to display (can be bool, int, float).
        title (str): Plot title.
        figsize (tuple): Figure size.
        cmap (str): Colormap.
        force_stretch (bool): If True, allows aspect ratio to stretch.

    Returns:
        matplotlib.figure.Figure: The figure object.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title)

    # Convert bool to int so matplotlib doesn't crash on vmin/vmax
    display_data = map.astype(int) if map.dtype == bool else map

    im = ax.imshow(display_data, cmap=cmap)

    unique_vals = np.unique(display_data[~np.isnan(display_data)])

    if len(unique_vals) > 2:
        fig.colorbar(im, ax=ax)
    else:
        # Dummy colorbar to maintain consistent layout and avoid notebook glitch
        cax = fig.add_axes([0.85, 0.2, 0.01, 0.3])
        cb = fig.colorbar(im, cax=cax)
        cb.ax.set_visible(False)

    if force_stretch:
        ax.set_aspect('auto')

    ax.axis('off')
    
    plt.show()


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def locked_plot(
    arr1, arr2,
    title1="Array 1", title2="Array 2",
    cmap1='terrain', cmap2='viridis',
    figsize=(11, 5),
    share_palette=False,
    hide_axes=True,
    logscale1=False, logscale2=False
):
    """
    Displays two side-by-side plots of 2D arrays with optional log scaling and separate colorbars.

    Args:
        arr1, arr2: 2D arrays to display
        logscale1, logscale2 (bool): enable logarithmic scale per array
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, sharex=True, sharey=True)

    data1 = arr1.astype(int) if arr1.dtype == bool else arr1
    data2 = arr2.astype(int) if arr2.dtype == bool else arr2

    # sanitize for logscale
    if logscale1:
        data1 = np.where(data1 <= 0, np.nan, data1)
    if logscale2:
        data2 = np.where(data2 <= 0, np.nan, data2)

    # color limits and norms
    if share_palette:
        vmin = np.nanmin([data1, data2])
        vmax = np.nanmax([data1, data2])
        norm1 = LogNorm(vmin=vmin, vmax=vmax) if logscale1 else None
        norm2 = LogNorm(vmin=vmin, vmax=vmax) if logscale2 else None
    else:
        vmin1, vmax1 = np.nanmin(data1), np.nanmax(data1)
        vmin2, vmax2 = np.nanmin(data2), np.nanmax(data2)
        norm1 = LogNorm(vmin=vmin1, vmax=vmax1) if logscale1 else None
        norm2 = LogNorm(vmin=vmin2, vmax=vmax2) if logscale2 else None

    # draw first plot + colorbar
    im1 = ax1.imshow(data1, cmap=cmap1, norm=norm1,
                     vmin=None if logscale1 else (vmin if share_palette else vmin1),
                     vmax=None if logscale1 else (vmax if share_palette else vmax1))
    ax1.set_title(title1)
    cax1 = fig.add_axes([0.08, 0.08, 0.35, 0.03])
    fig.colorbar(im1, cax=cax1, orientation='horizontal')

    # draw second plot + colorbar
    im2 = ax2.imshow(data2, cmap=cmap2, norm=norm2,
                     vmin=None if logscale2 else (vmin if share_palette else vmin2),
                     vmax=None if logscale2 else (vmax if share_palette else vmax2))
    ax2.set_title(title2)
    cax2 = fig.add_axes([0.57, 0.08, 0.35, 0.03])
    fig.colorbar(im2, cax=cax2, orientation='horizontal')

    # optionally hide axes
    if hide_axes:
        for ax in (ax1, ax2):
            ax.axis('off')

    plt.subplots_adjust(wspace=0.1, bottom=0.2)
    plt.show()


def add_d8_legend(ax, data, cmap_name="viridis", title="Drainage Directions", ncol=4, pad=0.25):
    """
    Adds a discrete D8-direction legend to a matplotlib axis.

    Args:
        ax (matplotlib.axes.Axes): The target axis.
        data (ndarray): 2D array with D8 flow directions (1-9, excluding 5).
        cmap_name (str, optional): Name of base colormap. Defaults to 'viridis'.
        title (str, optional): Plot title. Defaults to 'Drainage Directions'.
        ncol (int, optional): Number of columns in the legend. Defaults to 4.
        pad (float, optional): Padding under the plot for the legend. Defaults to 0.25.
    """
    fig = ax.figure

    # Remove any previous colorbars/legends attached to the figure
    for extra in fig.axes[1:]:
        fig.delaxes(extra)

    # Build discrete colormap with 9 values
    base = plt.get_cmap(cmap_name, 9)
    cmap = mcolors.ListedColormap(base(np.arange(9)))
    bounds = np.arange(1, 11)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    # Redraw the image on the axis
    ax.clear()
    im = ax.imshow(data.astype(int), cmap=cmap, norm=norm)
    ax.set_title(ax.get_title() or title)
    ax.axis("off")

    # D8 direction code mapping
    code_dirs = {
        1: "↙", 2: "↓", 3: "↘", 4: "←",
        6: "→", 7: "↖", 8: "↑", 9: "↗"
    }

    # Build legend entries (skip code 5 if not used)
    handles = [
        mpatches.Patch(color=cmap(norm(code)), label=f"{code} {arrow}")
        for code, arrow in code_dirs.items()
    ]

    # Add legend below the plot
    ax.legend(
        handles=handles,
        loc="lower center",
        ncol=ncol,
        bbox_to_anchor=(0.5, -pad),
    )

    fig.canvas.draw()

