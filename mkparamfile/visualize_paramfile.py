#!/usr/bin/env python3
"""
CLM5 Parameter File Visualization Script
=========================================
Reads a CLM5 NetCDF parameter file and creates comprehensive visualizations
for all parameter groups, generating an HTML report with embedded figures and
downloadable PDFs.

Usage: python visualize_paramfile.py <paramfile.nc>
"""

import os
import sys
import io
import math
import base64
from datetime import datetime, date as _date

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from matplotlib.patches import Patch
from netCDF4 import Dataset


# ---------------------------------------------------------------------------
# PFT name catalogue
# Sources (official CLM5 documentation):
#   NATPFT (Table 2.2.1):
#     https://escomp.github.io/CTSM/release-clm5.0/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html#id15
#   CFT (Table 2.26.1):
#     https://escomp.github.io/CTSM/release-clm5.0/tech_note/Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html#id20
# Fetched at import time (3 s timeout); falls back to hardcoded values offline.
# ---------------------------------------------------------------------------

def _fetch_pft_names_from_docs():
    import urllib.request
    from html.parser import HTMLParser

    class _TableParser(HTMLParser):
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
                pass
        return result if result else None

    natpft = _parse(
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Ecosystem/CLM50_Tech_Note_Ecosystem.html",
        table_id="id15",
    )
    cft = _parse(
        "https://escomp.github.io/CTSM/release-clm5.0/tech_note/"
        "Crop_Irrigation/CLM50_Tech_Note_Crop_Irrigation.html",
        table_id="id20",
    )
    return natpft, cft


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

N_NAT = 15  # natural PFT indices 0–14


# ---------------------------------------------------------------------------
# Low-level utilities
# ---------------------------------------------------------------------------

def fig_to_base64(fig):
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def save_pdf_and_b64(fig, pdf_path):
    """Save *fig* as a PDF at *pdf_path* and return a base64 PNG string."""
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
    b64 = fig_to_base64(fig)
    plt.close(fig)
    return b64


def get_var(nc, name):
    """Return variable *name* from *nc* as a float64 ndarray (fill → NaN).
    Returns None if the variable is not present.

    Special case: CLM5 uses _FillValue = 0. as an "not applicable" sentinel
    for many per-PFT parameters (e.g. laimx, hybgdd).  If we converted those
    masked zeros to NaN the bars would vanish even when the stored value is a
    legitimate 0.  So when _FillValue == 0 we keep masked values as 0.0
    instead of NaN; only large sentinel fills (-999, 9999 …) become NaN."""
    if name not in nc.variables:
        return None
    var = nc.variables[name]
    data = var[:].astype(float)
    if hasattr(data, 'mask'):
        fill_val = getattr(var, '_FillValue', None)
        if fill_val is not None and float(fill_val) == 0.0:
            data = np.ma.filled(data, 0.0)
        else:
            data = np.ma.filled(data, np.nan)
    return np.squeeze(data)


def _attr(nc, varname, attrname, default=''):
    """Safely read a NetCDF variable attribute."""
    if varname in nc.variables:
        return getattr(nc.variables[varname], attrname, default)
    return default


def get_pft_names_from_file(nc):
    """Read the pftname char array from *nc*. Returns a list of 79 strings."""
    if 'pftname' not in nc.variables:
        all_names = {**NATPFT_NAMES, **CFT_NAMES}
        return [all_names.get(i, f'PFT {i}') for i in range(79)]
    raw = nc.variables['pftname'][:]
    names = []
    for i in range(raw.shape[0]):
        row = raw[i]
        if hasattr(row, 'data'):
            row = row.data
        name = ''.join(
            c.decode('utf-8', errors='replace') if isinstance(c, bytes) else str(c)
            for c in row
        ).strip()
        names.append(name)
    return names


def get_pft_short(pft_names, max_len=22):
    """Return short y-axis labels: '{index}: {name[:max_len]}'."""
    return [f'{i}: {name[:max_len]}' for i, name in enumerate(pft_names)]


def get_segment_names(nc):
    """Read segment char array; fallback to generic labels."""
    if 'segment' not in nc.variables:
        return ['Root', 'Stem', 'Branch', 'Leaf']
    raw = nc.variables['segment'][:]
    names = []
    for i in range(raw.shape[0]):
        row = raw[i]
        if hasattr(row, 'data'):
            row = row.data
        name = ''.join(
            c.decode('utf-8', errors='replace') if isinstance(c, bytes) else str(c)
            for c in row
        ).strip()
        names.append(name if name else f'Seg {i}')
    return names


def _collect_scalar_rows(nc, names):
    """Return list of (varname, value_str, units, long_name) for allpfts/scalar vars."""
    rows = []
    for name in names:
        v = get_var(nc, name)
        if v is None:
            continue
        val = float(np.squeeze(v))
        units    = _attr(nc, name, 'units',     '–')
        longname = _attr(nc, name, 'long_name', name)
        rows.append((name, f'{val:.6g}', units, longname))
    return rows


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _pft_colors(n_pfts, n_nat=N_NAT):
    return ['#3182ce'] * n_nat + ['#68d391'] * max(0, n_pfts - n_nat)


# ---------------------------------------------------------------------------
# Date helpers  (YYYYMMDD ↔ day-of-year, like ESMF TimeSetymd)
# ---------------------------------------------------------------------------

# Day-of-year of the 1st of each month in a non-leap reference year.
_MONTH_STARTS_DOY = [_date(2001, m, 1).timetuple().tm_yday for m in range(1, 13)]
_MONTH_NAMES      = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def yyyymmdd_to_doy(arr):
    """Convert YYYYMMDD integer array → day-of-year (1–365, non-leap ref year).

    Mirrors the ESMF TimeSetymd decomposition (yy=YYYY//10000, mm=MM, dd=DD).
    The year component is ignored because these values represent seasonal
    calendar windows, not absolute dates.  0 / fill values → NaN.
    """
    arr = np.asarray(arr, dtype=float)
    result = np.full(len(arr), np.nan)
    for i, v in enumerate(arr):
        if np.isnan(v) or v <= 0:
            continue
        iv = int(v)
        mm = (iv % 10000) // 100
        dd = iv % 100
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            try:
                result[i] = _date(2001, mm, dd).timetuple().tm_yday
            except ValueError:
                pass  # invalid date (e.g. Feb 30) → NaN
    return result


