#!/usr/bin/env python3
"""
Surface Data Visualization Script for CLM5 Surface Data Files
==============================================================
This script reads a CLM5 surface data NetCDF file and creates comprehensive
visualizations for all variables, saving them as PDFs and generating an
HTML report for easy sharing and discussion.

Author: Generated for TSMP-PDAF preprocessing
Usage: python visualize_surfdata.py <surfdata_nc_file>
"""

import os
import sys
import base64
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from netCDF4 import Dataset

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False
    print("Warning: cartopy not available. Site location map will be skipped.")

# PFT/CFT names sourced from the official CLM5 documentation:
#   NATPFT (Table 2.2.1):  https://escomp.github.io/CTSM/release-clm5.0/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html#id15
#   CFT    (Table 2.26.1): https://escomp.github.io/CTSM/release-clm5.0/tech_note/Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html#id20
#
# At import time we try to parse those tables from the live HTML (stdlib only, 3-second
# timeout).  If the network is unavailable the hardcoded fallbacks below are used instead.

def _fetch_pft_names_from_docs():
    """Parse NATPFT and CFT name tables from the official CLM5 HTML documentation.

    Returns (natpft_dict, cft_dict), where each value is either a populated
    {int: str} dict or None when fetching/parsing failed.
    """
    import urllib.request
    from html.parser import HTMLParser

    _NATPFT_URL = (
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Ecosystem/CLM50_Tech_Note_Ecosystem.html"
    )
    _CFT_URL = (
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html"
    )

    class _TableParser(HTMLParser):
        """Collect cell text for every row inside a <table id="…">."""
        def __init__(self, table_id):
            super().__init__()
            self._target = table_id
            self._active = False
            self._in_cell = False
            self._cur_row = []
            self._cur_text = ""
            self.rows = []

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            if tag == "table" and d.get("id") == self._target:
                self._active = True
            if self._active:
                if tag == "tr":
                    self._cur_row = []
                elif tag in ("td", "th"):
                    self._in_cell = True
                    self._cur_text = ""

        def handle_endtag(self, tag):
            if not self._active:
                return
            if tag == "table":
                self._active = False
            elif tag == "tr":
                if self._cur_row:
                    self.rows.append(self._cur_row)
                self._cur_row = []
            elif tag in ("td", "th"):
                self._cur_row.append(self._cur_text.strip())
                self._in_cell = False

        def handle_data(self, data):
            if self._in_cell:
                self._cur_text += data

    def _parse(url, table_id):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None
        parser = _TableParser(table_id)
        parser.feed(html)
        result = {}
        for row in parser.rows:
            if len(row) < 2:
                continue
            try:
                result[int(row[0])] = row[1]
            except ValueError:
                pass  # skip header rows whose first cell is not an integer
        return result if result else None

    natpft = _parse(_NATPFT_URL, table_id="id15")
    cft    = _parse(_CFT_URL,    table_id="id20")
    return natpft, cft


# Hardcoded fallback — names transcribed from the official docs (see URLs above).
# PFT 9 is "Broadleaf evergreen shrub – temperate" (the "temperate" qualifier matters;
# a tropical broadleaf evergreen shrub is not represented in CLM5).
_NATPFT_FALLBACK = {
    0:  "Bare Ground",
    1:  "Needleleaf evergreen tree – temperate",
    2:  "Needleleaf evergreen tree – boreal",
    3:  "Needleleaf deciduous tree – boreal",
    4:  "Broadleaf evergreen tree – tropical",
    5:  "Broadleaf evergreen tree – temperate",
    6:  "Broadleaf deciduous tree – tropical",
    7:  "Broadleaf deciduous tree – temperate",
    8:  "Broadleaf deciduous tree – boreal",
    9:  "Broadleaf evergreen shrub – temperate",
    10: "Broadleaf deciduous shrub – temperate",
    11: "Broadleaf deciduous shrub – boreal",
    12: "C3 arctic grass",
    13: "C3 grass",
    14: "C4 grass",
}

_CFT_FALLBACK = {
    15: "C3 unmanaged rainfed crop",       16: "C3 unmanaged irrigated crop",
    17: "Temperate corn rainfed",           18: "Temperate corn irrigated",
    19: "Spring wheat rainfed",             20: "Spring wheat irrigated",
    21: "Winter wheat rainfed",             22: "Winter wheat irrigated",
    23: "Temperate soybean rainfed",        24: "Temperate soybean irrigated",
    25: "Barley rainfed",                   26: "Barley irrigated",
    27: "Winter barley rainfed",            28: "Winter barley irrigated",
    29: "Rye rainfed",                      30: "Rye irrigated",
    31: "Winter rye rainfed",               32: "Winter rye irrigated",
    33: "Cassava rainfed",                  34: "Cassava irrigated",
    35: "Citrus rainfed",                   36: "Citrus irrigated",
    37: "Cocoa rainfed",                    38: "Cocoa irrigated",
    39: "Coffee rainfed",                   40: "Coffee irrigated",
    41: "Cotton rainfed",                   42: "Cotton irrigated",
    43: "Datepalm rainfed",                 44: "Datepalm irrigated",
    45: "Foddergrass rainfed",              46: "Foddergrass irrigated",
    47: "Grapes rainfed",                   48: "Grapes irrigated",
    49: "Groundnuts rainfed",               50: "Groundnuts irrigated",
    51: "Millet rainfed",                   52: "Millet irrigated",
    53: "Oilpalm rainfed",                  54: "Oilpalm irrigated",
    55: "Potatoes rainfed",                 56: "Potatoes irrigated",
    57: "Pulses rainfed",                   58: "Pulses irrigated",
    59: "Rapeseed rainfed",                 60: "Rapeseed irrigated",
    61: "Rice rainfed",                     62: "Rice irrigated",
    63: "Sorghum rainfed",                  64: "Sorghum irrigated",
    65: "Sugarbeet rainfed",                66: "Sugarbeet irrigated",
    67: "Sugarcane rainfed",                68: "Sugarcane irrigated",
    69: "Sunflower rainfed",                70: "Sunflower irrigated",
    71: "Miscanthus rainfed",               72: "Miscanthus irrigated",
    73: "Switchgrass rainfed",              74: "Switchgrass irrigated",
    75: "Tropical corn rainfed",            76: "Tropical corn irrigated",
    77: "Tropical soybean rainfed",         78: "Tropical soybean irrigated",
}

_fetched_natpft, _fetched_cft = _fetch_pft_names_from_docs()
NATPFT_NAMES = _fetched_natpft if _fetched_natpft is not None else _NATPFT_FALLBACK
CFT_NAMES    = _fetched_cft    if _fetched_cft    is not None else _CFT_FALLBACK

URBAN_TYPES = ["Tall Building District (TBD)", "High Density (HD)", "Medium Density (MD)"]

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Soil layer depths (approximate centers in meters)
SOIL_DEPTHS = [0.01, 0.04, 0.09, 0.16, 0.26, 0.40, 0.59, 0.83, 1.14, 1.56]


def get_scalar_value(var):
    """Extract a scalar value from a potentially multi-dimensional variable."""
    data = var[:]
    if hasattr(data, 'mask'):
        data = np.ma.filled(data, np.nan)
    return float(np.squeeze(data))


def get_1d_array(var):
    """Extract a 1D array from a variable."""
    data = var[:]
    if hasattr(data, 'mask'):
        data = np.ma.filled(data, np.nan)
    return np.squeeze(data)


# =============================================================================
# Grid-type detection
# =============================================================================

def detect_grid_type(nc):
    """Return True if the file contains a regional (multi-cell) grid."""
    return nc.dimensions['lsmlat'].size > 1 or nc.dimensions['lsmlon'].size > 1


# =============================================================================
# Regional data helpers
# =============================================================================

def get_field_2d(var):
    """Return a 2-D (nlat, nlon) float array for a (lsmlat, lsmlon) variable.
    Any leading singleton dimensions are squeezed away."""
    data = var[:]
    if hasattr(data, 'mask'):
        data = np.ma.filled(data, np.nan)
    return np.array(np.squeeze(data), dtype=float)


def _robust_clim(data):
    """Return (vmin, vmax) clipped to the 2nd-98th percentile of finite values."""
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin = float(np.percentile(finite, 2))
    vmax = float(np.percentile(finite, 98))
    if vmin == vmax:
        vmin -= 0.5
        vmax += 0.5
    return vmin, vmax


def plot_map(ax, data2d, lons2d, lats2d, title, units, cmap='viridis'):
    """Plot a 2-D spatial field using pcolormesh with a colourbar."""
    vmin, vmax = _robust_clim(data2d)
    pcm = ax.pcolormesh(lons2d, lats2d, data2d, cmap=cmap,
                        vmin=vmin, vmax=vmax, shading='auto')
    plt.colorbar(pcm, ax=ax, label=units, fraction=0.046, pad=0.04)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xlabel('Lon (\u00b0E)', fontsize=7)
    ax.set_ylabel('Lat (\u00b0N)', fontsize=7)
    ax.tick_params(labelsize=7)


def plot_diff_map(ax, diff2d, lons2d, lats2d, title, units):
    """Plot a difference field (file2 - file1) with a symmetric diverging colourmap."""
    finite = diff2d[np.isfinite(diff2d)]
    vmax = float(np.percentile(np.abs(finite), 98)) if finite.size else 1.0
    if vmax == 0:
        vmax = 1.0
    pcm = ax.pcolormesh(lons2d, lats2d, diff2d, cmap='RdBu_r',
                        vmin=-vmax, vmax=vmax, shading='auto')
    plt.colorbar(pcm, ax=ax, label=units, fraction=0.046, pad=0.04)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xlabel('Lon (\u00b0E)', fontsize=7)
    ax.set_ylabel('Lat (\u00b0N)', fontsize=7)
    ax.tick_params(labelsize=7)


