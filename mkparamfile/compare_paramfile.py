#!/usr/bin/env python3
"""
CLM5 Parameter File Comparison Script
======================================
Compares two CLM5 NetCDF parameter files and generates an HTML report
with side-by-side and difference visualizations for all parameter groups.

Usage: python compare_paramfile.py <file1.nc> <file2.nc> <label1> <label2> [-o output_name]
"""

import os
import sys
import argparse
import math
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch
from netCDF4 import Dataset

# Import shared helpers from visualize_paramfile
from visualize_paramfile import (
    N_NAT, NATPFT_NAMES, CFT_NAMES,
    fig_to_base64, save_pdf_and_b64,
    get_var, get_pft_names_from_file, get_pft_short, get_segment_names,
    make_pft_bar_fig, make_flag_heatmap, make_2d_heatmap,
    make_scalar_table_fig, make_stacked_bar_fig,
    _collect_scalar_rows, _attr, _pft_colors, _build_html,
    yyyymmdd_to_doy, yyyymmdd_to_str, doy_month_ticks,
)


# ---------------------------------------------------------------------------
# Comparison-specific helpers
# ---------------------------------------------------------------------------

def extract_differing_parts(name1, name2):
    """Extract the differing portion of two filenames for output naming."""
    min_len = min(len(name1), len(name2))
    prefix_end = 0
    for i in range(min_len):
        if name1[i] != name2[i]:
            break
        prefix_end = i + 1
    suffix_start1, suffix_start2 = len(name1), len(name2)
    for i in range(1, min_len - prefix_end + 1):
        if name1[-i] != name2[-i]:
            break
        suffix_start1 = len(name1) - i + 1
        suffix_start2 = len(name2) - i + 1
    diff1 = name1[prefix_end:suffix_start1].strip('_')
    diff2 = name2[prefix_end:suffix_start2].strip('_')
    if diff1 and diff2:
        return f"{diff1}_vs_{diff2}"
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def get_change_color(diff, threshold=0.001):
    """Return a colour string based on sign and magnitude of *diff*."""
    if abs(diff) < threshold:
        return '#48bb78'   # green  — unchanged
    elif diff > 0:
        return '#e53e3e'   # red    — increased
    else:
        return '#3182ce'   # blue   — decreased