def doy_month_ticks():
    """Return (tick_positions, tick_labels) for a full-year DOY x-axis."""
    return _MONTH_STARTS_DOY, _MONTH_NAMES


def yyyymmdd_to_str(ival):
    """Format an YYYYMMDD integer as 'Mon DD' (e.g. 20010315 → 'Mar 15').
    Returns '' for 0 or invalid values."""
    if ival <= 0:
        return ''
    iv = int(ival)
    mm = (iv % 10000) // 100
    dd = iv % 100
    if 1 <= mm <= 12 and 1 <= dd <= 31:
        return f'{_MONTH_NAMES[mm - 1]} {dd:02d}'
    return ''


def make_pft_bar_fig(nc, var_specs, pft_labels, title, n_nat=N_NAT):
    """
    Horizontal bar chart figure for per-PFT variables.

    var_specs : list of (varname, display_title, units)
    Returns a matplotlib Figure.
    """
    n = len(var_specs)
    ncols = min(n, 3)
    nrows = math.ceil(n / ncols)
    n_pfts = len(pft_labels)
    col_w = 8
    row_h = max(10, n_pfts * 0.20 + 1.2)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(col_w * ncols, row_h * nrows),
                             constrained_layout=True)
    if n == 1:
        axes_flat = [axes]
    elif nrows == 1:
        axes_flat = list(axes)
    else:
        axes_flat = [ax for row in axes for ax in row]

    colors = _pft_colors(n_pfts, n_nat)
    y_pos  = np.arange(n_pfts)

    for idx, (varname, display_name, units) in enumerate(var_specs):
        ax = axes_flat[idx]
        vals = get_var(nc, varname)
        if vals is None:
            ax.text(0.5, 0.5, f'{varname}\n(not in file)',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=9, color='#718096')
            ax.set_title(display_name, fontsize=9, fontweight='bold')
            ax.axis('off')
            continue

        v1d = np.atleast_1d(vals)[:n_pfts]
        v_disp = np.where(np.isnan(v1d), 0.0, v1d)

        ax.barh(y_pos, v_disp, color=colors[:len(y_pos)],
                edgecolor='none', height=0.78, alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(pft_labels[:len(y_pos)], fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlabel(units, fontsize=8)
        ax.set_title(f'{display_name}\n({varname})', fontsize=9, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        if n_nat < len(v_disp):
            ax.axhline(n_nat - 0.5, color='#a0aec0', linewidth=1.2, linestyle='--')

    for idx in range(n, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.legend(handles=[
        Patch(facecolor='#3182ce', label=f'Natural PFTs (0–{n_nat - 1})'),
        Patch(facecolor='#68d391', label=f'Crop PFTs ({n_nat}–{n_pfts - 1})'),
    ], loc='upper right', fontsize=8, bbox_to_anchor=(1.0, 1.0))
    fig.suptitle(title, fontsize=12, fontweight='bold')
    return fig


def make_flag_heatmap(flag_data, flag_names, pft_labels, title):
    """Binary flag heatmap: rows = PFTs, columns = flags."""
    n_pfts  = len(pft_labels)
    n_flags = len(flag_names)
    fig_h = max(10, n_pfts * 0.22 + 2.0)
    fig_w = max(8,  n_flags * 1.3 + 2.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), constrained_layout=True)

    mat = np.zeros((n_pfts, n_flags))
    for j, fname in enumerate(flag_names):
        v = flag_data.get(fname)
        if v is not None:
            v1d = np.atleast_1d(v)[:n_pfts]
            mat[:len(v1d), j] = np.where(np.isnan(v1d), 0, v1d)

    im = ax.imshow(mat, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1,
                   interpolation='nearest')
    ax.set_xticks(range(n_flags))
    ax.set_xticklabels(flag_names, rotation=40, ha='right', fontsize=9)
    ax.set_yticks(range(n_pfts))
    ax.set_yticklabels(pft_labels, fontsize=6.5)
    ax.set_title(title, fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.5, label='Flag value (0 = off, 1 = on)')
    if N_NAT < n_pfts:
        ax.axhline(N_NAT - 0.5, color='white', linewidth=2, linestyle='--')
    return fig


def make_stacked_bar_fig(nc, fraction_groups, pft_labels, title):
    """
    Stacked horizontal bar chart for fraction-groups.

    fraction_groups : list of (group_title, [(varname, label, color), ...])
    """
    n_groups = len(fraction_groups)
    n_pfts   = len(pft_labels)
    row_h    = max(10, n_pfts * 0.20 + 1.2)
    fig, axes = plt.subplots(1, n_groups,
                             figsize=(8 * n_groups, row_h),
                             constrained_layout=True)
    if n_groups == 1:
        axes = [axes]

    for ax, (group_title, components) in zip(axes, fraction_groups):
        y_pos = np.arange(n_pfts)
        left  = np.zeros(n_pfts)
        for varname, label, color in components:
            vals = get_var(nc, varname)
            if vals is None:
                vals = np.zeros(n_pfts)
            v1d = np.atleast_1d(vals)[:n_pfts]
            v1d = np.where(np.isnan(v1d), 0.0, v1d)
            ax.barh(y_pos, v1d, left=left, height=0.78,
                    color=color, label=label, alpha=0.9, edgecolor='none')
            left += v1d
        ax.set_yticks(y_pos)
        ax.set_yticklabels(pft_labels, fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlabel('Fraction', fontsize=9)
        ax.set_title(group_title, fontsize=10, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        ax.set_xlim(0, 1.05)
        ax.legend(fontsize=8, loc='lower right')
        if N_NAT < n_pfts:
            ax.axhline(N_NAT - 0.5, color='#a0aec0', linewidth=1.2, linestyle='--')

    fig.suptitle(title, fontsize=12, fontweight='bold')
    return fig


def make_2d_heatmap(data, row_labels, col_labels, title, units):
    """Heatmap for 2-D variables (segments × PFTs or variants × PFTs)."""
    n_rows, n_cols = data.shape
    fig_w = max(14, n_cols * 0.22 + 3)
    fig_h = max(4,  n_rows * 1.5  + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), constrained_layout=True)
    d_plot = np.where(np.isnan(data), 0.0, data)
    im = ax.imshow(d_plot, aspect='auto', cmap='viridis', interpolation='nearest')
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels, fontsize=9)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, rotation=90, fontsize=6)
    ax.set_title(f'{title} [{units}]', fontsize=11, fontweight='bold')
    plt.colorbar(im, ax=ax, shrink=0.7, label=units)
    if N_NAT < n_cols:
        ax.axvline(N_NAT - 0.5, color='white', linewidth=1.5, linestyle='--')
    return fig


def make_scalar_table_fig(rows, title,
                           col_labels=('Parameter', 'Value', 'Units', 'Description')):
    """Table figure for allpfts / scalar parameters."""
    n_rows = len(rows)
    fig_h  = max(3, n_rows * 0.33 + 1.5)
    fig, ax = plt.subplots(figsize=(18, fig_h), constrained_layout=True)
    ax.axis('off')
    col_widths = [0.12, 0.10, 0.10, 0.68]
    tbl = ax.table(
        cellText=rows, colLabels=col_labels,
        colWidths=col_widths, loc='center', cellLoc='left',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.4)
    for j in range(len(col_labels)):
        tbl[(0, j)].set_facecolor('#2d3748')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    for i in range(1, n_rows + 1):
        bg = '#f7fafc' if i % 2 == 0 else 'white'
        for j in range(len(col_labels)):
            tbl[(i, j)].set_facecolor(bg)
    ax.set_title(title, fontsize=11, fontweight='bold', pad=8)
    return fig


def make_scalar_cards_fig(cards):
    """Card display for a handful of dimensionless scalar parameters."""
    n = len(cards)
    ncols = min(n, 4)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3 * nrows),
                             constrained_layout=True)
    if n == 1:
        axes_flat = [axes]
    elif nrows == 1:
        axes_flat = list(axes)
    else:
        axes_flat = [ax for row in axes for ax in row]

    for idx, (name, value, units, long_name) in enumerate(cards):
        ax = axes_flat[idx]
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        rect = mpatches.FancyBboxPatch(
            (0.3, 0.3), 9.4, 9.4, boxstyle="round,pad=0.1",
            facecolor='#f0f4f8', edgecolor='#2c5282', linewidth=2)
        ax.add_patch(rect)
        ax.text(5, 8.2, name,           ha='center', va='center', fontsize=11,
                fontweight='bold', color='#2d3748')
        ax.text(5, 5.8, f'{value:.6g}', ha='center', va='center', fontsize=16,
                fontweight='bold', color='#2b6cb0')
        ax.text(5, 4.0, f'[{units}]',  ha='center', va='center', fontsize=9,
                color='#4a5568')
        # Wrap long_name manually at 40 chars
        wrap = long_name
        if len(wrap) > 40:
            mid = wrap.rfind(' ', 0, 40)
            wrap = wrap[:mid] + '\n' + wrap[mid + 1:] if mid > 0 else wrap[:40] + '\n' + wrap[40:]
        ax.text(5, 2.2, wrap, ha='center', va='center', fontsize=7,
                color='#718096', multialignment='center')

    for idx in range(n, len(axes_flat)):
        axes_flat[idx].set_visible(False)
    return fig


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif;
          background: linear-gradient(135deg, #1a365d 0%, #2d3748 100%);
          min-height: 100vh; margin: 0; padding: 20px; }}
  .container {{ max-width: 1400px; margin: 0 auto; background: white;
                border-radius: 16px; padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
  h1 {{ color: #2d3748; font-size: 2rem; margin-bottom: 8px; }}
  h2 {{ color: #2b6cb0; font-size: 1.4rem;
        border-bottom: 3px solid #4299e1; padding-bottom: 8px; margin-top: 0; }}
  .meta {{ background: #ebf8ff; padding: 16px; border-radius: 8px;
           margin-bottom: 24px; border-left: 4px solid #3182ce; }}
  .meta p {{ margin: 4px 0; color: #2d3748; font-size: 0.9rem; }}
  nav.toc {{ background: #f7fafc; border: 1px solid #e2e8f0;
             border-radius: 8px; padding: 16px 24px; margin-bottom: 28px; }}
  nav.toc h3 {{ margin: 0 0 10px; color: #2d3748; font-size: 1rem; }}
  nav.toc ul {{ margin: 0; padding: 0 0 0 20px; column-count: 2; }}
  nav.toc li {{ padding: 3px 0; }}
  nav.toc a {{ color: #2b6cb0; text-decoration: none; font-size: 0.9rem; }}
  nav.toc a:hover {{ text-decoration: underline; }}
  .section {{ background: #f7fafc; border-radius: 12px; padding: 24px;
              margin-bottom: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .section-desc {{ color: #4a5568; font-size: 0.9rem;
                   margin-bottom: 16px; line-height: 1.6; }}
  .figure-wrap {{ margin-bottom: 20px; }}
  .figure-wrap img {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; }}
  .figure-caption {{ color: #4a5568; font-size: 0.85rem; margin: 6px 0 4px; }}
  .dl-btn {{ display: inline-block; background: #2b6cb0; color: white;
             padding: 5px 14px; border-radius: 6px; text-decoration: none;
             font-size: 0.8rem; margin-top: 4px; }}
  .dl-btn:hover {{ background: #2c5282; }}
  @media (max-width: 768px) {{ nav.toc ul {{ column-count: 1; }} }}
</style>
</head>
<body>
<div class="container">
  <h1>{title}</h1>
  <div class="meta">
    <p><strong>File:</strong> {filename}</p>
    <p><strong>Generated:</strong> {timestamp}</p>
    {extra_meta}
  </div>
  <nav class="toc">
    <h3>Quick Navigation</h3>
    <ul>{nav_links}</ul>
  </nav>
  {sections}
</div>
</body>
</html>
"""


def _build_html(title, filename, extra_meta, figures_data):
    nav_links = ""
    sections_html = ""
    for s in figures_data:
        nav_links += f'<li><a href="#{s["id"]}">{s["title"]}</a></li>\n'
        figs_html = ""
        for f in s['figures']:
            figs_html += (
                f'  <div class="figure-wrap">\n'
                f'    <img src="data:image/png;base64,{f["b64"]}" alt="{f["caption"]}">\n'
                f'    <p class="figure-caption">{f["caption"]}</p>\n'
                f'    <a class="dl-btn" href="{f["pdf_name"]}" download>Download PDF</a>\n'
                f'  </div>\n'
            )
        sections_html += (
            f'<section class="section" id="{s["id"]}">\n'
            f'  <h2>{s["title"]}</h2>\n'
            f'  <p class="section-desc">{s.get("description", "")}</p>\n'
            f'  {figs_html}\n'
            f'</section>\n'
        )
    return _HTML.format(
        title=title, filename=filename,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
        extra_meta=extra_meta, nav_links=nav_links, sections=sections_html,
    )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main(nc_file):
    print(f"Reading {nc_file} …")
    nc = Dataset(nc_file, 'r')

    nc_basename = os.path.basename(nc_file)
    stem    = nc_basename[:-3] if nc_basename.endswith('.nc') else nc_basename
    out_dir = os.path.join(os.path.dirname(os.path.abspath(nc_file)), stem + '_figures')
    os.makedirs(out_dir, exist_ok=True)

    pft_names_full = get_pft_names_from_file(nc)
    n_pfts         = len(pft_names_full)
    pft_short      = get_pft_short(pft_names_full)
    seg_names      = get_segment_names(nc)

    figures_data = []
    _ctr = [0]

    def _pdf(name):
        path = os.path.join(out_dir, f'{_ctr[0]:02d}_{name}.pdf')
        _ctr[0] += 1
        return path

    def _rel(pdf_path):
        return os.path.relpath(pdf_path, os.path.dirname(os.path.abspath(nc_file)))

    def _fig(section_list, b64, caption, pdf_path):
        section_list.append({'b64': b64, 'caption': caption, 'pdf_name': _rel(pdf_path)})

    # -----------------------------------------------------------------------
    # 0. PFT Catalogue
    # -----------------------------------------------------------------------
    print("  0. PFT Catalogue")
    s0 = []

    # PFT names table (blue rows = natural, white rows = crop)
    tbl_rows = [(str(i), pft_names_full[i] if i < len(pft_names_full) else '')
                for i in range(n_pfts)]
    fig_h = max(8, n_pfts * 0.28 + 2)
    fig0a, ax0a = plt.subplots(figsize=(14, fig_h), constrained_layout=True)
    ax0a.axis('off')
    tbl = ax0a.table(cellText=tbl_rows, colLabels=['Index', 'PFT Name'],
                     colWidths=[0.08, 0.92], loc='center', cellLoc='left')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.3)
    for j in range(2):
        tbl[(0, j)].set_facecolor('#2d3748')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    for i in range(1, n_pfts + 1):
        bg = ('#ebf8ff' if i % 2 == 0 else '#bee3f8') if i <= N_NAT \
             else ('#f7fafc' if i % 2 == 0 else 'white')
        for j in range(2):
            tbl[(i, j)].set_facecolor(bg)
    ax0a.set_title('Plant Functional Types (79 PFTs) — blue = natural, white = crop',
                   fontsize=12, fontweight='bold')
    p = _pdf('pft_catalogue')
    _fig(s0, save_pdf_and_b64(fig0a, p), 'All 79 PFTs (blue = natural PFTs 0–14, white = crop PFTs 15–78)', p)

    # Binary flag heatmap
    flag_vars = ['c3psn', 'crop', 'irrigated', 'woody', 'evergreen',
                 'season_decid', 'stress_decid', 'perennial', 'covercrop']
    flag_data = {v: get_var(nc, v) for v in flag_vars}
    fig0b = make_flag_heatmap(flag_data, flag_vars, pft_short, 'PFT Binary Flags')
    p = _pdf('pft_flags')
    _fig(s0, save_pdf_and_b64(fig0b, p), 'Binary classification flags for all 79 PFTs (green = 1, red = 0)', p)

    figures_data.append({
        'id': 'pft-catalogue', 'title': '0. PFT Catalogue',
        'description': (
            'Complete list of all 79 Plant Functional Types and their binary '
            'classification flags: C₃/C₄ photosynthesis (c3psn), crop status, '
            'irrigation, woody lifeform, leaf habit (evergreen / seasonally deciduous '
            '/ stress deciduous), and agricultural flags (perennial, covercrop).'
        ),
        'figures': s0,
    })

    # -----------------------------------------------------------------------
    # 1. Leaf & Canopy Optical Properties
    # -----------------------------------------------------------------------
    print("  1. Optical Properties")
    s1 = []

    for specs, fname, cap in [
        ([('rholvis', 'Leaf reflectance: visible',  'fraction'),
          ('rholnir', 'Leaf reflectance: near-IR',  'fraction'),
          ('rhosvis', 'Stem reflectance: visible',  'fraction'),
          ('rhosnir', 'Stem reflectance: near-IR',  'fraction')],
         'reflectance',
         'Leaf and stem reflectance in visible and near-infrared bands'),
        ([('taulvis', 'Leaf transmittance: visible', 'fraction'),
          ('taulnir', 'Leaf transmittance: near-IR', 'fraction'),
          ('tausvis', 'Stem transmittance: visible', 'fraction'),
          ('tausnir', 'Stem transmittance: near-IR', 'fraction')],
         'transmittance',
         'Leaf and stem transmittance in visible and near-infrared bands'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s1, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'optical', 'title': '1. Leaf & Canopy Optical Properties',
        'description': (
            'Reflectance and transmittance of leaf and stem tissue in visible (VIS) '
            'and near-infrared (NIR) bands. These parameters control radiative '
            'transfer through the canopy and are used in the two-stream approximation.'
        ),
        'figures': s1,
    })

    # -----------------------------------------------------------------------
    # 2. Canopy Structure & Gas Exchange
    # -----------------------------------------------------------------------
    print("  2. Canopy Structure")
    s2 = []

    for specs, fname, cap in [
        ([('slatop',    'Specific Leaf Area (top)',        'm²/gC'),
          ('dsladlai',  'dSLA/dLAI',                      'm²/gC'),
          ('laimx',     'Max LAI',                         '–'),
          ('dleaf',     'Characteristic leaf dimension',   'm')],
         'canopy_structure_a',
         'Specific leaf area, maximum LAI, and leaf dimension'),
        ([('xl',        'Leaf/stem orientation index',     '–'),
          ('z0mr',      'z₀ / canopy height ratio',        '–'),
          ('displar',   'Displacement height ratio',       '–'),
          ('ztopmx',    'Canopy top coefficient',          'm')],
         'canopy_structure_b',
         'Canopy geometry and momentum roughness parameters'),
        ([('mbbopt',          'Ball-Berry slope (unstressed)',   'umol H₂O/umol CO₂'),
          ('medlynslope',     'Medlyn slope',                    'umol H₂O/umol CO₂'),
          ('medlynintercept', 'Medlyn intercept',                'umol H₂O'),
          ('flnr',            'Fraction leaf N in Rubisco',      'fraction')],
         'gas_exchange',
         'Stomatal conductance model parameters (Ball-Berry, Medlyn) and Rubisco N fraction'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s2, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'canopy', 'title': '2. Canopy Structure & Gas Exchange',
        'description': (
            'Leaf and canopy geometry (SLA, LAI, orientation index, displacement height, '
            'roughness length), and stomatal conductance parameters (Ball-Berry and Medlyn '
            'models) controlling CO₂ and water vapour exchange with the atmosphere.'
        ),
        'figures': s2,
    })

    # -----------------------------------------------------------------------
    # 3. Carbon Allocation
    # -----------------------------------------------------------------------
    print("  3. Carbon Allocation")
    s3 = []

    for specs, fname, cap in [
        ([('froot_leaf', 'Fine root C / leaf C',          'gC/gC'),
          ('stem_leaf',  'Stem C / leaf C',               'gC/gC'),
          ('croot_stem', 'Coarse root C / stem C',        'gC/gC'),
          ('flivewd',    'Fraction live wood',             'fraction'),
          ('fcur',       'Current growth fraction',        'fraction'),
          ('grperc',     'Growth respiration factor',      '–')],
         'allocation_ratios',
         'Carbon allocation ratios between organs'),
        ([('aleaff',    'Leaf alloc. coefficient',        '–'),
          ('arootf',    'Root alloc. coefficient',        '–'),
          ('arooti',    'Root alloc. coeff. i',           '–'),
          ('astemf',    'Stem alloc. coefficient',        '–'),
          ('bfact',     'Leaf fraction exponent',         '–'),
          ('allconsl',  'Leaf alloc. power',              '–')],
         'allocation_shape',
         'Allometric allocation shape parameters (coefficients and exponents)'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s3, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'allocation', 'title': '3. Carbon Allocation',
        'description': (
            'Parameters controlling how newly assimilated carbon is distributed among '
            'plant organs (leaf, fine root, stem, coarse root). Includes allocation '
            'ratios and the allometric shape parameters (a, b exponents) used in '
            'CNAllocation.'
        ),
        'figures': s3,
    })

    # -----------------------------------------------------------------------
    # 4. C:N Stoichiometry
    # -----------------------------------------------------------------------
    print("  4. C:N Stoichiometry")
    s4 = []

    for specs, fname, cap in [
        ([('leafcn',     'Leaf C:N',             'gC/gN'),
          ('leafcn_min', 'Leaf C:N min',          'gC/gN'),
          ('leafcn_max', 'Leaf C:N max',          'gC/gN'),
          ('fleafcn',    'Leaf C:N organ fill',   'gC/gN')],
         'cn_leaf',
         'Leaf C:N ratios (mean, min, max, and organ-fill)'),
        ([('frootcn',       'Fine root C:N',      'gC/gN'),
          ('frootcn_min',   'Fine root C:N min',  'gC/gN'),
          ('frootcn_max',   'Fine root C:N max',  'gC/gN'),
          ('livewdcn',      'Live wood C:N',      'gC/gN'),
          ('deadwdcn',      'Dead wood C:N',      'gC/gN'),
          ('lflitcn',       'Leaf litter C:N',    'gC/gN')],
         'cn_root_wood',
         'Fine root, live/dead wood, and leaf litter C:N ratios'),
        ([('graincn',   'Grain C:N (crop)',         'gC/gN'),
          ('ffrootcn',  'Fine root C:N organ fill', 'gC/gN'),
          ('fstemcn',   'Stem C:N organ fill',      'gC/gN')],
         'cn_grain_fill',
         'C:N during organ fill and grain (primarily crop PFTs)'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s4, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'cn-stoichiometry', 'title': '4. C:N Stoichiometry',
        'description': (
            'Carbon-to-nitrogen ratios for leaf, fine root, live/dead wood, litter, '
            'and grain. These parameters govern nutrient limitation of photosynthesis, '
            'decomposition, and N cycling fluxes.'
        ),
        'figures': s4,
    })

    # -----------------------------------------------------------------------
    # 5. Phenology
    # -----------------------------------------------------------------------
    print("  5. Phenology")
    s5 = []

    for specs, fname, cap in [
        ([('hybgdd',   'GDD for maturity',           '°C·days'),
          ('grnfill',  'Grain fill parameter',        '–'),
          ('gddmin',   'Min GDD',                     '–'),
          ('lfemerg',  'Leaf emergence parameter',    '–'),
          ('mxmat',    'Max days to maturity',        'days'),
          ('lfmat',    'GDD for canopy maturity',     '–')],
         'phenology_gdd',
         'Growing degree day parameters for crop phenological stages'),
        ([('baset',           'Base temperature',             '°C'),
          ('mxtmp',           'Max temperature',              '°C'),
          ('planting_temp',   'Planting temp (10-day avg)',   'K'),
          ('min_planting_temp', 'Min planting temp (5-day min)', 'K')],
         'phenology_temp',
         'Temperature thresholds for phenological onset, planting, and senescence'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s5, save_pdf_and_b64(fig, p), cap, p)

    # Planting & harvest dates (YYYYMMDD → day-of-year with month-name axis)
    # Layout: 3 rows (min planting / max planting / max harvest) × 2 cols (NH / SH)
    date_grid = [
        ('Minimum planting date',
         'min_NH_planting_date', 'min_SH_planting_date'),
        ('Maximum planting date',
         'max_NH_planting_date', 'max_SH_planting_date'),
        ('Maximum harvest date',
         'max_NH_harvest_date',  'max_SH_harvest_date'),
    ]
    fig5d, axes5d = plt.subplots(
        3, 2, figsize=(16, max(10, n_pfts * 0.20 + 1) * 3),
        constrained_layout=True)
    colors_pft  = _pft_colors(n_pfts)
    tick_pos, tick_lbl = doy_month_ticks()
    y_pos = np.arange(n_pfts)

    for row, (row_title, nh_var, sh_var) in enumerate(date_grid):
        for col, (varname, hem) in enumerate([(nh_var, 'NH'), (sh_var, 'SH')]):
            ax = axes5d[row, col]
            vals = get_var(nc, varname)
            if vals is not None:
                v1d  = np.atleast_1d(vals)[:n_pfts]
                doys = yyyymmdd_to_doy(v1d)
                valid = ~np.isnan(doys)
                bars = ax.barh(
                    y_pos[valid], doys[valid],
                    color=[colors_pft[i] for i in np.where(valid)[0]],
                    height=0.78, alpha=0.85, edgecolor='none')
                # Annotate bars with 'Mon DD' labels
                for bar, idx in zip(bars, np.where(valid)[0]):
                    date_str = yyyymmdd_to_str(int(v1d[idx]))
                    if date_str:
                        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                                date_str, va='center', fontsize=5.5, color='#2d3748')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(pft_short, fontsize=6.5)
                ax.invert_yaxis()
                ax.set_xticks(tick_pos)
                ax.set_xticklabels(tick_lbl, fontsize=8)
                ax.set_xlim(1, 366)
                ax.set_xlabel('Calendar date', fontsize=9)
                ax.set_title(f'{hem} — {row_title}', fontsize=10, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)
                if N_NAT < n_pfts:
                    ax.axhline(N_NAT - 0.5, color='#a0aec0',
                               linewidth=1.2, linestyle='--')
            else:
                ax.text(0.5, 0.5, f'{varname}\nnot in file',
                        ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')

    fig5d.suptitle(
        'Planting & Harvest Dates — day-of-year from YYYYMMDD (non-leap reference)',
        fontsize=12, fontweight='bold')
    p = _pdf('phenology_dates')
    _fig(s5, save_pdf_and_b64(fig5d, p),
         'NH/SH minimum planting, maximum planting, and maximum harvest dates '
         '(YYYYMMDD parsed to calendar day-of-year)', p)

    figures_data.append({
        'id': 'phenology', 'title': '5. Phenology',
        'description': (
            'Growing degree day thresholds (hybgdd, gddmin, lfemerg), temperature '
            'triggers (baset, mxtmp, planting_temp), and planting date windows '
            '(min/max_NH_planting_date) controlling phenological development stages '
            'from leaf onset to maturity and senescence.'
        ),
        'figures': s5,
    })

    # -----------------------------------------------------------------------
    # 6. Root Properties & Plant Hydraulics
    # -----------------------------------------------------------------------
    print("  6. Root & Hydraulics")
    s6 = []

    for specs, fname, cap in [
        ([('roota_par', 'Root distribution α',              '1/m'),
          ('rootb_par', 'Root distribution β',              '1/m'),
          ('root_dmx',  'Max rooting depth (crop)',         'm'),
          ('krmax',     'Root segment max conductance',     'mm/mm/s')],
         'root_distribution',
         'Root distribution parameters (α, β) and maximum root conductance'),
        ([('smpso',        'Soil ψ: full stomatal opening', 'mm'),
          ('smpsc',        'Soil ψ: full stomatal closure', 'mm'),
          ('psi_soil_ref', 'Reference soil water potential', 'mm')],
         'water_stress',
         'Soil water potential thresholds controlling stomatal conductance'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s6, save_pdf_and_b64(fig, p), cap, p)

    # Segment × PFT heatmaps
    for varname, label, units in [
        ('kmax',  'Max plant conductance per segment', 'mm/mm/s'),
        ('psi50', 'ψ₅₀ per segment',                  'mm'),
        ('ck',    'Weibull shape parameter',           '–'),
    ]:
        v = get_var(nc, varname)
        if v is not None and v.ndim == 2:
            n_seg, n_pft_v = v.shape
            fig_hm = make_2d_heatmap(v, seg_names[:n_seg], pft_short[:n_pft_v],
                                     f'{label} ({varname})', units)
            p = _pdf(f'hydraulics_{varname}')
            _fig(s6, save_pdf_and_b64(fig_hm, p),
                 f'{label}: heatmap for all hydraulic segments × PFTs', p)

    # rootprof_beta (variants × PFTs)
    v_rpb = get_var(nc, 'rootprof_beta')
    if v_rpb is not None and v_rpb.ndim == 2:
        n_var_dim, n_pft_v = v_rpb.shape
        var_labels = [f'Variant {i}' for i in range(n_var_dim)]
        fig_rpb = make_2d_heatmap(v_rpb, var_labels, pft_short[:n_pft_v],
                                   'Root profile β parameter (rootprof_beta)', '–')
        p = _pdf('rootprof_beta')
        _fig(s6, save_pdf_and_b64(fig_rpb, p),
             'Root profile β for C and N vertical discretization (2 variants)', p)

    figures_data.append({
        'id': 'hydraulics', 'title': '6. Root Properties & Plant Hydraulics',
        'description': (
            'Root distribution parameters (α, β shape), hydraulic conductance (kmax) '
            'and vulnerability curve parameters (ψ₅₀, ck) across the four plant '
            'hydraulic segments, soil water potential thresholds for stomatal regulation, '
            'and the two-variant root profile β for vertical C/N discretization.'
        ),
        'figures': s6,
    })

    # -----------------------------------------------------------------------
    # 7. Litter Fractions & Wood Products
    # -----------------------------------------------------------------------
    print("  7. Litter & Wood Products")
    s7 = []

    fig7 = make_stacked_bar_fig(nc, [
        ('Leaf Litter Fractions\n(lf_flab + lf_fcel + lf_flig)', [
            ('lf_flab', 'Labile',    '#f6ad55'),
            ('lf_fcel', 'Cellulose', '#68d391'),
            ('lf_flig', 'Lignin',    '#9b2335'),
        ]),
        ('Fine Root Litter Fractions\n(fr_flab + fr_fcel + fr_flig)', [
            ('fr_flab', 'Labile',    '#f6ad55'),
            ('fr_fcel', 'Cellulose', '#68d391'),
            ('fr_flig', 'Lignin',    '#9b2335'),
        ]),
        ('Wood Product Allocation\n(pconv + pprod10 + pprod100)', [
            ('pconv',    'Conversion',  '#fc8181'),
            ('pprod10',  '10-yr pool',  '#90cdf4'),
            ('pprod100', '100-yr pool', '#9ae6b4'),
        ]),
    ], pft_short, 'Litter Biochemical Fractions & Wood Product Allocation')
    p = _pdf('litter_wood')
    _fig(s7, save_pdf_and_b64(fig7, p),
         'Leaf/root litter labile/cellulose/lignin fractions and dead-stem wood product allocation', p)

    figures_data.append({
        'id': 'litter-wood', 'title': '7. Litter Fractions & Wood Products',
        'description': (
            'Litter biochemical composition (labile, cellulose, and lignin fractions '
            'for leaf and fine root litter) and allocation of dead stem C to the '
            'conversion flux, 10-year, and 100-year wood product pools. '
            'Each stacked bar should sum to 1 for litter fractions.'
        ),
        'figures': s7,
    })

    # -----------------------------------------------------------------------
    # 8. Fire Parameters
    # -----------------------------------------------------------------------
    print("  8. Fire")
    s8 = []

    for specs, fname, cap in [
        ([('fm_leaf',   'Fire mortality: leaf',      '0–1'),
          ('fm_lstem',  'Fire mortality: live stem',  '0–1'),
          ('fm_dstem',  'Fire mortality: dead stem',  '0–1'),
          ('fm_root',   'Fire mortality: fine root',  '0–1'),
          ('fm_other',  'Fire mortality: other',      '0–1')],
         'fire_mortality',
         'Fire-related plant mortality factors per tissue type'),
        ([('cc_leaf',  'Combustion completeness: leaf',      '0–1'),
          ('cc_lstem', 'Combustion completeness: live stem', '0–1'),
          ('cc_dstem', 'Combustion completeness: dead stem', '0–1'),
          ('cc_other', 'Combustion completeness: other',     '0–1'),
          ('fd_pft',   'Fire duration',                      'hr'),
          ('fsr_pft',  'Fire spread rate',                   'm/s')],
         'fire_combustion',
         'Combustion completeness factors, fire spread rate, and duration'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s8, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'fire', 'title': '8. Fire Parameters',
        'description': (
            'PFT-level fire mortality factors by tissue type (leaf, live stem, dead stem, '
            'fine root, other) and combustion completeness factors. Also includes fire '
            'spread rate (fsr_pft) and fire duration (fd_pft). These parameters are '
            'primarily active for natural vegetation PFTs.'
        ),
        'figures': s8,
    })

    # -----------------------------------------------------------------------
    # 9. N Fixation, Mycorrhizal & Bioclimatic Limits
    # -----------------------------------------------------------------------
    print("  9. N fixation, mycorrhizal, bioclimatic")
    s9 = []

    for specs, fname, cap in [
        ([('FUN_fracfixers', 'Max C fraction for N fixation', 'fraction'),
          ('a_fix',          'N fixation param a',             '–'),
          ('b_fix',          'N fixation param b',             '1/°C'),
          ('c_fix',          'N fixation param c',             '°C'),
          ('s_fix',          'Baseline N fixation cost',       'gC/gN'),
          ('fnitr',          'Foliage N limitation factor',    '–')],
         'n_fixation',
         'Nitrogen fixation cost and temperature response parameters'),
        ([('akc_active',  'AM root active cost (C)',    'gC/m³'),
          ('akn_active',  'AM root active cost (N)',    'gC/m²'),
          ('ekc_active',  'EM root active cost (C)',    'gC/m³'),
          ('ekn_active',  'EM root active cost (N)',    'gC/m²'),
          ('kc_nonmyc',   'Non-myc root cost (C)',      'gC/m³'),
          ('perecm',      'Fraction N via EM fungi',    'fraction')],
         'mycorrhizal',
         'Arbuscular (AM) and ectomycorrhizal (EM) N uptake cost parameters'),
        ([('pftpar28', 'Min coldest month T',      '°C'),
          ('pftpar29', 'Max coldest month T',      '°C'),
          ('pftpar30', 'Min GDD (>5 °C)',          '°C·days'),
          ('pftpar31', 'Max warmest month T',      '°C')],
         'bioclimatic',
         'Bioclimatic envelope limits for PFT establishment and survival'),
    ]:
        fig = make_pft_bar_fig(nc, specs, pft_short, cap)
        p   = _pdf(fname)
        _fig(s9, save_pdf_and_b64(fig, p), cap, p)

    figures_data.append({
        'id': 'n-fix-myc', 'title': '9. N Fixation, Mycorrhizal & Bioclimatic',
        'description': (
            'Nitrogen fixation cost parameters (FUN framework) and temperature response '
            '(Houlton et al. 2008); mycorrhizal N uptake cost constants for arbuscular '
            '(AM) and ectomycorrhizal (EM) fungi; and bioclimatic temperature and GDD '
            'limits used in vegetation dynamics (CNDV).'
        ),
        'figures': s9,
    })

    # -----------------------------------------------------------------------
    # 10. Global (allpfts) Parameters
    # -----------------------------------------------------------------------
    print("  10. Global parameters")
    s10 = []

    groups_10 = [
        ('global_decomp',
         'Decomposition Rates, Turnover Times & SOM C:N',
         'Litter and SOM decomposition rates, turnover times, and C:N ratios for soil organic matter pools',
         ['k_l1', 'k_l2', 'k_l3', 'k_s1', 'k_s2', 'k_s3', 'k_s4', 'k_frag',
          'tau_l1', 'tau_l2_l3', 'tau_s1', 'tau_s2', 'tau_s3', 'tau_cwd',
          'cn_s1', 'cn_s2', 'cn_s3', 'cn_s4',
          'cn_s1_bgc', 'cn_s2_bgc', 'cn_s3_bgc',
          'rf_l1s1', 'rf_l2s2', 'rf_l3s3', 'rf_s1s2', 'rf_s2s3', 'rf_s3s4',
          'rf_l1s1_bgc', 'rf_l2s1_bgc', 'rf_l3s2_bgc',
          'rf_s2s1_bgc', 'rf_s2s3_bgc', 'rf_s3s1_bgc',
          'rf_cwdl2_bgc', 'rf_cwdl3_bgc',
          'cwd_fcel', 'cwd_flig', 'decomp_depth_efolding', 'organic_max']),
        ('global_resp',
         'Respiration, Mortality & Turnover',
         'Maintenance respiration base rate and Q₁₀ factors, mortality coefficients, wood turnover',
         ['br_mr', 'q10_mr', 'q10_hr', 'froz_q10', 'r_mort', 'k_mort',
          'lwtop_ann', 'lake_decomp_fact', 'rootlitfrac', 'dayscrecover',
          'fstor2tran']),
        ('global_ncycling',
         'Nitrogen Cycling (Global)',
         'Nitrification/denitrification rates and competition parameters among microbes and plants for NH₄ and NO₃',
         ['bdnr', 'dnp', 'k_nitr_max', 'sf_minn', 'sf_no3',
          'compet_decomp_nh4', 'compet_decomp_no3', 'compet_denit',
          'compet_nit', 'compet_plant_nh4', 'compet_plant_no3',
          'depth_runoff_Nloss', 'rc_npool', 'cnscalefactor']),
        ('global_ch4',
         'Methane Dynamics & Soil Gas Transport',
         'CH₄ production, oxidation (Michaelis-Menten kinetics), Q₁₀ factors, and soil gas diffusion parameters',
         ['f_ch4', 'atmch4', 'k_m', 'k_m_o2', 'k_m_unsat',
          'q10ch4', 'q10_ch4oxid', 'q10lakebase',
          'vmax_ch4_oxid', 'vmax_oxid_unsat',
          'oxinhib', 'pHmin', 'pHmax',
          'nongrassporosratio', 'porosmin', 'unsat_aere_ratio',
          'scale_factor_aere', 'scale_factor_gasdiff', 'scale_factor_liqdiff',
          'vgc_max', 'redoxlag', 'redoxlag_vertical',
          'smp_crit', 'f_sat', 'satpow', 'som_diffus',
          'rij_kro_a', 'rij_kro_alpha', 'rij_kro_beta',
          'rij_kro_delta', 'rij_kro_gamma',
          'rob', 'surface_tension_water']),
        ('global_phenology_fire',
         'Phenology Triggers & Fire (Global)',
         'Global leaf onset/offset thresholds, day-length triggers, Q₁₀ water-table lag, and fire fuel thresholds',
         ['crit_dayl', 'crit_offset_fdd', 'crit_offset_swi',
          'crit_onset_fdd', 'crit_onset_swi',
          'ndays_off', 'ndays_on', 'gddfunc_p1', 'gddfunc_p2',
          'soilpsi_off', 'soilpsi_on', 'highlatfact', 'qflxlagd',
          'ef_time', 'maxpsi_hr', 'minpsi_hr',
          'wcf', 'minfuel', 'me_herb', 'me_woody']),
    ]

    for pdf_name, title_str, caption, var_list in groups_10:
        rows = _collect_scalar_rows(nc, var_list)
        if not rows:
            continue
        fig = make_scalar_table_fig(rows, title_str)
        p   = _pdf(pdf_name)
        _fig(s10, save_pdf_and_b64(fig, p), caption, p)

    # True scalar cards (dimensionless, no PFT dimension)
    scalar_cards = []
    for name in ['aereoxid', 'mino2lim', 'q10ch4base', 'capthick']:
        v = get_var(nc, name)
        if v is not None:
            scalar_cards.append((
                name,
                float(np.squeeze(v)),
                _attr(nc, name, 'units',     '–'),
                _attr(nc, name, 'long_name', name),
            ))
    if scalar_cards:
        fig_sc = make_scalar_cards_fig(scalar_cards)
        p = _pdf('global_scalars')
        _fig(s10, save_pdf_and_b64(fig_sc, p),
             'True scalar parameters (no PFT or allpfts dimension)', p)

    figures_data.append({
        'id': 'global-params', 'title': '10. Global (allpfts) Parameters',
        'description': (
            'Biogeochemistry parameters that apply globally (not per-PFT): '
            'decomposition and SOM turnover rates, maintenance respiration Q₁₀ factors, '
            'N cycling competition parameters, methane dynamics (production, oxidation, '
            'diffusion), and global phenology onset/offset triggers.'
        ),
        'figures': s10,
    })

    # -----------------------------------------------------------------------
    # Build HTML
    # -----------------------------------------------------------------------
    n_vars = len(nc.variables)
    extra_meta = (f'<p><strong>Variables:</strong> {n_vars}</p>'
                  f'<p><strong>PFTs:</strong> {n_pfts}</p>')

    html = _build_html(
        title=f'CLM5 Parameter File — {nc_basename}',
        filename=nc_basename,
        extra_meta=extra_meta,
        figures_data=figures_data,
    )

    html_path = os.path.join(os.path.dirname(os.path.abspath(nc_file)), stem + '.html')
    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(html)

    nc.close()
    print(f"\nDone → {html_path}")
    print(f"       {out_dir}/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 2:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_nc = os.path.join(
            script_dir,
            'clm5_params.c171117_boas_cc34_on_mod5_hybgdd950_noapple.nc',
        )
        if not os.path.exists(default_nc):
            print("Usage: python visualize_paramfile.py <paramfile.nc>")
            sys.exit(1)
        nc_file = default_nc
    else:
        nc_file = sys.argv[1]

    main(nc_file)