def plot_map_grid(data_list, titles, lons2d, lats2d, suptitle,
                  units=None, cmap='viridis', ncols=3, cell_size=(4.2, 3.2)):
    """Create a grid of 2-D spatial maps.

    units : str or list of str (one per map)
    cmap  : str or list of str (one per map)
    """
    n = len(data_list)
    if n == 0:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
        return fig
    units_list = ([units] * n) if (units is None or isinstance(units, str)) else list(units)
    if units is None:
        units_list = [''] * n
    cmap_list = [cmap] * n if isinstance(cmap, str) else list(cmap)
    nrows = max(1, (n + ncols - 1) // ncols)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * cell_size[0], nrows * cell_size[1]),
                             squeeze=False)
    axes_flat = axes.flatten()
    for i in range(n):
        plot_map(axes_flat[i], data_list[i], lons2d, lats2d,
                 titles[i], units_list[i], cmap=cmap_list[i])
    for i in range(n, len(axes_flat)):
        axes_flat[i].axis('off')
    fig.suptitle(suptitle, fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def create_domain_map_figure(lons2d, lats2d, figsize=(10, 7)):
    """Create a domain overview map with the bounding box highlighted.
    Returns None if cartopy is not available."""
    if not HAS_CARTOPY:
        return None
    lon_min = float(np.nanmin(lons2d))
    lon_max = float(np.nanmax(lons2d))
    lat_min = float(np.nanmin(lats2d))
    lat_max = float(np.nanmax(lats2d))
    margin_lon = max(2.0, (lon_max - lon_min) * 0.15)
    margin_lat = max(2.0, (lat_max - lat_min) * 0.15)
    title = (f'Domain Extent  '
             f'{lon_min:.2f}\u00b0\u2013{lon_max:.2f}\u00b0E, '
             f'{lat_min:.2f}\u00b0\u2013{lat_max:.2f}\u00b0N  '
             f'({lons2d.shape[1]}\u00d7{lons2d.shape[0]} cells)')
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    extent = [lon_min - margin_lon, lon_max + margin_lon,
              lat_min - margin_lat, lat_max + margin_lat]
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#c8e6f5')
    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='#f2efe8')
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.8, edgecolor='#555555')
    ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.7, edgecolor='#888888')
    ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor='#c8e6f5', alpha=0.8)
    ax.add_feature(cfeature.RIVERS.with_scale('50m'), linewidth=0.4, edgecolor='#6baed6', alpha=0.6)
    ax.plot([lon_min, lon_max, lon_max, lon_min, lon_min],
            [lat_min, lat_min, lat_max, lat_max, lat_min],
            color='#e53e3e', linewidth=2.5, transform=ccrs.PlateCarree(), zorder=5)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(title, fontsize=12, fontweight='bold')
    return fig


def plot_monthly_timeseries_regional(ax, data, pft_indices, title, units,
                                     pft_names, land_mask):
    """Plot monthly time series for selected PFTs as spatial means over land cells."""
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(pft_indices), 1)))
    for pft_idx, color in zip(pft_indices, colors):
        values = np.array([
            float(np.nanmean(np.where(land_mask, data[m, pft_idx, :, :], np.nan)))
            for m in range(12)
        ])
        if np.any(values > 0):
            label = pft_names.get(pft_idx, f'PFT {pft_idx}')
            if len(label) > 25:
                label = label[:22] + '...'
            ax.plot(range(12), values, marker='o', label=label, color=color, linewidth=2)
    ax.set_xticks(range(12))
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_xlabel('Month')
    ax.set_ylabel(f'[{units}] (spatial mean)')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=7)
    ax.grid(alpha=0.3)


def create_scalar_card(ax, name, value, units, long_name):
    """Create a card-style visualization for a scalar variable."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Background
    rect = mpatches.FancyBboxPatch((0.5, 0.5), 9, 9, boxstyle="round,pad=0.1",
                                    facecolor='#f0f4f8', edgecolor='#2c5282', linewidth=2)
    ax.add_patch(rect)

    # Variable name
    ax.text(5, 7.5, name, ha='center', va='center', fontsize=14, fontweight='bold', color='#2c5282')

    # Value
    if isinstance(value, float):
        if abs(value) < 0.01 or abs(value) > 10000:
            value_str = f'{value:.4e}'
        else:
            value_str = f'{value:.4f}'
    else:
        value_str = str(value)

    ax.text(5, 5, value_str, ha='center', va='center', fontsize=20, fontweight='bold', color='#1a365d')

    # Units
    ax.text(5, 3, f'[{units}]', ha='center', va='center', fontsize=10, color='#4a5568')

    # Long name (wrapped)
    wrapped_name = '\n'.join([long_name[i:i+30] for i in range(0, len(long_name), 30)])
    ax.text(5, 1.5, wrapped_name, ha='center', va='center', fontsize=8, color='#718096', style='italic')


def plot_soil_profile(ax, depths, values, title, units, color='#3182ce'):
    """Create a soil profile plot (vertical bar chart)."""
    ax.barh(range(len(depths)), values, color=color, edgecolor='#2c5282', alpha=0.8)
    ax.set_yticks(range(len(depths)))
    ax.set_yticklabels([f'{d:.2f}m' for d in depths])
    ax.invert_yaxis()
    ax.set_xlabel(f'{title} [{units}]')
    ax.set_ylabel('Depth')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add value labels
    for i, v in enumerate(values):
        ax.text(v + max(values)*0.02, i, f'{v:.1f}', va='center', fontsize=8)


def plot_pie_chart(ax, labels, values, title, min_pct=0.5):
    """Create a pie chart with smart label handling."""
    # Filter out zero or very small values
    mask = values > min_pct
    filtered_labels = [l for l, m in zip(labels, mask) if m]
    filtered_values = values[mask]

    if len(filtered_values) == 0:
        ax.text(0.5, 0.5, 'No significant values', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title, fontsize=12, fontweight='bold')
        return

    colors = plt.cm.tab20(np.linspace(0, 1, len(filtered_values)))

    wedges, texts, autotexts = ax.pie(filtered_values, labels=None, autopct='%1.1f%%',
                                       colors=colors, pctdistance=0.75)

    # Add legend with labels
    ax.legend(wedges, [f'{l}: {v:.1f}%' for l, v in zip(filtered_labels, filtered_values)],
              loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8)

    ax.set_title(title, fontsize=12, fontweight='bold')


def plot_bar_chart(ax, labels, values, title, units, color='#3182ce', horizontal=False):
    """Create a bar chart."""
    x = range(len(labels))

    if horizontal:
        ax.barh(x, values, color=color, edgecolor='#2c5282', alpha=0.8)
        ax.set_yticks(x)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel(f'{title} [{units}]')
    else:
        ax.bar(x, values, color=color, edgecolor='#2c5282', alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel(f'[{units}]')

    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(axis='y' if not horizontal else 'x', alpha=0.3)


def plot_monthly_timeseries(ax, data, pft_indices, title, units, pft_names):
    """Plot monthly time series for selected PFTs."""
    colors = plt.cm.tab10(np.linspace(0, 1, len(pft_indices)))

    for i, (pft_idx, color) in enumerate(zip(pft_indices, colors)):
        values = data[:, pft_idx, 0, 0]  # time, pft, lat, lon
        if np.any(values > 0):
            label = pft_names.get(pft_idx, f'PFT {pft_idx}')
            # Truncate label if too long
            if len(label) > 25:
                label = label[:22] + '...'
            ax.plot(range(12), values, marker='o', label=label, color=color, linewidth=2)

    ax.set_xticks(range(12))
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_xlabel('Month')
    ax.set_ylabel(f'[{units}]')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=7)
    ax.grid(alpha=0.3)


def plot_grouped_bar(ax, data, group_labels, bar_labels, title, units):
    """Create a grouped bar chart."""
    x = np.arange(len(group_labels))
    width = 0.25
    n_bars = len(bar_labels)

    colors = plt.cm.Set2(np.linspace(0, 1, n_bars))

    for i, (bar_label, color) in enumerate(zip(bar_labels, colors)):
        offset = (i - n_bars/2 + 0.5) * width
        ax.bar(x + offset, data[i], width, label=bar_label, color=color, edgecolor='#2c5282')

    ax.set_xticks(x)
    ax.set_xticklabels(group_labels, fontsize=9)
    ax.set_ylabel(f'[{units}]')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)


def plot_heatmap(ax, data, x_labels, y_labels, title, units, cmap='viridis'):
    """Create a heatmap."""
    im = ax.imshow(data, cmap=cmap, aspect='auto')

    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels, fontsize=9)

    # Add value annotations
    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            val = data[i, j]
            text_color = 'white' if val > np.mean(data) else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=text_color, fontsize=8)

    ax.set_title(f'{title} [{units}]', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax, label=units)


def fig_to_base64(fig):
    """Convert a matplotlib figure to base64 string for HTML embedding."""
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def create_site_location_figure(lons, lats, labels=None, zoom_margin=10, figsize=(10, 7)):
    """Create a figure with a political map showing one or more site locations.

    Parameters
    ----------
    lons, lats : lists of float
        Longitude and latitude values of the site(s).
    labels : list of str, optional
        Labels shown next to each site marker.
    zoom_margin : float
        Degrees of padding around the site(s) on the map.
    figsize : tuple
        Figure size in inches.

    Returns None if cartopy is not available.
    """
    if not HAS_CARTOPY:
        return None

    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # Compute map extent
    if len(lons) == 1:
        lon_c, lat_c = lons[0], lats[0]
        extent = [lon_c - zoom_margin, lon_c + zoom_margin,
                  lat_c - zoom_margin * 0.7, lat_c + zoom_margin * 0.7]
    else:
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        span = max(lon_max - lon_min, lat_max - lat_min)
        margin = max(zoom_margin, span + 5)
        lon_c = (lon_min + lon_max) / 2
        lat_c = (lat_min + lat_max) / 2
        extent = [lon_c - margin, lon_c + margin,
                  lat_c - margin * 0.7, lat_c + margin * 0.7]

    ax.set_extent(extent, crs=ccrs.PlateCarree())

    # Add map features
    ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#c8e6f5')
    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='#f2efe8')
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.8, edgecolor='#555555')
    ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.7, edgecolor='#888888', linestyle='-')
    ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor='#c8e6f5', alpha=0.8)
    ax.add_feature(cfeature.RIVERS.with_scale('50m'), linewidth=0.4, edgecolor='#6baed6', alpha=0.6)

    # Plot site markers
    site_colors = ['#e53e3e', '#3182ce', '#38a169', '#d69e2e', '#805ad5']
    for i, (lon, lat) in enumerate(zip(lons, lats)):
        color = site_colors[i % len(site_colors)]
        ax.plot(lon, lat, marker='*', color=color, markersize=20,
                transform=ccrs.PlateCarree(), zorder=5,
                markeredgecolor='white', markeredgewidth=0.5)
        label_text = labels[i] if labels else f'({lon:.3f}°E, {lat:.3f}°N)'
        ax.text(lon + 0.3, lat + 0.3, label_text,
                transform=ccrs.PlateCarree(), fontsize=9, fontweight='bold',
                color=color,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor=color, linewidth=1.2, alpha=0.9),
                zorder=6)

    # Gridlines
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False

    if len(lons) == 1:
        ax.set_title(f'Site Location  ({lons[0]:.3f}°E, {lats[0]:.3f}°N)',
                     fontsize=13, fontweight='bold')
    else:
        ax.set_title('Site Locations', fontsize=13, fontweight='bold')

    return fig


def create_html_report(figures_data, nc_file, output_dir, metadata_str=''):
    """Generate an HTML report with all figures embedded."""

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surface Data Visualization Report</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        header {{
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #718096;
            font-size: 1.1em;
        }}
        .metadata {{
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
            font-size: 0.9em;
            color: #4a5568;
        }}
        .nav {{
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .nav h3 {{
            color: #2d3748;
            margin-bottom: 15px;
        }}
        .nav ul {{
            list-style: none;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .nav a {{
            display: inline-block;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 20px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        .nav a:hover {{
            background: #5a67d8;
            transform: translateY(-2px);
        }}
        .section {{
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .section h2 {{
            color: #2d3748;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .section-description {{
            color: #718096;
            margin-bottom: 20px;
            font-style: italic;
        }}
        .figure-container {{
            text-align: center;
            margin: 20px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 10px;
        }}
        .figure-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .figure-caption {{
            margin-top: 15px;
            color: #4a5568;
            font-size: 0.95em;
        }}
        .download-btn {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #48bb78;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.85em;
            transition: background 0.3s ease;
        }}
        .download-btn:hover {{
            background: #38a169;
        }}
        footer {{
            text-align: center;
            color: white;
            padding: 20px;
            font-size: 0.9em;
        }}
        .variable-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .variable-table th, .variable-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        .variable-table th {{
            background: #edf2f7;
            color: #2d3748;
            font-weight: 600;
        }}
        .variable-table tr:hover {{
            background: #f7fafc;
        }}
        @media (max-width: 768px) {{
            h1 {{
                font-size: 1.8em;
            }}
            .nav ul {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CLM5 Surface Data Visualization Report</h1>
            <p class="subtitle">Comprehensive analysis of land surface parameters for model input review</p>
            <div class="metadata">
                <strong>Source File:</strong> {nc_file}<br>
                <strong>Generated:</strong> {timestamp}<br>
                {metadata_str}
            </div>
        </header>

        <nav class="nav">
            <h3>Quick Navigation</h3>
            <ul>
                {nav_links}
            </ul>
        </nav>

        {sections}

        <footer>
            <p>Generated by CLM5 Surface Data Visualization Tool</p>
            <p>For discussion of model input parameters</p>
        </footer>
    </div>
</body>
</html>"""

    sections_html = ""
    nav_links_html = ""

    for section in figures_data:
        section_id = section['id']
        section_title = section['title']
        section_desc = section.get('description', '')

        nav_links_html += f'<li><a href="#{section_id}">{section_title}</a></li>\n'

        figures_html = ""
        for fig_data in section['figures']:
            pdf_filename = fig_data['pdf_name']
            caption = fig_data['caption']
            img_base64 = fig_data['base64']

            figures_html += f"""
            <div class="figure-container">
                <img src="data:image/png;base64,{img_base64}" alt="{caption}">
                <p class="figure-caption">{caption}</p>
                <a href="{pdf_filename}" class="download-btn">Download PDF</a>
            </div>
            """

        sections_html += f"""
        <section class="section" id="{section_id}">
            <h2>{section_title}</h2>
            <p class="section-description">{section_desc}</p>
            {figures_html}
        </section>
        """

    html_content = html_template.format(
        nc_file=os.path.basename(nc_file),
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        metadata_str=metadata_str,
        nav_links=nav_links_html,
        sections=sections_html
    )

    # Create HTML filename based on NC filename (replace .nc with .html)
    nc_basename = os.path.basename(nc_file)
    if nc_basename.endswith('.nc'):
        html_basename = nc_basename[:-3] + '.html'
    else:
        html_basename = nc_basename + '.html'

    output_file = os.path.join(output_dir, html_basename)
    with open(output_file, 'w') as f:
        f.write(html_content)

    return output_file