def make_scalar_comparison_table(nc1, nc2, var_names, title, label1, label2):
    """
    Comparison table for allpfts / scalar variables.
    Columns: Parameter | label1 | label2 | Diff | % Change | Units | Description
    Returns a matplotlib Figure, or None if no matching variables found.
    """
    rows = []
    for name in var_names:
        v1 = get_var(nc1, name)
        v2 = get_var(nc2, name)
        if v1 is None and v2 is None:
            continue
        f1 = float(np.squeeze(v1)) if v1 is not None else np.nan
        f2 = float(np.squeeze(v2)) if v2 is not None else np.nan
        diff = (f2 - f1) if not (np.isnan(f1) or np.isnan(f2)) else np.nan
        if not np.isnan(diff) and f1 != 0:
            pct = (diff / abs(f1)) * 100
        elif not np.isnan(diff) and f2 != 0:
            pct = np.inf if diff > 0 else -np.inf
        else:
            pct = 0.0 if not np.isnan(diff) else np.nan
        units    = _attr(nc1, name, 'units',     _attr(nc2, name, 'units',     '–'))
        longname = _attr(nc1, name, 'long_name', _attr(nc2, name, 'long_name', name))[:55]
        rows.append((
            name,
            f'{f1:.6g}'    if not np.isnan(f1)   else '–',
            f'{f2:.6g}'    if not np.isnan(f2)   else '–',
            f'{diff:+.4g}' if not np.isnan(diff) else '–',
            f'{pct:+.2f}%' if np.isfinite(pct)  else ('∞' if not np.isnan(pct) else '–'),
            units,
            longname,
        ))
    if not rows:
        return None

    col_labels = ['Parameter', label1, label2, 'Diff', '% Change', 'Units', 'Description']
    col_widths  = [0.11, 0.09, 0.09, 0.09, 0.09, 0.08, 0.45]
    n_rows      = len(rows)
    fig_h       = max(3, n_rows * 0.33 + 1.5)
    fig, ax     = plt.subplots(figsize=(22, fig_h), constrained_layout=True)
    ax.axis('off')
    tbl = ax.table(cellText=rows, colLabels=col_labels,
                   colWidths=col_widths, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    tbl.scale(1, 1.4)
    for j in range(len(col_labels)):
        tbl[(0, j)].set_facecolor('#2d3748')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold')
    for i, row_data in enumerate(rows, start=1):
        try:
            dv = float(row_data[3].replace('+', '').replace('∞', '0'))
        except ValueError:
            dv = 0.0
        diff_color = get_change_color(dv)
        for j in range(len(col_labels)):
            bg = '#f7fafc' if i % 2 == 0 else 'white'
            if j == 3:
                bg = diff_color
            tbl[(i, j)].set_facecolor(bg)
    ax.set_title(title, fontsize=11, fontweight='bold', pad=8)
    return fig


def make_pft_bar_diff_fig(nc1, nc2, var_specs, pft_labels, title, label1, label2,
                           n_nat=N_NAT):
    """
    Three-column figure for per-PFT comparison: file1 | file2 | difference.
    Each row corresponds to one variable in var_specs.

    var_specs : list of (varname, display_title, units)
    """
    n      = len(var_specs)
    n_pfts = len(pft_labels)
    row_h  = max(8, n_pfts * 0.18 + 1.0)
    fig, axes = plt.subplots(n, 3,
                             figsize=(24, row_h * n),
                             constrained_layout=True)
    if n == 1:
        axes = axes.reshape(1, 3)

    c1  = _pft_colors(n_pfts, n_nat)
    c2  = ['#ed8936'] * n_nat + ['#f6ad55'] * max(0, n_pfts - n_nat)

    for row, (varname, display_name, units) in enumerate(var_specs):
        ax1, ax2, ax_diff = axes[row]
        v1 = get_var(nc1, varname)
        v2 = get_var(nc2, varname)

        y_pos = np.arange(n_pfts)

        for ax, vals, colors, flabel in [
            (ax1,    v1, c1, label1),
            (ax2,    v2, c2, label2),
        ]:
            if vals is None:
                ax.text(0.5, 0.5, f'{varname}\nnot in file',
                        ha='center', va='center', transform=ax.transAxes, fontsize=8)
                ax.axis('off')
            else:
                v1d = np.atleast_1d(vals)[:n_pfts]
                vd  = np.where(np.isnan(v1d), 0.0, v1d)
                ax.barh(y_pos, vd, color=colors[:len(y_pos)],
                        height=0.78, alpha=0.85, edgecolor='none')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(pft_labels[:len(y_pos)], fontsize=6)
                ax.invert_yaxis()
                ax.set_xlabel(units, fontsize=8)
                ax.set_title(f'{flabel}\n{display_name} ({varname})',
                             fontsize=8, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)
                if n_nat < len(vd):
                    ax.axhline(n_nat - 0.5, color='#a0aec0',
                               linewidth=1.2, linestyle='--')

        # Difference panel
        if v1 is not None and v2 is not None:
            a1 = np.atleast_1d(v1)[:n_pfts]
            a2 = np.atleast_1d(v2)[:n_pfts]
            diff = np.where(np.isnan(a1) | np.isnan(a2), 0.0, a2 - a1)
            dcol = ['#e53e3e' if d > 0 else '#3182ce' for d in diff]
            ax_diff.barh(y_pos, diff, color=dcol[:len(y_pos)],
                         height=0.78, alpha=0.85, edgecolor='none')
            ax_diff.set_yticks(y_pos)
            ax_diff.set_yticklabels(pft_labels[:len(y_pos)], fontsize=6)
            ax_diff.invert_yaxis()
            ax_diff.set_xlabel(units, fontsize=8)
            ax_diff.set_title(f'Diff ({label2} − {label1})\n{display_name} ({varname})',
                              fontsize=8, fontweight='bold')
            ax_diff.axvline(0, color='#2d3748', linewidth=1)
            ax_diff.grid(axis='x', alpha=0.3)
            if n_nat < len(diff):
                ax_diff.axhline(n_nat - 0.5, color='#a0aec0',
                                linewidth=1.2, linestyle='--')
        else:
            ax_diff.text(0.5, 0.5, 'One file\nmissing variable',
                         ha='center', va='center', transform=ax_diff.transAxes)
            ax_diff.axis('off')

    # Legend
    fig.legend(handles=[
        Patch(facecolor='#3182ce', label=f'{label1} – natural'),
        Patch(facecolor='#68d391', label=f'{label1} – crop'),
        Patch(facecolor='#ed8936', label=f'{label2} – natural'),
        Patch(facecolor='#f6ad55', label=f'{label2} – crop'),
        Patch(facecolor='#e53e3e', label=f'{label2} > {label1}'),
        Patch(facecolor='#3182ce', label=f'{label2} < {label1}'),
    ], loc='upper right', fontsize=7, ncol=2, bbox_to_anchor=(1.0, 1.0))
    fig.suptitle(title, fontsize=12, fontweight='bold')
    return fig


def make_flag_comparison(nc1, nc2, flag_vars, pft_labels, label1, label2):
    """Side-by-side flag heatmaps and a difference heatmap."""
    n_pfts  = len(pft_labels)
    n_flags = len(flag_vars)
    fig_h   = max(10, n_pfts * 0.22 + 2.0)
    fig_w   = max(8,  n_flags * 1.3 + 2.0)
    fig, axes = plt.subplots(1, 3, figsize=(fig_w * 3, fig_h), constrained_layout=True)

    for ax, nc, lbl in [(axes[0], nc1, label1), (axes[1], nc2, label2)]:
        mat = np.zeros((n_pfts, n_flags))
        for j, fname in enumerate(flag_vars):
            v = get_var(nc, fname)
            if v is not None:
                v1d = np.atleast_1d(v)[:n_pfts]
                mat[:len(v1d), j] = np.where(np.isnan(v1d), 0, v1d)
        im = ax.imshow(mat, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1,
                       interpolation='nearest')
        ax.set_xticks(range(n_flags))
        ax.set_xticklabels(flag_vars, rotation=40, ha='right', fontsize=8)
        ax.set_yticks(range(n_pfts))
        ax.set_yticklabels(pft_labels, fontsize=6.5)
        ax.set_title(lbl, fontsize=11, fontweight='bold')
        if N_NAT < n_pfts:
            ax.axhline(N_NAT - 0.5, color='white', linewidth=2, linestyle='--')

    # Difference
    mats = []
    for nc in [nc1, nc2]:
        mat = np.zeros((n_pfts, n_flags))
        for j, fname in enumerate(flag_vars):
            v = get_var(nc, fname)
            if v is not None:
                v1d = np.atleast_1d(v)[:n_pfts]
                mat[:len(v1d), j] = np.where(np.isnan(v1d), 0, v1d)
        mats.append(mat)
    diff_mat = mats[1] - mats[0]
    im = axes[2].imshow(diff_mat, aspect='auto', cmap='RdBu_r', vmin=-1, vmax=1,
                        interpolation='nearest')
    axes[2].set_xticks(range(n_flags))
    axes[2].set_xticklabels(flag_vars, rotation=40, ha='right', fontsize=8)
    axes[2].set_yticks(range(n_pfts))
    axes[2].set_yticklabels(pft_labels, fontsize=6.5)
    axes[2].set_title(f'Difference ({label2} − {label1})', fontsize=11, fontweight='bold')
    if N_NAT < n_pfts:
        axes[2].axhline(N_NAT - 0.5, color='black', linewidth=2, linestyle='--')

    fig.suptitle('PFT Binary Flags Comparison', fontsize=13, fontweight='bold')
    return fig


def make_planting_date_comparison_fig(nc1, nc2, pft_labels, label1, label2):
    """
    3-column comparison of NH and SH planting/harvest dates.
    YYYYMMDD integers are parsed to day-of-year (mirrors ESMF TimeSetymd
    decomposition: yy=YYYY//10000, mm=MM, dd=DD).

    Layout: 6 rows (min/max planting NH, min/max planting SH, max harvest NH/SH)
            × 3 cols (label1 | label2 | difference in days).
    Difference column shows days shifted later (red) / earlier (blue).
    """
    date_vars = [
        ('min_NH_planting_date', 'NH min planting'),
        ('max_NH_planting_date', 'NH max planting'),
        ('min_SH_planting_date', 'SH min planting'),
        ('max_SH_planting_date', 'SH max planting'),
        ('max_NH_harvest_date',  'NH max harvest'),
        ('max_SH_harvest_date',  'SH max harvest'),
    ]
    n_pfts    = len(pft_labels)
    y_pos     = np.arange(n_pfts)
    n_vars    = len(date_vars)
    tick_pos, tick_lbl = doy_month_ticks()
    row_h = max(8, n_pfts * 0.18 + 1.2)

    fig, axes = plt.subplots(n_vars, 3,
                             figsize=(18, row_h * n_vars),
                             constrained_layout=True)

    col_titles = [label1, label2, f'Difference ({label2} − {label1}, days)']
    for col, title in enumerate(col_titles):
        axes[0, col].set_title(title, fontsize=11, fontweight='bold')

    for row, (varname, var_title) in enumerate(date_vars):
        raw1 = get_var(nc1, varname)
        raw2 = get_var(nc2, varname)

        def _doy(v):
            if v is None:
                return None
            return yyyymmdd_to_doy(np.atleast_1d(v)[:n_pfts])

        doy1 = _doy(raw1)
        doy2 = _doy(raw2)

        def _draw_bars(ax, doys, raw, color):
            if doys is None:
                ax.text(0.5, 0.5, f'{varname}\nnot in file',
                        ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
                return
            valid = ~np.isnan(doys)
            bars = ax.barh(y_pos[valid], doys[valid], height=0.78,
                           color=color, alpha=0.85, edgecolor='none')
            if raw is not None:
                r1d = np.atleast_1d(raw)[:n_pfts]
                for bar, idx in zip(bars, np.where(valid)[0]):
                    ds = yyyymmdd_to_str(int(r1d[idx]))
                    if ds:
                        ax.text(bar.get_width() + 1,
                                bar.get_y() + bar.get_height() / 2,
                                ds, va='center', fontsize=5.5, color='#2d3748')
            ax.set_xticks(tick_pos)
            ax.set_xticklabels(tick_lbl, fontsize=7)
            ax.set_xlim(1, 366)
            ax.set_xlabel('Calendar date', fontsize=8)

        _draw_bars(axes[row, 0], doy1, raw1, '#3182ce')
        _draw_bars(axes[row, 1], doy2, raw2, '#ed8936')

        ax3 = axes[row, 2]
        if doy1 is not None and doy2 is not None:
            diff = np.where(np.isnan(doy1) | np.isnan(doy2), np.nan, doy2 - doy1)
            valid = ~np.isnan(diff)
            colors_diff = ['#e53e3e' if d > 0 else '#3182ce' if d < 0 else '#a0aec0'
                           for d in diff[valid]]
            ax3.barh(y_pos[valid], diff[valid], height=0.78,
                     color=colors_diff, alpha=0.85, edgecolor='none')
            ax3.axvline(0, color='#2d3748', linewidth=1)
            ax3.set_xlabel('Days', fontsize=8)
        else:
            ax3.text(0.5, 0.5, 'One file\nmissing variable',
                     ha='center', va='center', transform=ax3.transAxes)
            ax3.axis('off')

        for ax in (axes[row, 0], axes[row, 1], axes[row, 2]):
            if ax.axison:
                ax.set_yticks(y_pos)
                ax.set_yticklabels(pft_labels, fontsize=6.5)
                ax.invert_yaxis()
                ax.grid(axis='x', alpha=0.3)
                if N_NAT < n_pfts:
                    ax.axhline(N_NAT - 0.5, color='#a0aec0',
                               linewidth=1.2, linestyle='--')
        axes[row, 0].set_ylabel(var_title, fontsize=9)

    fig.suptitle(
        f'Planting & Harvest Dates (DOY from YYYYMMDD)  ·  {label1} vs {label2}',
        fontsize=12, fontweight='bold')
    return fig


def make_pftname_comparison_fig(names1, names2, label1, label2):
    """
    Table figure listing PFTs whose names differ between the two files.
    Rows: index | label1 name | label2 name
    Identical PFTs are omitted.  If every name is the same a 'no differences'
    message is shown instead.
    """
    n = max(len(names1), len(names2))
    diffs = []
    for i in range(n):
        n1 = names1[i] if i < len(names1) else ''
        n2 = names2[i] if i < len(names2) else ''
        if n1 != n2:
            diffs.append((i, n1, n2))

    fig, ax = plt.subplots(figsize=(14, max(2.0, len(diffs) * 0.55 + 1.5)),
                           constrained_layout=True)
    ax.axis('off')

    if not diffs:
        ax.text(0.5, 0.5,
                'No differences in pftname between the two files.',
                ha='center', va='center', fontsize=11, color='#276749',
                transform=ax.transAxes)
    else:
        col_labels = ['PFT index', label1, label2]
        table_data = [[str(idx), n1, n2] for idx, n1, n2 in diffs]
        tbl = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc='left',
            loc='center',
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.auto_set_column_width([0, 1, 2])
        # Header row styling
        for j in range(3):
            tbl[(0, j)].set_facecolor('#2b6cb0')
            tbl[(0, j)].set_text_props(color='white', fontweight='bold')
        # Highlight differing cells
        for row_i, (_, n1, n2) in enumerate(diffs, start=1):
            row_color = '#fff5f5'
            for j in range(3):
                tbl[(row_i, j)].set_facecolor(row_color)
            tbl[(row_i, 1)].set_facecolor('#fed7d7')  # label1 value
            tbl[(row_i, 2)].set_facecolor('#bee3f8')  # label2 value

    ax.set_title(f'pftname differences: {label1} vs {label2}',
                 fontsize=11, fontweight='bold', pad=8)
    return fig


def make_stacked_bar_comparison(nc1, nc2, fraction_groups, pft_labels,
                                 title, label1, label2):
    """Side-by-side stacked bar charts for fraction groups."""
    n_groups = len(fraction_groups)
    n_pfts   = len(pft_labels)
    row_h    = max(10, n_pfts * 0.20 + 1.2)
    # 2 columns per group (file1, file2)
    fig, axes = plt.subplots(n_groups, 2,
                             figsize=(16, row_h * n_groups),
                             constrained_layout=True)
    if n_groups == 1:
        axes = axes.reshape(1, 2)

    for row, (group_title, components) in enumerate(fraction_groups):
        for col, (nc, lbl) in enumerate([(nc1, label1), (nc2, label2)]):
            ax    = axes[row, col]
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
            ax.set_title(f'{lbl}\n{group_title}', fontsize=9, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            ax.set_xlim(0, 1.05)
            if row == 0 and col == 0:
                ax.legend(fontsize=8, loc='lower right')
            if N_NAT < n_pfts:
                ax.axhline(N_NAT - 0.5, color='#a0aec0', linewidth=1.2, linestyle='--')

    fig.suptitle(title, fontsize=12, fontweight='bold')
    return fig


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main(nc_file1, nc_file2, label1, label2, output_name=None):
    print(f"Comparing\n  {nc_file1}\n  {nc_file2}")
    nc1 = Dataset(nc_file1, 'r')
    nc2 = Dataset(nc_file2, 'r')

    base1 = os.path.basename(nc_file1)
    base2 = os.path.basename(nc_file2)

    if output_name is None:
        output_name = f'comparison_{label1}_vs_{label2}'

    out_dir_base = os.path.dirname(os.path.abspath(nc_file1))
    out_dir      = os.path.join(out_dir_base, output_name + '_figures')
    os.makedirs(out_dir, exist_ok=True)

    pft_names_full = get_pft_names_from_file(nc1)
    n_pfts         = len(pft_names_full)
    pft_short      = get_pft_short(pft_names_full)
    seg_names      = get_segment_names(nc1)

    figures_data = []
    _ctr = [0]

    def _pdf(name):
        path = os.path.join(out_dir, f'{_ctr[0]:02d}_{name}.pdf')
        _ctr[0] += 1
        return path

    def _rel(pdf_path):
        return os.path.relpath(pdf_path, out_dir_base)

    def _fig(section_list, b64, caption, pdf_path):
        section_list.append({'b64': b64, 'caption': caption, 'pdf_name': _rel(pdf_path)})

    # -----------------------------------------------------------------------
    # 0. PFT Catalogue — pftname differences + flag comparison
    # -----------------------------------------------------------------------
    print("  0. PFT Catalogue")
    pft_names2 = get_pft_names_from_file(nc2)
    s0 = []

    # pftname comparison table (only rows that differ are shown)
    fig_names = make_pftname_comparison_fig(
        pft_names_full, pft_names2, label1, label2)
    p = _pdf('pft_names_cmp')
    _fig(s0, save_pdf_and_b64(fig_names, p),
         f'pftname: PFTs whose names differ between {label1} and {label2} '
         f'(identical PFTs omitted)', p)

    flag_vars = ['c3psn', 'crop', 'irrigated', 'woody', 'evergreen',
                 'season_decid', 'stress_decid', 'perennial', 'covercrop']
    fig_flags = make_flag_comparison(nc1, nc2, flag_vars, pft_short, label1, label2)
    p = _pdf('pft_flags_cmp')
    _fig(s0, save_pdf_and_b64(fig_flags, p),
         f'Binary PFT flags: {label1} (left) | {label2} (centre) | difference (right)', p)

    figures_data.append({
        'id': 'pft-catalogue', 'title': '0. PFT Catalogue',
        'description': (
            'PFT name differences (only differing indices listed) and '
            'side-by-side comparison of PFT binary classification flags '
            '(c3psn, crop, irrigated, woody, evergreen, season_decid, '
            'stress_decid, perennial, covercrop). The rightmost flag panel '
            'shows the difference (blue = flag removed, red = flag added).'
        ),
        'figures': s0,
    })

    # -----------------------------------------------------------------------
    # Helper: per-PFT section with comparison figure + caption
    # -----------------------------------------------------------------------
    def _pft_section(section_id, section_title, description,
                     var_group_pairs, pdf_prefix):
        """
        var_group_pairs : list of (var_specs, pdf_suffix)
          where var_specs is a list of (varname, display_title, units)
        Returns a section dict.
        """
        sfigs = []
        for var_specs, pdf_suffix in var_group_pairs:
            fig = make_pft_bar_diff_fig(
                nc1, nc2, var_specs, pft_short,
                f'{section_title}  ·  {label1} vs {label2}',
                label1, label2,
            )
            p = _pdf(f'{pdf_prefix}_{pdf_suffix}')
            names = ', '.join(vs[0] for vs in var_specs)
            _fig(sfigs, save_pdf_and_b64(fig, p),
                 f'{label1} | {label2} | difference — {names}', p)
        return {'id': section_id, 'title': section_title,
                'description': description, 'figures': sfigs}

    # -----------------------------------------------------------------------
    # 1. Optical Properties
    # -----------------------------------------------------------------------
    print("  1. Optical")
    figures_data.append(_pft_section(
        'optical', '1. Optical Properties',
        'Comparison of leaf and stem reflectance/transmittance in VIS and NIR bands.',
        [
            ([('rholvis', 'Leaf refl.: VIS',  'fraction'),
              ('rholnir', 'Leaf refl.: NIR',  'fraction'),
              ('rhosvis', 'Stem refl.: VIS',  'fraction'),
              ('rhosnir', 'Stem refl.: NIR',  'fraction')],
             'reflectance'),
            ([('taulvis', 'Leaf transm.: VIS', 'fraction'),
              ('taulnir', 'Leaf transm.: NIR', 'fraction'),
              ('tausvis', 'Stem transm.: VIS', 'fraction'),
              ('tausnir', 'Stem transm.: NIR', 'fraction')],
             'transmittance'),
        ],
        'optical',
    ))

    # -----------------------------------------------------------------------
    # 2. Canopy Structure & Gas Exchange
    # -----------------------------------------------------------------------
    print("  2. Canopy")
    figures_data.append(_pft_section(
        'canopy', '2. Canopy Structure & Gas Exchange',
        'Comparison of SLA, LAI, canopy geometry, and stomatal conductance parameters.',
        [
            ([('slatop',   'SLA (top)',    'm²/gC'),
              ('dsladlai', 'dSLA/dLAI',   'm²/gC'),
              ('laimx',    'Max LAI',      '–'),
              ('dleaf',    'Leaf dim.',    'm')],
             'struct_a'),
            ([('xl',       'Orient. index', '–'),
              ('z0mr',     'z₀ ratio',      '–'),
              ('displar',  'Displ. ratio',  '–'),
              ('ztopmx',   'Canopy top',    'm')],
             'struct_b'),
            ([('mbbopt',          'Ball-Berry slope',  'umol/umol'),
              ('medlynslope',     'Medlyn slope',      'umol/umol'),
              ('medlynintercept', 'Medlyn intercept',  'umol H₂O'),
              ('flnr',            'N in Rubisco',      'fraction')],
             'gas_exchange'),
        ],
        'canopy',
    ))

    # -----------------------------------------------------------------------
    # 3. Carbon Allocation
    # -----------------------------------------------------------------------
    print("  3. Allocation")
    figures_data.append(_pft_section(
        'allocation', '3. Carbon Allocation',
        'Comparison of allocation ratios and shape parameters between the two parameter files.',
        [
            ([('froot_leaf', 'Froot/leaf',   'gC/gC'),
              ('stem_leaf',  'Stem/leaf',    'gC/gC'),
              ('croot_stem', 'Croot/stem',   'gC/gC'),
              ('flivewd',    'Live wood fr.', 'fraction'),
              ('fcur',       'Cur. growth',  'fraction'),
              ('grperc',     'Grow. resp.',  '–')],
             'ratios'),
            ([('aleaff',   'Leaf coeff.',  '–'),
              ('arootf',   'Root coeff.',  '–'),
              ('arooti',   'Root coeff. i','–'),
              ('astemf',   'Stem coeff.',  '–'),
              ('bfact',    'Leaf exp.',    '–'),
              ('allconsl', 'Leaf power',   '–')],
             'shape'),
        ],
        'allocation',
    ))

    # -----------------------------------------------------------------------
    # 4. C:N Stoichiometry
    # -----------------------------------------------------------------------
    print("  4. C:N")
    figures_data.append(_pft_section(
        'cn', '4. C:N Stoichiometry',
        'Comparison of C:N ratios for leaves, roots, wood, and litter between the two files.',
        [
            ([('leafcn',     'Leaf C:N',     'gC/gN'),
              ('leafcn_min', 'Leaf CN min',  'gC/gN'),
              ('leafcn_max', 'Leaf CN max',  'gC/gN'),
              ('fleafcn',    'Leaf CN fill', 'gC/gN')],
             'leaf'),
            ([('frootcn',    'Root C:N',     'gC/gN'),
              ('frootcn_min','Root CN min',  'gC/gN'),
              ('frootcn_max','Root CN max',  'gC/gN'),
              ('livewdcn',   'Live wd CN',   'gC/gN'),
              ('deadwdcn',   'Dead wd CN',   'gC/gN'),
              ('lflitcn',    'Lf litter CN', 'gC/gN')],
             'root_wood'),
            ([('graincn',  'Grain CN',    'gC/gN'),
              ('ffrootcn', 'Root CN fill','gC/gN'),
              ('fstemcn',  'Stem CN fill','gC/gN')],
             'grain_fill'),
        ],
        'cn',
    ))

    # -----------------------------------------------------------------------
    # 5. Phenology
    # -----------------------------------------------------------------------
    print("  5. Phenology")
    s5 = []
    for var_specs, pdf_suffix in [
        ([('hybgdd',   'GDD maturity',  '°C·days'),
          ('grnfill',  'Grain fill',    '–'),
          ('gddmin',   'Min GDD',       '–'),
          ('lfemerg',  'Lf emergence',  '–'),
          ('mxmat',    'Max days mat.',  'days'),
          ('lfmat',    'Canopy GDD mat','–')],
         'gdd'),
        ([('baset',             'Base T',         '°C'),
          ('mxtmp',             'Max T',          '°C'),
          ('planting_temp',     'Planting T',     'K'),
          ('min_planting_temp', 'Min plant. T',   'K')],
         'temp'),
    ]:
        fig = make_pft_bar_diff_fig(
            nc1, nc2, var_specs, pft_short,
            f'5. Phenology  ·  {label1} vs {label2}',
            label1, label2,
        )
        p = _pdf(f'phenology_{pdf_suffix}')
        names = ', '.join(vs[0] for vs in var_specs)
        _fig(s5, save_pdf_and_b64(fig, p),
             f'{label1} | {label2} | difference — {names}', p)

    # Planting & harvest dates: YYYYMMDD → day-of-year (via TimeSetymd-style parse)
    fig5d = make_planting_date_comparison_fig(nc1, nc2, pft_short, label1, label2)
    p = _pdf('phenology_dates')
    _fig(s5, save_pdf_and_b64(fig5d, p),
         'NH/SH planting & harvest dates (YYYYMMDD parsed to day-of-year): '
         f'{label1} | {label2} | difference in days', p)

    figures_data.append({
        'id': 'phenology', 'title': '5. Phenology',
        'description': (
            'Comparison of GDD thresholds (hybgdd, gddmin, lfemerg), temperature '
            'limits (baset, mxtmp, planting_temp), and NH/SH planting & harvest '
            'date windows. YYYYMMDD integers are decomposed into (yy, mm, dd) '
            'and plotted as day-of-year; the difference column shows days '
            'shifted later (red) or earlier (blue).'
        ),
        'figures': s5,
    })

    # -----------------------------------------------------------------------
    # 6. Root & Hydraulics
    # -----------------------------------------------------------------------
    print("  6. Root & Hydraulics")
    s6 = []

    fig6a = make_pft_bar_diff_fig(
        nc1, nc2,
        [('roota_par', 'Root α',    '1/m'),
         ('rootb_par', 'Root β',    '1/m'),
         ('root_dmx',  'Max depth', 'm'),
         ('krmax',     'k_rmax',    'mm/mm/s')],
        pft_short,
        f'Root Distribution & Conductance  ·  {label1} vs {label2}',
        label1, label2,
    )
    p = _pdf('root_dist')
    _fig(s6, save_pdf_and_b64(fig6a, p),
         f'{label1} | {label2} | diff — roota_par, rootb_par, root_dmx, krmax', p)

    fig6b = make_pft_bar_diff_fig(
        nc1, nc2,
        [('smpso',        'ψ open',   'mm'),
         ('smpsc',        'ψ close',  'mm'),
         ('psi_soil_ref', 'ψ ref',    'mm')],
        pft_short,
        f'Water Stress Thresholds  ·  {label1} vs {label2}',
        label1, label2,
    )
    p = _pdf('water_stress')
    _fig(s6, save_pdf_and_b64(fig6b, p),
         f'{label1} | {label2} | diff — smpso, smpsc, psi_soil_ref', p)

    # Segment × PFT heatmaps
    for varname, label, units in [
        ('kmax',  'Max conductance (kmax)',  'mm/mm/s'),
        ('psi50', 'ψ₅₀ (psi50)',            'mm'),
        ('ck',    'Weibull shape (ck)',      '–'),
    ]:
        v1 = get_var(nc1, varname)
        v2 = get_var(nc2, varname)
        if v1 is not None and v1.ndim == 2 and v2 is not None and v2.ndim == 2:
            n_seg  = v1.shape[0]
            n_pftv = v1.shape[1]
            diff      = v2 - v1
            diff_abs  = np.nanmax(np.abs(diff))
            if diff_abs == 0 or np.isnan(diff_abs):
                diff_abs = 1e-18
            diff_range = (-diff_abs, diff_abs)
            fig_3h, axs = plt.subplots(1, 3,
                                        figsize=(14 * 3, max(4, n_seg * 1.5 + 2)),
                                        constrained_layout=True)
            for ax_h, data, lbl, cmap, vrange in [
                (axs[0], v1,   label1, 'viridis',  None),
                (axs[1], v2,   label2, 'viridis',  None),
                (axs[2], diff, f'Diff ({label2}−{label1})', 'RdBu_r', diff_range),
            ]:
                d_plot = np.where(np.isnan(data), 0.0, data)
                vmin   = np.nanmin(d_plot) if vrange is None else vrange[0]
                vmax   = np.nanmax(d_plot) if vrange is None else vrange[1]
                if vmin == vmax:
                    vmin -= 1e-10
                im = ax_h.imshow(d_plot, aspect='auto', cmap=cmap,
                                 vmin=vmin, vmax=vmax, interpolation='nearest')
                ax_h.set_yticks(range(n_seg))
                ax_h.set_yticklabels(seg_names[:n_seg], fontsize=9)
                ax_h.set_xticks(range(n_pftv))
                ax_h.set_xticklabels(pft_short[:n_pftv], rotation=90, fontsize=5.5)
                ax_h.set_title(f'{lbl}\n{label}', fontsize=9, fontweight='bold')
                plt.colorbar(im, ax=ax_h, shrink=0.7, label=units)
                if N_NAT < n_pftv:
                    ax_h.axvline(N_NAT - 0.5, color='white', linewidth=1.5, linestyle='--')
            fig_3h.suptitle(f'{label} ({varname})', fontsize=11, fontweight='bold')
            p = _pdf(f'hydraulics_{varname}')
            _fig(s6, save_pdf_and_b64(fig_3h, p),
                 f'{label} heatmaps: {label1} | {label2} | difference', p)

    figures_data.append({
        'id': 'hydraulics', 'title': '6. Root Properties & Plant Hydraulics',
        'description': (
            'Comparison of root distribution parameters (α, β), segment hydraulic '
            'conductance (kmax), vulnerability curve parameters (ψ₅₀, ck), and '
            'stomatal water stress thresholds.'
        ),
        'figures': s6,
    })

    # -----------------------------------------------------------------------
    # 7. Litter Fractions & Wood Products
    # -----------------------------------------------------------------------
    print("  7. Litter & Wood")
    s7 = []
    fraction_groups = [
        ('Leaf Litter', [
            ('lf_flab', 'Labile',    '#f6ad55'),
            ('lf_fcel', 'Cellulose', '#68d391'),
            ('lf_flig', 'Lignin',    '#9b2335'),
        ]),
        ('Fine Root Litter', [
            ('fr_flab', 'Labile',    '#f6ad55'),
            ('fr_fcel', 'Cellulose', '#68d391'),
            ('fr_flig', 'Lignin',    '#9b2335'),
        ]),
        ('Wood Products', [
            ('pconv',    'Conversion',  '#fc8181'),
            ('pprod10',  '10-yr pool',  '#90cdf4'),
            ('pprod100', '100-yr pool', '#9ae6b4'),
        ]),
    ]
    fig7 = make_stacked_bar_comparison(
        nc1, nc2, fraction_groups, pft_short,
        f'Litter Fractions & Wood Products  ·  {label1} vs {label2}',
        label1, label2,
    )
    p = _pdf('litter_wood')
    _fig(s7, save_pdf_and_b64(fig7, p),
         f'Stacked litter and wood product fractions: {label1} (left) | {label2} (right)', p)

    figures_data.append({
        'id': 'litter-wood', 'title': '7. Litter Fractions & Wood Products',
        'description': 'Side-by-side stacked bar comparison of litter biochemical fractions and wood product allocation.',
        'figures': s7,
    })

    # -----------------------------------------------------------------------
    # 8. Fire Parameters
    # -----------------------------------------------------------------------
    print("  8. Fire")
    figures_data.append(_pft_section(
        'fire', '8. Fire Parameters',
        'Comparison of fire mortality, combustion completeness, spread rate, and duration.',
        [
            ([('fm_leaf',  'FM leaf',   '0–1'),
              ('fm_lstem', 'FM lstem',  '0–1'),
              ('fm_dstem', 'FM dstem',  '0–1'),
              ('fm_root',  'FM root',   '0–1'),
              ('fm_other', 'FM other',  '0–1')],
             'mortality'),
            ([('cc_leaf',  'CC leaf',  '0–1'),
              ('cc_lstem', 'CC lstem', '0–1'),
              ('cc_dstem', 'CC dstem', '0–1'),
              ('cc_other', 'CC other', '0–1'),
              ('fd_pft',   'Duration', 'hr'),
              ('fsr_pft',  'Spread',   'm/s')],
             'combustion'),
        ],
        'fire',
    ))

    # -----------------------------------------------------------------------
    # 9. N Fixation, Mycorrhizal & Bioclimatic
    # -----------------------------------------------------------------------
    print("  9. N-fix, Myc, Bioclim")
    figures_data.append(_pft_section(
        'n-fix-myc', '9. N Fixation, Mycorrhizal & Bioclimatic',
        'Comparison of N fixation cost parameters, mycorrhizal uptake constants, and bioclimatic limits.',
        [
            ([('FUN_fracfixers', 'FUN fracfix', 'fraction'),
              ('a_fix',          'a_fix',        '–'),
              ('b_fix',          'b_fix',        '1/°C'),
              ('c_fix',          'c_fix',        '°C'),
              ('s_fix',          's_fix',        'gC/gN'),
              ('fnitr',          'fnitr',        '–')],
             'nfix'),
            ([('akc_active', 'AM cost C', 'gC/m³'),
              ('akn_active', 'AM cost N', 'gC/m²'),
              ('ekc_active', 'EM cost C', 'gC/m³'),
              ('ekn_active', 'EM cost N', 'gC/m²'),
              ('kc_nonmyc',  'Nonmyc C',  'gC/m³'),
              ('perecm',     'Frac ECM',  'fraction')],
             'myc'),
            ([('pftpar28', 'Min cold T',  '°C'),
              ('pftpar29', 'Max cold T',  '°C'),
              ('pftpar30', 'Min GDD',     '°C·d'),
              ('pftpar31', 'Max warm T',  '°C')],
             'bioclim'),
        ],
        'nfix_myc',
    ))

    # -----------------------------------------------------------------------
    # 10. Global (allpfts) Parameters — scalar comparison tables
    # -----------------------------------------------------------------------
    print("  10. Global params")
    s10 = []

    groups_10 = [
        ('global_decomp',
         'Decomposition Rates, Turnover Times & SOM C:N',
         'Comparison of litter/SOM decomposition rates, turnover times, and C:N ratios',
         ['k_l1', 'k_l2', 'k_l3', 'k_s1', 'k_s2', 'k_s3', 'k_s4', 'k_frag',
          'tau_l1', 'tau_l2_l3', 'tau_s1', 'tau_s2', 'tau_s3', 'tau_cwd',
          'cn_s1', 'cn_s2', 'cn_s3', 'cn_s4',
          'rf_l1s1', 'rf_l2s2', 'rf_l3s3', 'rf_s1s2', 'rf_s2s3', 'rf_s3s4',
          'cwd_fcel', 'cwd_flig', 'decomp_depth_efolding', 'organic_max']),
        ('global_resp',
         'Respiration, Mortality & Turnover',
         'Comparison of Q₁₀ factors, mortality rates, and wood turnover rates',
         ['br_mr', 'q10_mr', 'q10_hr', 'froz_q10', 'r_mort', 'k_mort',
          'lwtop_ann', 'lake_decomp_fact', 'rootlitfrac', 'dayscrecover', 'fstor2tran']),
        ('global_ncycling',
         'Nitrogen Cycling (Global)',
         'Comparison of nitrification/denitrification and competition parameters',
         ['bdnr', 'dnp', 'k_nitr_max', 'sf_minn', 'sf_no3',
          'compet_decomp_nh4', 'compet_decomp_no3', 'compet_denit',
          'compet_nit', 'compet_plant_nh4', 'compet_plant_no3',
          'depth_runoff_Nloss', 'rc_npool', 'cnscalefactor']),
        ('global_ch4',
         'Methane Dynamics & Soil Gas Transport',
         'Comparison of CH₄ kinetics, Q₁₀ factors, and gas transport parameters',
         ['f_ch4', 'atmch4', 'k_m', 'k_m_o2', 'k_m_unsat',
          'q10ch4', 'q10_ch4oxid', 'vmax_ch4_oxid', 'vmax_oxid_unsat',
          'oxinhib', 'pHmin', 'pHmax',
          'nongrassporosratio', 'porosmin', 'unsat_aere_ratio',
          'vgc_max', 'redoxlag', 'redoxlag_vertical', 'smp_crit']),
        ('global_phenology_fire',
         'Phenology Triggers & Fire (Global)',
         'Comparison of leaf onset/offset thresholds, fire fuel parameters',
         ['crit_dayl', 'crit_offset_fdd', 'crit_offset_swi',
          'crit_onset_fdd', 'crit_onset_swi',
          'ndays_off', 'ndays_on', 'gddfunc_p1', 'gddfunc_p2',
          'soilpsi_off', 'soilpsi_on',
          'wcf', 'minfuel', 'me_herb', 'me_woody',
          'aereoxid', 'mino2lim', 'q10ch4base', 'capthick']),
    ]

    for pdf_name, title_str, caption, var_list in groups_10:
        fig = make_scalar_comparison_table(nc1, nc2, var_list, title_str, label1, label2)
        if fig is None:
            continue
        p = _pdf(pdf_name)
        _fig(s10, save_pdf_and_b64(fig, p), caption, p)

    figures_data.append({
        'id': 'global-params', 'title': '10. Global (allpfts) Parameters',
        'description': (
            'Comparison tables for all globally-applicable scalar parameters: '
            'decomposition and SOM turnover, respiration Q₁₀ factors, N cycling '
            'competition, methane dynamics, and phenology/fire triggers. '
            'Green = unchanged, red = increased, blue = decreased.'
        ),
        'figures': s10,
    })

    # -----------------------------------------------------------------------
    # Build HTML
    # -----------------------------------------------------------------------
    extra_meta = (
        f'<p><strong>File 1 ({label1}):</strong> {base1}</p>'
        f'<p><strong>File 2 ({label2}):</strong> {base2}</p>'
        f'<p><strong>PFTs:</strong> {n_pfts}</p>'
    )

    html = _build_html(
        title=f'CLM5 Parameter File Comparison — {label1} vs {label2}',
        filename=f'{label1} vs {label2}',
        extra_meta=extra_meta,
        figures_data=figures_data,
    )

    html_path = os.path.join(out_dir_base, output_name + '.html')
    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(html)

    nc1.close()
    nc2.close()
    print(f"\nDone → {html_path}")
    print(f"       {out_dir}/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compare two CLM5 parameter NetCDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python compare_paramfile.py params_A.nc params_B.nc A B\n'
            '  python compare_paramfile.py params_A.nc params_B.nc A B -o cmp_A_B\n'
        ),
    )
    parser.add_argument('file1',   help='First (reference) parameter NetCDF file')
    parser.add_argument('file2',   help='Second (comparison) parameter NetCDF file')
    parser.add_argument('label1',  help='Label for file1')
    parser.add_argument('label2',  help='Label for file2')
    parser.add_argument('-o', '--output', dest='output_name', default=None,
                        help='Output base name (default: comparison_<label1>_vs_<label2>)')
    args = parser.parse_args()

    main(args.file1, args.file2, args.label1, args.label2, args.output_name)