def main(nc_file):
    """Main function to create all visualizations."""

    if not os.path.exists(nc_file):
        print(f"Error: File not found: {nc_file}")
        sys.exit(1)

    # Create output directory based on NC filename (replace .nc with _figures)
    output_dir = os.path.dirname(nc_file)
    if not output_dir:
        output_dir = '.'

    nc_basename = os.path.basename(nc_file)
    if nc_basename.endswith('.nc'):
        figures_dirname = nc_basename[:-3] + '_figures'
    else:
        figures_dirname = nc_basename + '_figures'

    pdf_dir = os.path.join(output_dir, figures_dirname)
    os.makedirs(pdf_dir, exist_ok=True)

    print(f"Reading NetCDF file: {nc_file}")
    nc = Dataset(nc_file, 'r')

    # Detect grid type
    is_regional = detect_grid_type(nc)
    print(f"Grid mode: {'regional' if is_regional else 'single-site'}")

    # Get coordinates / domain info
    if is_regional:
        lons = get_field_2d(nc.variables['LONGXY'])
        lats = get_field_2d(nc.variables['LATIXY'])
        lon_min = float(np.nanmin(lons))
        lon_max = float(np.nanmax(lons))
        lat_min = float(np.nanmin(lats))
        lat_max = float(np.nanmax(lats))
        # Land mask for spatial averages
        if 'LANDFRAC_PFT' in nc.variables:
            land_mask = get_field_2d(nc.variables['LANDFRAC_PFT']) > 0
        elif 'PFTDATA_MASK' in nc.variables:
            land_mask = get_field_2d(nc.variables['PFTDATA_MASK']).astype(bool)
        else:
            land_mask = np.ones(lons.shape, dtype=bool)
        metadata_str = (f'<strong>Mode:</strong> Regional grid '
                        f'({lons.shape[1]}\u00d7{lons.shape[0]} cells)<br>'
                        f'<strong>Domain:</strong> '
                        f'{lon_min:.2f}\u00b0\u2013{lon_max:.2f}\u00b0E, '
                        f'{lat_min:.2f}\u00b0\u2013{lat_max:.2f}\u00b0N')
    else:
        lon = get_scalar_value(nc.variables['LONGXY'])
        lat = get_scalar_value(nc.variables['LATIXY'])
        metadata_str = f'<strong>Coordinates:</strong> {lon:.3f}\u00b0E, {lat:.3f}\u00b0N'

    figures_data = []

    # =========================================================================
    # SECTION 1: Location and Basic Parameters
    # =========================================================================
    print("Creating Section 1: Location and Basic Parameters...")
    section1_figures = []

    if is_regional:
        # Domain overview map
        fig_map = create_domain_map_figure(lons, lats)
        if fig_map is not None:
            pdf_path = os.path.join(pdf_dir, '00_domain_overview.pdf')
            fig_map.savefig(pdf_path, bbox_inches='tight')
            section1_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': (f'Domain extent: {lon_min:.2f}\u00b0\u2013{lon_max:.2f}\u00b0E, '
                            f'{lat_min:.2f}\u00b0\u2013{lat_max:.2f}\u00b0N '
                            f'({lons.shape[1]}\u00d7{lons.shape[0]} cells).'),
                'base64': fig_to_base64(fig_map)
            })
            plt.close(fig_map)

        # Grid of basic parameter maps
        basic_map_vars = [
            ('AREA',      'km\u00b2',    'viridis'),
            ('FMAX',      'unitless',    'Blues'),
            ('SOIL_COLOR','index',       'tab20b'),
            ('zbedrock',  'm',           'copper'),
            ('SLOPE',     'degrees',     'YlOrRd'),
            ('STD_ELEV',  'm',           'terrain'),
            ('LAKEDEPTH', 'm',           'Blues'),
            ('peatf',     'fraction',    'Greens'),
            ('gdp',       'unitless',    'YlOrBr'),
        ]
        data_list, titles_list, units_list, cmaps_list = [], [], [], []
        for var_name, units_str, cmap_str in basic_map_vars:
            if var_name in nc.variables:
                d = get_field_2d(nc.variables[var_name])
                if d.ndim == 2:
                    data_list.append(d)
                    titles_list.append(var_name)
                    units_list.append(units_str)
                    cmaps_list.append(cmap_str)
        fig = plot_map_grid(data_list, titles_list, lons, lats,
                            'Basic Parameters \u2013 Spatial Distribution',
                            units=units_list, cmap=cmaps_list, ncols=3)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '01_basic_parameters.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section1_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial maps of basic parameters: area, FMAX, soil colour, bedrock depth, slope, elevation std, lake depth, peatland fraction, GDP.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    else:
        # Figure 1.0: Site location map
        fig_map = create_site_location_figure([lon], [lat])
        if fig_map is not None:
            pdf_path = os.path.join(pdf_dir, '00_site_location.pdf')
            fig_map.savefig(pdf_path, bbox_inches='tight')
            section1_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': f'Political map showing the site location at {lon:.3f}\u00b0E, {lat:.3f}\u00b0N.',
                'base64': fig_to_base64(fig_map)
            })
            plt.close(fig_map)

        # Figure 1.1: Location and basic info
        fig, axes = plt.subplots(3, 4, figsize=(16, 12))
        fig.suptitle('Basic Site Parameters', fontsize=16, fontweight='bold')

        scalar_vars = [
            ('LONGXY', 'degrees east'),
            ('LATIXY', 'degrees north'),
            ('AREA', 'km^2'),
            ('FMAX', 'unitless'),
            ('SOIL_COLOR', 'index'),
            ('mxsoil_color', 'unitless'),
            ('zbedrock', 'm'),
            ('SLOPE', 'degrees'),
            ('STD_ELEV', 'm'),
            ('LAKEDEPTH', 'm'),
            ('gdp', 'unitless'),
            ('abm', 'month')
        ]

        for ax, (var_name, units) in zip(axes.flatten(), scalar_vars):
            var = nc.variables[var_name]
            value = get_scalar_value(var)
            long_name = var.long_name if hasattr(var, 'long_name') else var_name
            create_scalar_card(ax, var_name, value, units, long_name)

        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '01_basic_parameters.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section1_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Basic site parameters including location, area, soil color, bedrock depth, slope, and economic indicators.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'basic-params',
        'title': 'Basic Site Parameters' if not is_regional else 'Domain Overview & Basic Parameters',
        'description': 'Fundamental parameters describing the site location, topography, and basic soil/lake properties.',
        'figures': section1_figures,
    })

    # =========================================================================
    # SECTION 2: Land Cover Fractions
    # =========================================================================
    print("Creating Section 2: Land Cover Fractions...")
    section2_figures = []

    if is_regional:
        # Spatial maps of major land cover fractions
        lc_vars = [
            ('PCT_NATVEG',  'Natural Vegetation (%)',  'Greens'),
            ('PCT_CROP',    'Cropland (%)',             'YlOrBr'),
            ('PCT_LAKE',    'Lake (%)',                 'Blues'),
            ('PCT_WETLAND', 'Wetland (%)',              'PuBuGn'),
            ('PCT_GLACIER', 'Glacier (%)',              'cool'),
        ]
        data_list, titles_list, units_list, cmaps_list = [], [], [], []
        for var_name, title_str, cmap_str in lc_vars:
            if var_name in nc.variables:
                data_list.append(get_field_2d(nc.variables[var_name]))
                titles_list.append(title_str)
                units_list.append('%')
                cmaps_list.append(cmap_str)
        # Total urban (sum over density classes)
        if 'PCT_URBAN' in nc.variables:
            pct_urban_3d = np.array(nc.variables['PCT_URBAN'][:])
            if hasattr(pct_urban_3d, 'mask'):
                pct_urban_3d = np.ma.filled(pct_urban_3d, 0.0)
            data_list.append(pct_urban_3d.sum(axis=0))
            titles_list.append('Urban total (%)')
            units_list.append('%')
            cmaps_list.append('Reds')
        fig = plot_map_grid(data_list, titles_list, lons, lats,
                            'Land Cover Fractions \u2013 Spatial Distribution',
                            units=units_list, cmap=cmaps_list, ncols=3)
        pdf_path = os.path.join(pdf_dir, '02_land_cover_maps.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section2_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial maps of land cover fractions: natural vegetation, cropland, lake, wetland, glacier, and total urban.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Also store domain-mean land values for use in later sections
        pct_natveg = float(np.nanmean(np.where(land_mask, get_field_2d(nc.variables['PCT_NATVEG']), np.nan)))
        pct_crop   = float(np.nanmean(np.where(land_mask, get_field_2d(nc.variables['PCT_CROP']),   np.nan)))
        pct_urban_arr = data_list[titles_list.index('Urban total (%)')]
        pct_urban  = np.array([
            float(np.nanmean(np.where(land_mask, get_field_2d(nc.variables['PCT_URBAN'])[i], np.nan)))
            for i in range(nc.variables['PCT_URBAN'].shape[0])
        ])

    else:
        # Figure 2.1: Major land cover pie chart
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        pct_natveg = get_scalar_value(nc.variables['PCT_NATVEG'])
        pct_crop   = get_scalar_value(nc.variables['PCT_CROP'])
        pct_urban  = get_1d_array(nc.variables['PCT_URBAN'])
        pct_lake    = get_scalar_value(nc.variables['PCT_LAKE'])
        pct_wetland = get_scalar_value(nc.variables['PCT_WETLAND'])
        pct_glacier = get_scalar_value(nc.variables['PCT_GLACIER'])

        land_labels = ['Natural Vegetation', 'Cropland', 'Urban', 'Lake', 'Wetland', 'Glacier']
        land_values = np.array([pct_natveg, pct_crop, np.sum(pct_urban),
                                pct_lake, pct_wetland, pct_glacier])

        plot_pie_chart(axes[0], land_labels, land_values, 'Major Land Cover Types', min_pct=0.1)

        axes[1].bar(land_labels, land_values,
                    color=['#48bb78', '#ecc94b', '#a0aec0', '#4299e1', '#9f7aea', '#63b3ed'],
                    edgecolor='#2d3748')
        axes[1].set_ylabel('Percent (%)')
        axes[1].set_title('Land Cover Distribution', fontsize=12, fontweight='bold')
        axes[1].tick_params(axis='x', rotation=45)
        for i, v in enumerate(land_values):
            if v > 0:
                axes[1].text(i, v + 1, f'{v:.1f}%', ha='center', fontsize=9)
        axes[1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '02_land_cover_major.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section2_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Distribution of major land cover types: natural vegetation, cropland, urban, lake, wetland, and glacier.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'land-cover',
        'title': 'Land Cover Fractions',
        'description': 'Overview of land surface cover type distribution.',
        'figures': section2_figures
    })

    # =========================================================================
    # SECTION 3: Natural PFT Distribution
    # =========================================================================
    print("Creating Section 3: Natural PFT Distribution...")
    section3_figures = []

    if is_regional:
        pct_nat_pft_data = np.array(nc.variables['PCT_NAT_PFT'][:], dtype=float)
        if hasattr(nc.variables['PCT_NAT_PFT'][:], 'mask'):
            pct_nat_pft_data = np.ma.filled(nc.variables['PCT_NAT_PFT'][:], np.nan)
        n_natpft = pct_nat_pft_data.shape[0]

        # Maps for PFTs present anywhere in the domain (max > 1%)
        active_idx = [i for i in range(n_natpft)
                      if np.nanmax(pct_nat_pft_data[i]) > 1.0]
        data_list  = [pct_nat_pft_data[i] for i in active_idx]
        titles_list = [NATPFT_NAMES.get(i, f'PFT {i}')[:22] for i in active_idx]

        if data_list:
            ncols = min(4, len(data_list))
            fig = plot_map_grid(data_list, titles_list, lons, lats,
                                'Natural PFT Distribution (% of natural veg landunit)',
                                units='%', cmap='YlGn', ncols=ncols)
            pdf_path = os.path.join(pdf_dir, '03_natural_pft_maps.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            section3_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': f'Spatial maps of natural PFT fractions (showing {len(active_idx)} PFTs with max > 1%).',
                'base64': fig_to_base64(fig)
            })
            plt.close(fig)

        # Domain-mean bar chart
        natpft_labels = [NATPFT_NAMES.get(i, f'PFT {i}') for i in range(n_natpft)]
        pct_nat_pft_mean = np.array([
            float(np.nanmean(np.where(land_mask, pct_nat_pft_data[i], np.nan)))
            for i in range(n_natpft)
        ])
        fig, ax = plt.subplots(figsize=(12, 6))
        colors_bar = plt.cm.Greens(np.linspace(0.3, 0.9, n_natpft))
        ax.barh(range(n_natpft), pct_nat_pft_mean, color=colors_bar, edgecolor='#2d3748')
        ax.set_yticks(range(n_natpft))
        ax.set_yticklabels(natpft_labels, fontsize=9)
        ax.set_xlabel('Domain-mean percent of Natural Vegetation Landunit (%)')
        ax.set_title('Natural PFTs \u2013 Domain Mean', fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '03b_natural_pft_mean.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section3_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Domain-mean natural PFT fractions (land-cell average).',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Keep domain-mean for summary use
        pct_nat_pft = pct_nat_pft_mean

    else:
        fig, axes = plt.subplots(1, 2, figsize=(16, 7))

        pct_nat_pft = get_1d_array(nc.variables['PCT_NAT_PFT'])
        natpft_labels = [NATPFT_NAMES.get(i, f'PFT {i}') for i in range(15)]

        plot_pie_chart(axes[0], natpft_labels, pct_nat_pft,
                       f'Natural PFT Distribution\n(within {pct_natveg:.1f}% natural veg)', min_pct=0.5)

        colors = plt.cm.Greens(np.linspace(0.3, 0.9, 15))
        y_pos = range(15)
        axes[1].barh(y_pos, pct_nat_pft, color=colors, edgecolor='#2d3748')
        axes[1].set_yticks(y_pos)
        axes[1].set_yticklabels(natpft_labels, fontsize=9)
        axes[1].set_xlabel('Percent of Natural Vegetation Landunit (%)')
        axes[1].set_title('Natural Plant Functional Types', fontsize=12, fontweight='bold')
        axes[1].grid(axis='x', alpha=0.3)
        for i, v in enumerate(pct_nat_pft):
            if v > 0:
                axes[1].text(v + 1, i, f'{v:.1f}%', va='center', fontsize=8)

        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '03_natural_pft.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section3_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Distribution of natural Plant Functional Types (PFTs). Values represent percentages within the natural vegetation landunit.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'natural-pft',
        'title': 'Natural PFT Distribution',
        'description': 'Natural Plant Functional Type distribution within the natural vegetation landunit.',
        'figures': section3_figures
    })

    # =========================================================================
    # SECTION 4: Crop Functional Types
    # =========================================================================
    print("Creating Section 4: Crop Functional Types...")
    section4_figures = []

    cft_indices = nc.variables['cft'][:]

    if is_regional:
        pct_cft_data = np.array(nc.variables['PCT_CFT'][:], dtype=float)
        if hasattr(nc.variables['PCT_CFT'][:], 'mask'):
            pct_cft_data = np.ma.filled(nc.variables['PCT_CFT'][:], np.nan)
        n_cft = pct_cft_data.shape[0]

        # Maps for CFTs present anywhere (max > 1%)
        active_cft_idx = [i for i in range(n_cft)
                          if np.nanmax(pct_cft_data[i]) > 1.0]
        if active_cft_idx:
            data_list   = [pct_cft_data[i] for i in active_cft_idx]
            titles_list = [CFT_NAMES.get(int(cft_indices[i]), f'CFT {cft_indices[i]}')[:22]
                           for i in active_cft_idx]
            ncols = min(4, len(data_list))
            fig = plot_map_grid(data_list, titles_list, lons, lats,
                                'Crop Functional Types (% of crop landunit)',
                                units='%', cmap='YlOrBr', ncols=ncols)
            pdf_path = os.path.join(pdf_dir, '04_cft_maps.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            section4_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': f'Spatial maps of crop functional types (showing {len(active_cft_idx)} CFTs with max > 1%).',
                'base64': fig_to_base64(fig)
            })
            plt.close(fig)

        # Domain-mean fertilizer bar chart
        fertnitro_data = np.array(nc.variables['CONST_FERTNITRO_CFT'][:], dtype=float)
        if hasattr(nc.variables['CONST_FERTNITRO_CFT'][:], 'mask'):
            fertnitro_data = np.ma.filled(nc.variables['CONST_FERTNITRO_CFT'][:], np.nan)
        fert_mean = np.array([
            float(np.nanmean(np.where(land_mask, fertnitro_data[i], np.nan)))
            for i in range(n_cft)
        ])
        nonzero_fert_mask = fert_mean > 0
        if np.any(nonzero_fert_mask):
            nz_fert = fert_mean[nonzero_fert_mask]
            nz_fert_labels = [CFT_NAMES.get(int(cft_indices[i]), f'CFT {cft_indices[i]}')
                              for i in range(n_cft) if nonzero_fert_mask[i]]
            fig, ax = plt.subplots(figsize=(14, 6))
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(nz_fert)))
            ax.bar(range(len(nz_fert)), nz_fert, color=colors, edgecolor='#2d3748')
            ax.set_xticks(range(len(nz_fert)))
            ax.set_xticklabels(nz_fert_labels, rotation=45, ha='right', fontsize=9)
            ax.set_ylabel('N Fertilizer \u2013 Domain Mean (gN/m\u00b2/yr)')
            ax.set_title('Nitrogen Fertilizer \u2013 Domain Mean by Crop Type', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            pdf_path = os.path.join(pdf_dir, '04b_nitrogen_fertilizer.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            section4_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': 'Domain-mean nitrogen fertilizer application rates for non-zero crop types.',
                'base64': fig_to_base64(fig)
            })
            plt.close(fig)

    else:
        pct_cft = get_1d_array(nc.variables['PCT_CFT'])
        nonzero_mask = pct_cft > 0.1
        nonzero_cft_values  = pct_cft[nonzero_mask]
        nonzero_cft_indices = cft_indices[nonzero_mask]
        nonzero_cft_labels  = [CFT_NAMES.get(int(i), f'CFT {i}') for i in nonzero_cft_indices]

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        if len(nonzero_cft_values) > 0:
            plot_pie_chart(axes[0], nonzero_cft_labels, nonzero_cft_values,
                          f'Crop Type Distribution\n(within {pct_crop:.1f}% cropland)', min_pct=0.1)
            colors = plt.cm.YlOrBr(np.linspace(0.3, 0.9, len(nonzero_cft_values)))
            y_pos = range(len(nonzero_cft_values))
            axes[1].barh(y_pos, nonzero_cft_values, color=colors, edgecolor='#2d3748')
            axes[1].set_yticks(y_pos)
            axes[1].set_yticklabels(nonzero_cft_labels, fontsize=9)
            axes[1].set_xlabel('Percent of Crop Landunit (%)')
            axes[1].set_title('Crop Functional Types (non-zero only)', fontsize=12, fontweight='bold')
            axes[1].grid(axis='x', alpha=0.3)
            for i, v in enumerate(nonzero_cft_values):
                axes[1].text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=9)
        else:
            axes[0].text(0.5, 0.5, 'No crops present', ha='center', va='center', transform=axes[0].transAxes)
            axes[1].text(0.5, 0.5, 'No crops present', ha='center', va='center', transform=axes[1].transAxes)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '04_crop_functional_types.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section4_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Distribution of Crop Functional Types (CFTs). Values represent percentages within the crop landunit.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(14, 6))
        fertnitro = get_1d_array(nc.variables['CONST_FERTNITRO_CFT'])
        nonzero_fert_mask = fertnitro > 0
        if np.any(nonzero_fert_mask):
            nonzero_fert = fertnitro[nonzero_fert_mask]
            nonzero_fert_indices = cft_indices[nonzero_fert_mask]
            nonzero_fert_labels  = [CFT_NAMES.get(int(i), f'CFT {i}') for i in nonzero_fert_indices]
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(nonzero_fert)))
            ax.bar(range(len(nonzero_fert)), nonzero_fert, color=colors, edgecolor='#2d3748')
            ax.set_xticks(range(len(nonzero_fert)))
            ax.set_xticklabels(nonzero_fert_labels, rotation=45, ha='right', fontsize=9)
            ax.set_ylabel('Nitrogen Fertilizer (gN/m\u00b2/yr)')
            ax.set_title('Nitrogen Fertilizer Application by Crop Type', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            for i, v in enumerate(nonzero_fert):
                ax.text(i, v + 0.3, f'{v:.1f}', ha='center', fontsize=9)
        else:
            ax.text(0.5, 0.5, 'No fertilizer data', ha='center', va='center', transform=ax.transAxes)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '04b_nitrogen_fertilizer.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section4_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Nitrogen fertilizer application rates for different crop types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'crop-types',
        'title': 'Crop Functional Types',
        'description': 'Crop Functional Type (CFT) distribution and associated nitrogen fertilizer application rates.',
        'figures': section4_figures
    })

    # =========================================================================
    # SECTION 5: Soil Properties
    # =========================================================================
    print("Creating Section 5: Soil Properties...")
    section5_figures = []

    if is_regional:
        # Load 3-D soil arrays: (nlevsoi, nlat, nlon)
        sand_3d = np.array(nc.variables['PCT_SAND'][:], dtype=float)
        clay_3d = np.array(nc.variables['PCT_CLAY'][:], dtype=float)
        org_3d  = np.array(nc.variables['ORGANIC'][:],  dtype=float)
        for arr in [sand_3d, clay_3d, org_3d]:
            if hasattr(arr, 'mask'):
                arr = np.ma.filled(arr, np.nan)

        # Maps of depth-mean values
        sand_mean2d = np.nanmean(sand_3d, axis=0)
        clay_mean2d = np.nanmean(clay_3d, axis=0)
        org_mean2d  = np.nanmean(org_3d,  axis=0)

        fig = plot_map_grid(
            [sand_mean2d, clay_mean2d, org_mean2d],
            ['Sand \u2013 depth mean', 'Clay \u2013 depth mean', 'Organic matter \u2013 depth mean'],
            lons, lats,
            'Soil Properties \u2013 Depth-Averaged Spatial Distribution',
            units=['%', '%', 'kg/m\u00b3'],
            cmap=['YlOrBr', 'Reds', 'Greens'],
            ncols=3
        )
        pdf_path = os.path.join(pdf_dir, '05_soil_maps.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section5_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Depth-averaged spatial maps of sand content, clay content, and organic matter density.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Domain-mean soil profiles (mean ± std over land cells)
        def _masked_profile(arr3d):
            out_mean, out_std = [], []
            for lev in range(arr3d.shape[0]):
                d = arr3d[lev]
                vals = d[land_mask & np.isfinite(d)]
                out_mean.append(float(np.nanmean(vals)) if vals.size else np.nan)
                out_std.append(float(np.nanstd(vals))  if vals.size else np.nan)
            return np.array(out_mean), np.array(out_std)

        sand_m, sand_s = _masked_profile(sand_3d)
        clay_m, clay_s = _masked_profile(clay_3d)
        org_m,  org_s  = _masked_profile(org_3d)

        fig, axes = plt.subplots(1, 3, figsize=(15, 6))
        for ax, m, s, title, units_str, col in zip(
                axes,
                [sand_m, clay_m, org_m],
                [sand_s, clay_s, org_s],
                ['Sand Content', 'Clay Content', 'Organic Matter'],
                ['%', '%', 'kg/m\u00b3'],
                ['#f6ad55', '#fc8181', '#68d391']):
            ax.barh(range(len(SOIL_DEPTHS)), m, color=col, edgecolor='#2d3748', alpha=0.8,
                    xerr=s, error_kw=dict(ecolor='#2d3748', capsize=3))
            ax.set_yticks(range(len(SOIL_DEPTHS)))
            ax.set_yticklabels([f'{d:.2f}m' for d in SOIL_DEPTHS])
            ax.invert_yaxis()
            ax.set_xlabel(f'{title} [{units_str}]')
            ax.set_title(f'{title}\n(domain mean \u00b1 std)', fontsize=11, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
        fig.suptitle('Soil Properties by Depth \u2013 Domain Mean', fontsize=14, fontweight='bold')
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '05b_soil_profiles.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section5_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Domain-mean soil profiles (error bars show spatial std) for sand, clay, and organic matter.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Store domain-mean 1-D profiles for summary use
        pct_sand = sand_m
        pct_clay = clay_m

    else:
        fig, axes = plt.subplots(1, 3, figsize=(15, 6))
        pct_sand = get_1d_array(nc.variables['PCT_SAND'])
        plot_soil_profile(axes[0], SOIL_DEPTHS, pct_sand, 'Sand Content', '%', '#f6ad55')
        pct_clay = get_1d_array(nc.variables['PCT_CLAY'])
        plot_soil_profile(axes[1], SOIL_DEPTHS, pct_clay, 'Clay Content', '%', '#fc8181')
        organic = get_1d_array(nc.variables['ORGANIC'])
        plot_soil_profile(axes[2], SOIL_DEPTHS, organic, 'Organic Matter', 'kg/m3', '#68d391')
        fig.suptitle('Soil Properties by Depth', fontsize=14, fontweight='bold')
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '05_soil_properties.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section5_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Vertical profiles of soil texture (sand and clay content) and organic matter density across 10 soil layers.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 8))
        pct_silt = 100 - pct_sand - pct_clay
        x = range(len(SOIL_DEPTHS))
        width = 0.6
        ax.barh(x, pct_sand, width, label='Sand', color='#f6ad55', edgecolor='#2d3748')
        ax.barh(x, pct_silt, width, left=pct_sand, label='Silt', color='#a0aec0', edgecolor='#2d3748')
        ax.barh(x, pct_clay, width, left=pct_sand + pct_silt, label='Clay', color='#fc8181', edgecolor='#2d3748')
        ax.set_yticks(x)
        ax.set_yticklabels([f'{d:.2f}m' for d in SOIL_DEPTHS])
        ax.invert_yaxis()
        ax.set_xlabel('Percent (%)')
        ax.set_ylabel('Depth')
        ax.set_title('Soil Texture Composition by Depth', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 100)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '05b_soil_texture.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section5_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Stacked bar chart showing soil texture composition (sand, silt, clay) at each soil layer.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'soil',
        'title': 'Soil Properties',
        'description': 'Soil texture and organic matter content profiles. Critical inputs for soil hydrology and biogeochemistry.',
        'figures': section5_figures
    })

    # =========================================================================
    # SECTION 6: Monthly LAI and Vegetation Parameters
    # =========================================================================
    print("Creating Section 6: Monthly Vegetation Parameters...")
    section6_figures = []

    lai_data = np.array(nc.variables['MONTHLY_LAI'][:], dtype=float)
    sai_data = np.array(nc.variables['MONTHLY_SAI'][:], dtype=float)
    all_pft_names = {**NATPFT_NAMES, **CFT_NAMES}

    if is_regional:
        # Active PFTs: non-zero anywhere in domain
        active_pfts = [pft for pft in range(lai_data.shape[1])
                       if np.nanmax(lai_data[:, pft, :, :]) > 0]

        # Domain-mean timeseries
        fig, ax = plt.subplots(figsize=(14, 7))
        plot_monthly_timeseries_regional(ax, lai_data, active_pfts[:10],
                                         'Monthly LAI \u2013 Domain Mean', 'm\u00b2/m\u00b2',
                                         all_pft_names, land_mask)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06_monthly_lai.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Domain-mean monthly LAI for active PFTs (spatial average over land cells).',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(14, 7))
        plot_monthly_timeseries_regional(ax, sai_data, active_pfts[:10],
                                         'Monthly SAI \u2013 Domain Mean', 'm\u00b2/m\u00b2',
                                         all_pft_names, land_mask)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06b_monthly_sai.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Domain-mean monthly SAI for active PFTs.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Annual-mean LAI maps for top active PFTs
        n_map_pfts = min(8, len(active_pfts))
        if n_map_pfts > 0:
            data_list   = [np.nanmean(lai_data[:, p, :, :], axis=0) for p in active_pfts[:n_map_pfts]]
            titles_list = [all_pft_names.get(p, f'PFT {p}')[:22] for p in active_pfts[:n_map_pfts]]
            ncols = min(4, n_map_pfts)
            fig = plot_map_grid(data_list, titles_list, lons, lats,
                                'Annual-Mean LAI by PFT',
                                units='m\u00b2/m\u00b2', cmap='YlGn', ncols=ncols)
            pdf_path = os.path.join(pdf_dir, '06c_lai_maps.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            section6_figures.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': f'Spatial maps of annual-mean LAI for the {n_map_pfts} most active PFTs.',
                'base64': fig_to_base64(fig)
            })
            plt.close(fig)

    else:
        # Identify active PFTs (non-zero LAI at any month at the single cell)
        active_pfts = [pft for pft in range(79)
                       if np.any(lai_data[:, pft, 0, 0] > 0)]

        fig, ax = plt.subplots(figsize=(14, 7))
        plot_monthly_timeseries(ax, lai_data, active_pfts[:10],
                                'Monthly Leaf Area Index (LAI)', 'm2/m2', all_pft_names)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06_monthly_lai.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Monthly Leaf Area Index (LAI) time series for active Plant Functional Types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(14, 7))
        plot_monthly_timeseries(ax, sai_data, active_pfts[:10],
                                'Monthly Stem Area Index (SAI)', 'm2/m2', all_pft_names)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06b_monthly_sai.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Monthly Stem Area Index (SAI) time series for active Plant Functional Types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        height_top = nc.variables['MONTHLY_HEIGHT_TOP'][:]
        height_bot = nc.variables['MONTHLY_HEIGHT_BOT'][:]
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        plot_monthly_timeseries(axes[0], height_top, active_pfts[:10],
                                'Monthly Canopy Top Height', 'm', all_pft_names)
        plot_monthly_timeseries(axes[1], height_bot, active_pfts[:10],
                                'Monthly Canopy Bottom Height', 'm', all_pft_names)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06c_canopy_heights.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Monthly canopy top and bottom heights for active Plant Functional Types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'vegetation',
        'title': 'Monthly Vegetation Parameters',
        'description': 'Seasonal cycle of vegetation properties including LAI, SAI, and canopy heights.',
        'figures': section6_figures
    })

    # =========================================================================
    # SECTION 7: Urban Parameters
    # =========================================================================
    print("Creating Section 7: Urban Parameters...")
    section7_figures = []

    if is_regional:
        # Maps of PCT_URBAN per density class
        pct_urban_3d = np.array(nc.variables['PCT_URBAN'][:], dtype=float)
        data_list   = [pct_urban_3d[i] for i in range(len(URBAN_TYPES))]
        titles_list = [f'PCT_URBAN\n{t}' for t in URBAN_TYPES]
        fig = plot_map_grid(data_list, titles_list, lons, lats,
                            'Urban Fraction by Density Class',
                            units='%', cmap='Reds', ncols=3)
        pdf_path = os.path.join(pdf_dir, '07_urban_maps.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section7_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial maps of urban fraction for Tall Building District, High Density, and Medium Density classes.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Domain-mean bar charts for building parameters
        def _urban_mean(var_name):
            d = np.array(nc.variables[var_name][:], dtype=float)
            return np.array([
                float(np.nanmean(np.where(land_mask, d[i], np.nan)))
                for i in range(len(URBAN_TYPES))
            ])

        pct_urban      = _urban_mean('PCT_URBAN')
        canyon_hwr     = _urban_mean('CANYON_HWR')
        ht_roof        = _urban_mean('HT_ROOF')
        t_building     = _urban_mean('T_BUILDING_MIN')
        wtlunit_roof   = _urban_mean('WTLUNIT_ROOF')
        wtroad_perv    = _urban_mean('WTROAD_PERV')
        thick_roof     = _urban_mean('THICK_ROOF')
        thick_wall     = _urban_mean('THICK_WALL')
        em_improad     = _urban_mean('EM_IMPROAD')
        em_perroad     = _urban_mean('EM_PERROAD')
        em_roof        = _urban_mean('EM_ROOF')
        em_wall        = _urban_mean('EM_WALL')

    # For single-site: read all urban parameter vectors directly
    if not is_regional:
        pct_urban    = get_1d_array(nc.variables['PCT_URBAN'])
        canyon_hwr   = get_1d_array(nc.variables['CANYON_HWR'])
        ht_roof      = get_1d_array(nc.variables['HT_ROOF'])
        t_building   = get_1d_array(nc.variables['T_BUILDING_MIN'])
        wtlunit_roof = get_1d_array(nc.variables['WTLUNIT_ROOF'])
        wtroad_perv  = get_1d_array(nc.variables['WTROAD_PERV'])
        thick_roof   = get_1d_array(nc.variables['THICK_ROOF'])
        thick_wall   = get_1d_array(nc.variables['THICK_WALL'])
        em_improad   = get_1d_array(nc.variables['EM_IMPROAD'])
        em_perroad   = get_1d_array(nc.variables['EM_PERROAD'])
        em_roof      = get_1d_array(nc.variables['EM_ROOF'])
        em_wall      = get_1d_array(nc.variables['EM_WALL'])

    # Shared bar chart for building parameters (works for both modes)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    axes[0, 0].bar(URBAN_TYPES, pct_urban, color=['#e53e3e', '#dd6b20', '#d69e2e'], edgecolor='#2d3748')
    axes[0, 0].set_ylabel('Percent (%)')
    axes[0, 0].set_title('Urban Fraction by Density Type', fontsize=11, fontweight='bold')
    axes[0, 0].tick_params(axis='x', rotation=15)
    for i, v in enumerate(pct_urban):
        axes[0, 0].text(i, v + 0.1, f'{v:.2f}%', ha='center', fontsize=9)

    axes[0, 1].bar(URBAN_TYPES, canyon_hwr, color='#805ad5', edgecolor='#2d3748')
    axes[0, 1].set_ylabel('Height/Width Ratio')
    axes[0, 1].set_title('Canyon Height-to-Width Ratio', fontsize=11, fontweight='bold')
    axes[0, 1].tick_params(axis='x', rotation=15)

    axes[0, 2].bar(URBAN_TYPES, ht_roof, color='#3182ce', edgecolor='#2d3748')
    axes[0, 2].set_ylabel('Height (m)')
    axes[0, 2].set_title('Roof Height', fontsize=11, fontweight='bold')
    axes[0, 2].tick_params(axis='x', rotation=15)

    axes[1, 0].bar(URBAN_TYPES, t_building - 273.15, color='#e53e3e', edgecolor='#2d3748')
    axes[1, 0].set_ylabel('Temperature (\u00b0C)')
    axes[1, 0].set_title('Min. Building Interior Temp.', fontsize=11, fontweight='bold')
    axes[1, 0].tick_params(axis='x', rotation=15)

    x = np.arange(len(URBAN_TYPES))
    width = 0.35
    axes[1, 1].bar(x - width/2, wtlunit_roof, width, label='Roof Fraction', color='#805ad5', edgecolor='#2d3748')
    axes[1, 1].bar(x + width/2, wtroad_perv,  width, label='Pervious Road Fraction', color='#38a169', edgecolor='#2d3748')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[1, 1].set_ylabel('Fraction')
    axes[1, 1].set_title('Urban Surface Fractions', fontsize=11, fontweight='bold')
    axes[1, 1].legend(fontsize=8)

    axes[1, 2].bar(x - width/2, thick_roof, width, label='Roof Thickness', color='#4299e1', edgecolor='#2d3748')
    axes[1, 2].bar(x + width/2, thick_wall, width, label='Wall Thickness', color='#ed8936', edgecolor='#2d3748')
    axes[1, 2].set_xticks(x)
    axes[1, 2].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[1, 2].set_ylabel('Thickness (m)')
    axes[1, 2].set_title('Building Element Thickness', fontsize=11, fontweight='bold')
    axes[1, 2].legend(fontsize=8)

    lbl_suffix = ' (domain mean)' if is_regional else ''
    fig.suptitle(f'Urban Parameters{lbl_suffix}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '07_urban_basic.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section7_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': ('Basic urban parameters for three density classes (domain-mean values shown for regional grids).'
                    if is_regional else
                    'Basic urban parameters for three density classes.'),
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    # Urban radiative properties
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    em_labels = ['Impervious Road', 'Pervious Road', 'Roof', 'Wall']
    em_data   = [em_improad, em_perroad, em_roof, em_wall]

    x = np.arange(len(URBAN_TYPES))
    width = 0.2
    colors = plt.cm.Set2(np.linspace(0, 1, 4))

    for i, (data, label, color) in enumerate(zip(em_data, em_labels, colors)):
        axes[0, 0].bar(x + (i - 1.5) * width, data, width, label=label, color=color, edgecolor='#2d3748')

    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[0, 0].set_ylabel('Emissivity')
    axes[0, 0].set_title('Surface Emissivities', fontsize=11, fontweight='bold')
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].set_ylim(0, 1)

    # Direct albedos (VIS band)
    alb_vars_dir = ['ALB_IMPROAD_DIR', 'ALB_PERROAD_DIR', 'ALB_ROOF_DIR', 'ALB_WALL_DIR']
    alb_data_dir = []
    for v in alb_vars_dir:
        data = np.array(nc.variables[v][:], dtype=float)
        if is_regional:
            # domain mean over (numurbl, lat, lon): axis 0 = numrad, 1 = numurbl
            alb_data_dir.append(np.array([
                float(np.nanmean(np.where(land_mask, data[0, i, :, :], np.nan)))
                for i in range(len(URBAN_TYPES))
            ]))
        else:
            alb_data_dir.append(data[0, :, 0, 0])  # VIS band

    for i, (data, label, color) in enumerate(zip(alb_data_dir, em_labels, colors)):
        axes[0, 1].bar(x + (i - 1.5) * width, data, width, label=label, color=color, edgecolor='#2d3748')

    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[0, 1].set_ylabel('Albedo (VIS)')
    axes[0, 1].set_title('Direct Albedo (Visible Band)', fontsize=11, fontweight='bold')
    axes[0, 1].legend(fontsize=8)

    # Thermal conductivity (first level)
    tk_vars = ['TK_ROOF', 'TK_WALL', 'TK_IMPROAD']
    tk_labels = ['Roof', 'Wall', 'Impervious Road']
    tk_data = []
    for v in tk_vars:
        d = np.array(nc.variables[v][:], dtype=float)
        if is_regional:
            tk_data.append(np.array([
                float(np.nanmean(np.where(land_mask, d[0, i, :, :], np.nan)))
                for i in range(len(URBAN_TYPES))
            ]))
        else:
            tk_data.append(d[0, :, 0, 0])

    for i, (data, label) in enumerate(zip(tk_data, tk_labels)):
        axes[1, 0].bar(x + (i - 1) * 0.25, data, 0.25, label=label,
                      color=plt.cm.coolwarm(i/2), edgecolor='#2d3748')

    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[1, 0].set_ylabel('Thermal Conductivity (W/m\u00b7K)')
    axes[1, 0].set_title('Thermal Conductivity (Layer 1)', fontsize=11, fontweight='bold')
    axes[1, 0].legend(fontsize=8)

    # Heat capacity (first level)
    cv_vars = ['CV_ROOF', 'CV_WALL', 'CV_IMPROAD']
    cv_labels = ['Roof', 'Wall', 'Impervious Road']
    cv_data = []
    for v in cv_vars:
        d = np.array(nc.variables[v][:], dtype=float)
        if is_regional:
            cv_data.append(np.array([
                float(np.nanmean(np.where(land_mask, d[0, i, :, :], np.nan)))
                for i in range(len(URBAN_TYPES))
            ]) / 1e6)
        else:
            cv_data.append(d[0, :, 0, 0] / 1e6)  # Convert to MJ for readability

    for i, (data, label) in enumerate(zip(cv_data, cv_labels)):
        axes[1, 1].bar(x + (i - 1) * 0.25, data, 0.25, label=label,
                      color=plt.cm.coolwarm(i/2), edgecolor='#2d3748')

    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(URBAN_TYPES, rotation=15)
    axes[1, 1].set_ylabel('Heat Capacity (MJ/m3*K)')
    axes[1, 1].set_title('Volumetric Heat Capacity (Layer 1)', fontsize=11, fontweight='bold')
    axes[1, 1].legend(fontsize=8)

    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '07b_urban_thermal.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section7_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Urban radiative and thermal properties: emissivities, albedos, thermal conductivity, and heat capacity.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'urban',
        'title': 'Urban Parameters',
        'description': 'Urban canyon and building parameters for three density classes. Important for urban energy balance simulations.',
        'figures': section7_figures
    })

    # =========================================================================
    # SECTION 8: Emission Factors and Other Parameters
    # =========================================================================
    print("Creating Section 8: Emission Factors and Other Parameters...")
    section8_figures = []

    ef_vars   = ['EF1_BTR', 'EF1_FET', 'EF1_FDT', 'EF1_SHR', 'EF1_GRS', 'EF1_CRP']
    ef_labels = ['Broadleaf Trees', 'Fineleaf Evergreen Trees', 'Fineleaf Deciduous Trees',
                 'Shrubs', 'Grasses', 'Crops']

    if is_regional:
        # Spatial maps of emission factors
        data_list   = [get_field_2d(nc.variables[v]) for v in ef_vars]
        fig = plot_map_grid(data_list, ef_labels, lons, lats,
                            'Isoprene Emission Factors \u2013 Spatial Distribution',
                            units='unitless', cmap='YlGn', ncols=3)
        pdf_path = os.path.join(pdf_dir, '08_emission_maps.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section8_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial maps of isoprene emission factors for the six vegetation functional types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Harvest maps
        harvest_vars   = ['CONST_HARVEST_VH1', 'CONST_HARVEST_VH2', 'CONST_HARVEST_SH1',
                          'CONST_HARVEST_SH2', 'CONST_HARVEST_SH3']
        harvest_labels = ['Primary Forest', 'Primary Non-Forest', 'Sec. Mature Forest',
                          'Sec. Young Forest', 'Sec. Non-Forest']
        harvest_data   = [get_field_2d(nc.variables[v]) for v in harvest_vars]
        fig = plot_map_grid(harvest_data, harvest_labels, lons, lats,
                            'Constant Harvest Rates \u2013 Spatial Distribution',
                            units='gC/m\u00b2/yr', cmap='YlOrBr', ncols=3)
        pdf_path = os.path.join(pdf_dir, '08b_harvest_maps.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section8_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial maps of constant harvest rates for different land cover types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        # Glacier elevation (domain-mean of PCT_GLC_MEC, GLC_MEC is 1-D)
        glc_mec      = get_1d_array(nc.variables['GLC_MEC'])
        pct_glc_data = np.array(nc.variables['PCT_GLC_MEC'][:], dtype=float)
        topo_glc_data = np.array(nc.variables['TOPO_GLC_MEC'][:], dtype=float)
        pct_glc_mec  = np.array([
            float(np.nanmean(np.where(land_mask, pct_glc_data[i], np.nan)))
            for i in range(pct_glc_data.shape[0])
        ])
        topo_glc_mec = np.array([
            float(np.nanmean(np.where(land_mask, topo_glc_data[i], np.nan)))
            for i in range(topo_glc_data.shape[0])
        ])

    else:
        ef_values = [get_scalar_value(nc.variables[v]) for v in ef_vars]

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        colors = plt.cm.Greens(np.linspace(0.3, 0.9, len(ef_vars)))
        axes[0].bar(ef_labels, ef_values, color=colors, edgecolor='#2d3748')
        axes[0].set_ylabel('Emission Factor')
        axes[0].set_title('Isoprene Emission Factors by Vegetation Type', fontsize=11, fontweight='bold')
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].set_yscale('log')
        for i, v in enumerate(ef_values):
            axes[0].text(i, v * 1.1, f'{v:.0f}', ha='center', fontsize=9)

        glc_mec      = get_1d_array(nc.variables['GLC_MEC'])
        pct_glc_mec  = get_1d_array(nc.variables['PCT_GLC_MEC'])
        topo_glc_mec = get_1d_array(nc.variables['TOPO_GLC_MEC'])

        ax2 = axes[1].twinx()
        x_glc = range(len(pct_glc_mec))
        axes[1].bar(x_glc, pct_glc_mec, color='#63b3ed', alpha=0.7, label='Glacier %', edgecolor='#2d3748')
        ax2.plot(x_glc, topo_glc_mec, 'ro-', label='Mean Elevation', linewidth=2, markersize=8)
        axes[1].set_xticks(x_glc)
        axes[1].set_xticklabels([f'{glc_mec[i]:.0f}-{glc_mec[i+1]:.0f}m' for i in range(len(glc_mec)-1)], rotation=45)
        axes[1].set_xlabel('Elevation Class')
        axes[1].set_ylabel('Glacier Percent (%)', color='#3182ce')
        ax2.set_ylabel('Mean Elevation (m)', color='red')
        axes[1].set_title('Glacier Elevation Classes', fontsize=11, fontweight='bold')
        axes[1].legend(loc='upper left')
        ax2.legend(loc='upper right')
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '08_emission_glacier.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section8_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Isoprene emission factors by vegetation type and glacier distribution across elevation classes.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

        harvest_vars   = ['CONST_HARVEST_VH1', 'CONST_HARVEST_VH2', 'CONST_HARVEST_SH1',
                          'CONST_HARVEST_SH2', 'CONST_HARVEST_SH3']
        harvest_labels = ['Primary Forest', 'Primary Non-Forest', 'Secondary Mature Forest',
                          'Secondary Young Forest', 'Secondary Non-Forest']
        harvest_values = [get_scalar_value(nc.variables[v]) for v in harvest_vars]

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.YlOrBr(np.linspace(0.3, 0.9, len(harvest_vars)))
        ax.bar(harvest_labels, harvest_values, color=colors, edgecolor='#2d3748')
        ax.set_ylabel('Harvest Rate (gC/m\u00b2/yr)')
        ax.set_title('Constant Harvest Rates by Land Type', fontsize=12, fontweight='bold')
        ax.tick_params(axis='x', rotation=30)
        ax.grid(axis='y', alpha=0.3)
        for i, v in enumerate(harvest_values):
            if v > 0:
                ax.text(i, v + 10, f'{v:.1f}', ha='center', fontsize=9)
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '08b_harvest.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section8_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Constant harvest rates for different land cover types.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'other',
        'title': 'Emission Factors & Other Parameters',
        'description': 'Biogenic emission factors, glacier elevation classes, and harvest parameters.',
        'figures': section8_figures
    })

    # =========================================================================
    # SECTION 9: Summary Overview
    # =========================================================================
    print("Creating Section 9: Summary Overview...")
    section9_figures = []

    nc_basename_stem = os.path.splitext(os.path.basename(nc_file))[0]

    if is_regional:
        # Grid of key spatial maps
        summary_vars = [
            ('PCT_NATVEG',  'Natural Vegetation (%)',      'Greens'),
            ('PCT_CROP',    'Cropland (%)',                 'YlOrBr'),
            ('SOIL_COLOR',  'Soil Color Index',             'tab20b'),
            ('FMAX',        'Max Saturated Fraction',       'Blues'),
            ('zbedrock',    'Bedrock Depth (m)',            'copper'),
            ('peatf',       'Peatland Fraction',            'Greens'),
        ]
        data_list, titles_list, cmaps_list = [], [], []
        for var_name, title_str, cmap_str in summary_vars:
            if var_name in nc.variables:
                d = get_field_2d(nc.variables[var_name])
                if d.ndim == 2:
                    data_list.append(d)
                    titles_list.append(title_str)
                    cmaps_list.append(cmap_str)
        fig = plot_map_grid(data_list, titles_list, lons, lats,
                            f'Key Parameters Overview \u2013 {nc_basename_stem}',
                            units='', cmap=cmaps_list, ncols=3)
        pdf_path = os.path.join(pdf_dir, '09_summary.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section9_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Spatial overview of key surface data parameters.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    else:
        fig = plt.figure(figsize=(16, 12))

        ax1 = fig.add_subplot(2, 3, 1)
        land_labels = ['Natural Vegetation', 'Cropland', 'Urban', 'Lake', 'Wetland', 'Glacier']
        land_values = np.array([
            pct_natveg, pct_crop, np.sum(pct_urban),
            get_scalar_value(nc.variables['PCT_LAKE']),
            get_scalar_value(nc.variables['PCT_WETLAND']),
            get_scalar_value(nc.variables['PCT_GLACIER'])
        ])
        nonzero_land = land_values > 0.1
        ax1.pie(land_values[nonzero_land],
                labels=[l for l, m in zip(land_labels, nonzero_land) if m],
                autopct='%1.1f%%', colors=plt.cm.Set3(np.linspace(0, 1, sum(nonzero_land))))
        ax1.set_title('Land Cover Types', fontsize=11, fontweight='bold')

        ax2 = fig.add_subplot(2, 3, 2)
        mean_sand = float(np.mean(pct_sand))
        mean_clay = float(np.mean(pct_clay))
        mean_silt = 100 - mean_sand - mean_clay
        ax2.pie([mean_sand, mean_silt, mean_clay], labels=['Sand', 'Silt', 'Clay'],
                autopct='%1.1f%%', colors=['#f6ad55', '#a0aec0', '#fc8181'])
        ax2.set_title('Mean Soil Texture', fontsize=11, fontweight='bold')

        ax3 = fig.add_subplot(2, 3, 3)
        active_labels    = [all_pft_names.get(p, f'PFT {p}')[:20] for p in active_pfts[:8]]
        active_lai_mean  = [float(np.mean(lai_data[:, p, 0, 0])) for p in active_pfts[:8]]
        ax3.barh(range(len(active_labels)), active_lai_mean,
                 color=plt.cm.Greens(np.linspace(0.3, 0.9, max(len(active_labels), 1))))
        ax3.set_yticks(range(len(active_labels)))
        ax3.set_yticklabels(active_labels, fontsize=8)
        ax3.set_xlabel('Mean LAI')
        ax3.set_title('Top Active PFTs by LAI', fontsize=11, fontweight='bold')

        ax4 = fig.add_subplot(2, 3, (4, 6))
        ax4.axis('off')
        key_params = [
            ('Longitude',            f'{lon:.3f}\u00b0E'),
            ('Latitude',             f'{lat:.3f}\u00b0N'),
            ('Natural Vegetation',   f'{pct_natveg:.1f}%'),
            ('Cropland',             f'{pct_crop:.1f}%'),
            ('Urban (total)',         f'{float(np.sum(pct_urban)):.2f}%'),
            ('Bedrock Depth',        f'{get_scalar_value(nc.variables["zbedrock"]):.2f} m'),
            ('Slope',                f'{get_scalar_value(nc.variables["SLOPE"]):.2f}\u00b0'),
            ('Soil Color Index',     f'{int(get_scalar_value(nc.variables["SOIL_COLOR"]))}'),
            ('Max Saturated Frac.',  f'{get_scalar_value(nc.variables["FMAX"]):.3f}'),
            ('Peatland Fraction',    f'{get_scalar_value(nc.variables["peatf"]):.3f}'),
        ]
        table_data = [[p[0], p[1]] for p in key_params]
        table = ax4.table(cellText=table_data, colLabels=['Parameter', 'Value'],
                          loc='center', cellLoc='left', colWidths=[0.4, 0.3])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.8)
        for i in range(len(table_data) + 1):
            for j in range(2):
                cell = table[(i, j)]
                if i == 0:
                    cell.set_facecolor('#667eea')
                    cell.set_text_props(color='white', fontweight='bold')
                elif i % 2 == 0:
                    cell.set_facecolor('#f7fafc')
                else:
                    cell.set_facecolor('#edf2f7')
        ax4.set_title('Key Site Parameters Summary', fontsize=12, fontweight='bold', pad=20)

        fig.suptitle(f'Surface Data Overview \u2013 {nc_basename_stem}',
                     fontsize=16, fontweight='bold')
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '09_summary.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section9_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Comprehensive summary of key surface data parameters.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'summary',
        'title': 'Summary Overview',
        'description': 'A comprehensive overview combining key parameters for quick reference.',
        'figures': section9_figures
    })

    # Close NetCDF file
    nc.close()

    # Generate HTML report
    print("Generating HTML report...")
    html_file = create_html_report(figures_data, nc_file, output_dir, metadata_str)

    print(f"\nVisualization complete!")
    print(f"PDF figures saved in: {pdf_dir}")
    print(f"HTML report saved as: {html_file}")

    return html_file


if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Default to the NC file in the same directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        nc_file = os.path.join(script_dir, 'surfdata_BE-Lon_hist_78pfts_CMIP6_simyr2005_c260203.nc')
        if not os.path.exists(nc_file):
            print("Usage: python visualize_surfdata.py <surfdata_nc_file>")
            print("No default file found.")
            sys.exit(1)
    else:
        nc_file = sys.argv[1]

    main(nc_file)
