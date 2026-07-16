#!/usr/bin/env python3
"""
Ensemble Surface Data Visualization for CLM5 Surface Data Files
================================================================
Reads an ensemble of single-site CLM5 surface data NetCDF files and produces
per-layer distribution plots (box plots with member dots) for soil properties
and soil hydraulic parameters across ensemble members.

Restricted to single-site (1x1) files.

Usage:
  python ensemble_surfdata.py member_01.nc member_02.nc ... \\
      [--label ENSEMBLE_NAME] [-o OUTPUT_DIR]

  python ensemble_surfdata.py member_*.nc --label SaveCrops4EU
"""

import os
import sys
import argparse
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset

from visualize_surfdata import (
    HYD_PARAM_SPECS, SOIL_DEPTHS,
    detect_grid_type, detect_soil_hydraulic_params,
    get_1d_array, fig_to_base64,
)


# Soil texture parameters for Section 5 (single-site variables only)
# Each entry: (nc_varname, display_name, units, log_scale)
SOIL_TEXTURE_SPECS = [
    ('PCT_SAND', 'Sand Content',   '%',          False),
    ('PCT_CLAY', 'Clay Content',   '%',          False),
    ('ORGANIC',  'Organic Matter', 'kg/m\u00b3', False),
]


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def _plot_ensemble_profile(param_data, depths, title, units, log_scale=False,
                           color='#4299e1'):
    """Horizontal box-and-whisker plot of per-layer ensemble distribution.

    Parameters
    ----------
    param_data : ndarray, shape (n_members, n_lev)
    depths     : sequence of float, length n_lev
    log_scale  : bool — log x-axis (for PSIS_SAT, KSAT)

    Returns
    -------
    matplotlib Figure
    """
    n_members, n_lev = param_data.shape
    rng = np.random.default_rng(42)

    fig, ax = plt.subplots(figsize=(8, max(4, n_lev * 0.6 + 1.5)))

    layer_data = [param_data[:, l][np.isfinite(param_data[:, l])]
                  for l in range(n_lev)]

    ax.boxplot(
        layer_data,
        vert=False,
        positions=range(n_lev),
        whis=(0, 100),          # whiskers extend to min/max
        patch_artist=True,
        boxprops=dict(facecolor=color, alpha=0.45, linewidth=1.2),
        medianprops=dict(color='#2d3748', linewidth=2.2),
        whiskerprops=dict(linewidth=1.2, color='#4a5568'),
        capprops=dict(linewidth=1.5, color='#4a5568'),
        flierprops=dict(marker=''),  # outliers shown via dot overlay
    )

    # Individual member dots with slight y-jitter
    for l, vals in enumerate(layer_data):
        if vals.size == 0:
            continue
        jitter = rng.uniform(-0.18, 0.18, size=vals.size)
        ax.scatter(vals, np.full(vals.size, l) + jitter,
                   color='#2d3748', alpha=0.65, s=22, zorder=5, linewidths=0)

    ax.set_yticks(range(n_lev))
    ax.set_yticklabels([f'{d:.2f} m' for d in depths])
    ax.invert_yaxis()
    ax.set_xlabel(f'[{units}]')
    ax.set_title(f'{title}  (N\u202f=\u202f{n_members})', fontsize=12, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    if log_scale:
        ax.set_xscale('log')

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _create_html_report(figures_data, label, nc_files, output_dir):
    """Write a self-contained HTML report."""

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ensemble Surface Data Report &ndash; {label}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #2b6cb0 0%, #553c9a 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{
            background: rgba(255,255,255,0.96);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{ color: #2d3748; font-size: 2.2em; margin-bottom: 8px; }}
        .subtitle {{ color: #718096; font-size: 1.05em; }}
        .metadata {{
            margin-top: 18px;
            padding: 14px;
            background: #f7fafc;
            border-radius: 8px;
            font-size: 0.88em;
            color: #4a5568;
            line-height: 1.7;
        }}
        .nav {{
            background: rgba(255,255,255,0.96);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .nav h3 {{ color: #2d3748; margin-bottom: 12px; }}
        .nav ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 10px; }}
        .nav a {{
            display: inline-block;
            padding: 8px 16px;
            background: #2b6cb0;
            color: white;
            text-decoration: none;
            border-radius: 20px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        .nav a:hover {{ background: #2c5282; transform: translateY(-2px); }}
        .section {{
            background: rgba(255,255,255,0.96);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .section h2 {{
            color: #2d3748;
            border-bottom: 3px solid #2b6cb0;
            padding-bottom: 10px;
            margin-bottom: 18px;
        }}
        .section-description {{
            color: #718096;
            margin-bottom: 20px;
            font-style: italic;
        }}
        .figure-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }}
        .figure-container {{
            text-align: center;
            padding: 16px;
            background: #f7fafc;
            border-radius: 10px;
            flex: 1 1 340px;
            max-width: 520px;
        }}
        .figure-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .figure-caption {{
            margin-top: 12px;
            color: #4a5568;
            font-size: 0.9em;
        }}
        .download-btn {{
            display: inline-block;
            margin-top: 8px;
            padding: 6px 14px;
            background: #48bb78;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.82em;
            transition: background 0.3s ease;
        }}
        .download-btn:hover {{ background: #38a169; }}
        footer {{
            text-align: center;
            color: rgba(255,255,255,0.85);
            padding: 20px;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.6em; }}
            .figure-container {{ max-width: 100%; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>CLM5 Ensemble Surface Data Report</h1>
        <p class="subtitle">Per-layer parameter distributions across ensemble members</p>
        <div class="metadata">
            <strong>Ensemble:</strong> {label}<br>
            <strong>Members:</strong> {n_members}<br>
            <strong>Generated:</strong> {timestamp}<br>
            <strong>Files:</strong><br>{file_list}
        </div>
    </header>

    <nav class="nav">
        <h3>Quick Navigation</h3>
        <ul>{nav_links}</ul>
    </nav>

    {sections}

    <footer>
        <p>Generated by CLM5 Ensemble Surface Data Visualization Tool</p>
    </footer>
</div>
</body>
</html>"""

    sections_html = ''
    nav_links_html = ''

    for sec in figures_data:
        nav_links_html += f'<li><a href="#{sec["id"]}">{sec["title"]}</a></li>\n'

        figs_html = '<div class="figure-row">\n'
        for fd in sec['figures']:
            figs_html += f"""
            <div class="figure-container">
                <img src="data:image/png;base64,{fd['base64']}" alt="{fd['caption']}">
                <p class="figure-caption">{fd['caption']}</p>
                <a href="{fd['pdf_name']}" class="download-btn">Download PDF</a>
            </div>"""
        figs_html += '\n</div>'

        sections_html += f"""
        <section class="section" id="{sec['id']}">
            <h2>{sec['title']}</h2>
            <p class="section-description">{sec.get('description', '')}</p>
            {figs_html}
        </section>"""

    file_list_html = '<br>'.join(
        f'&nbsp;&nbsp;{os.path.basename(f)}' for f in nc_files
    )

    html_content = html_template.format(
        label=label,
        n_members=len(nc_files),
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        file_list=file_list_html,
        nav_links=nav_links_html,
        sections=sections_html,
    )

    html_path = os.path.join(output_dir, f'{label}_ensemble.html')
    with open(html_path, 'w') as fh:
        fh.write(html_content)

    return html_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Per-layer ensemble distribution plots for CLM5 surface data files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ensemble_surfdata.py member_*.nc --label SaveCrops4EU
  python ensemble_surfdata.py m01.nc m02.nc m03.nc -o /tmp/out --label Test
""")
    parser.add_argument('nc_files', nargs='+',
                        help='Two or more single-site CLM5 surface data NetCDF files')
    parser.add_argument('--label', default='ensemble',
                        help='Ensemble name used in titles and output filename (default: ensemble)')
    parser.add_argument('-o', '--output-dir', default=None,
                        help='Output directory (default: directory of first input file)')
    args = parser.parse_args()

    if len(args.nc_files) < 2:
        print('Error: at least two ensemble members required.')
        sys.exit(1)

    for f in args.nc_files:
        if not os.path.exists(f):
            print(f'Error: file not found: {f}')
            sys.exit(1)

    # Output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        first_dir = os.path.dirname(os.path.abspath(args.nc_files[0]))
        output_dir = os.path.join(first_dir, f'{args.label}_ensemble_figures')
    os.makedirs(output_dir, exist_ok=True)

    n_members = len(args.nc_files)
    print(f'Ensemble: {args.label}  ({n_members} members)')
    print(f'Output:   {output_dir}')

    # ------------------------------------------------------------------
    # Load data — reject regional files
    # ------------------------------------------------------------------
    print('Reading NetCDF files...')

    n_lev_tex = len(SOIL_DEPTHS)   # 10 standard soil layers

    # Soil texture arrays: (n_members, n_lev)
    tex_arrays = {base: np.full((n_members, n_lev_tex), np.nan)
                  for base, *_ in SOIL_TEXTURE_SPECS}

    # Hydraulic parameter arrays collected after we know n_lev and suffix
    hyd_arrays = {}   # base -> (n_members, n_lev) — built on first member that has them
    hyd_meta   = {}   # base -> (display, units, log_scale)
    hyd_n_lev  = None

    for m_idx, nc_path in enumerate(args.nc_files):
        nc = Dataset(nc_path, 'r')

        # Reject regional files
        if detect_grid_type(nc):
            print(f'Error: {os.path.basename(nc_path)} is a regional file. '
                  'This script supports single-site files only.')
            nc.close()
            sys.exit(1)

        # --- Soil texture ---
        for base, display, units_str, log_scale in SOIL_TEXTURE_SPECS:
            if base in nc.variables:
                arr = get_1d_array(nc.variables[base])
                n = min(len(arr), n_lev_tex)
                tex_arrays[base][m_idx, :n] = arr[:n]

        # --- Soil hydraulic parameters ---
        hyd_info = detect_soil_hydraulic_params(nc)
        if hyd_info is not None:
            suffix = hyd_info['suffix']
            n_lev_h = hyd_info['n_lev']

            if hyd_n_lev is None:
                hyd_n_lev = n_lev_h
                for base, display, units_str, log_scale in HYD_PARAM_SPECS:
                    vname = f'{base}{suffix}'
                    if vname in nc.variables:
                        hyd_arrays[base] = np.full((n_members, hyd_n_lev), np.nan)
                        hyd_meta[base]   = (display, units_str, log_scale)

            for base in list(hyd_arrays.keys()):
                vname = f'{base}{suffix}'
                if vname in nc.variables:
                    arr = get_1d_array(nc.variables[vname])
                    n = min(len(arr), hyd_n_lev)
                    hyd_arrays[base][m_idx, :n] = arr[:n]

        nc.close()
        print(f'  [{m_idx+1}/{n_members}] {os.path.basename(nc_path)}')

    depths_tex = SOIL_DEPTHS[:n_lev_tex]
    depths_hyd = SOIL_DEPTHS[:hyd_n_lev] if hyd_n_lev else []

    figures_data = []

    # ------------------------------------------------------------------
    # Section 5: Soil Properties
    # ------------------------------------------------------------------
    print('Creating Section 5: Soil Properties...')
    sec5_figs = []

    tex_colors = {
        'PCT_SAND': '#f6ad55',
        'PCT_CLAY': '#fc8181',
        'ORGANIC':  '#68d391',
    }

    for base, display, units_str, log_scale in SOIL_TEXTURE_SPECS:
        data = tex_arrays[base]
        fig = _plot_ensemble_profile(data, depths_tex, display, units_str,
                                     log_scale=log_scale,
                                     color=tex_colors.get(base, '#4299e1'))
        pdf_path = os.path.join(output_dir, f'05_ensemble_{base.lower()}.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        sec5_figs.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': f'Ensemble distribution of {display} per soil layer.',
            'base64': fig_to_base64(fig),
        })
        plt.close(fig)

    # Derived: silt = 100 - sand - clay
    if 'PCT_SAND' in tex_arrays and 'PCT_CLAY' in tex_arrays:
        silt_data = 100.0 - tex_arrays['PCT_SAND'] - tex_arrays['PCT_CLAY']
        fig = _plot_ensemble_profile(silt_data, depths_tex,
                                     'Silt Content (derived)', '%',
                                     color='#a0aec0')
        pdf_path = os.path.join(output_dir, '05_ensemble_pct_silt.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        sec5_figs.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Ensemble distribution of silt content (= 100 \u2212 sand \u2212 clay) per soil layer.',
            'base64': fig_to_base64(fig),
        })
        plt.close(fig)

    figures_data.append({
        'id': 'soil-properties',
        'title': 'Soil Properties',
        'description': (
            f'Per-layer distributions of soil texture (PCT_SAND, PCT_CLAY, ORGANIC) '
            f'across {n_members} ensemble members. '
            'Boxes show IQR, whiskers extend to min/max, dots are individual members.'
        ),
        'figures': sec5_figs,
    })

    # ------------------------------------------------------------------
    # Section 5b: Soil Hydraulic Parameters (optional)
    # ------------------------------------------------------------------
    if hyd_arrays:
        print('Creating Section 5b: Soil Hydraulic Parameters...')
        sec5b_figs = []

        hyd_colors = ['#4299e1', '#ed8936', '#48bb78', '#9f7aea']

        for c_idx, (base, (display, units_str, log_scale)) in enumerate(hyd_meta.items()):
            data = hyd_arrays[base]
            fig = _plot_ensemble_profile(data, depths_hyd, display, units_str,
                                         log_scale=log_scale,
                                         color=hyd_colors[c_idx % len(hyd_colors)])
            pdf_path = os.path.join(output_dir, f'05h_ensemble_{base.lower()}.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            sec5b_figs.append({
                'pdf_name': os.path.basename(pdf_path),
                'caption': (f'Ensemble distribution of {display} per soil layer'
                            + (' (log scale).' if log_scale else '.')),
                'base64': fig_to_base64(fig),
            })
            plt.close(fig)

        figures_data.append({
            'id': 'soil-hydraulic',
            'title': 'Soil Hydraulic Parameters',
            'description': (
                f'Per-layer distributions of soil hydraulic parameters '
                f'(PSIS_SAT, THETAS, SHAPE_PARAM, KSAT) across {n_members} ensemble members. '
                'Boxes show IQR, whiskers extend to min/max, dots are individual members. '
                'PSIS_SAT and KSAT use a logarithmic x-axis.'
            ),
            'figures': sec5b_figs,
        })
    else:
        print('  No soil hydraulic parameters found — Section 5b skipped.')

    # ------------------------------------------------------------------
    # HTML report
    # ------------------------------------------------------------------
    html_path = _create_html_report(figures_data, args.label, args.nc_files, output_dir)
    print(f'\nDone. Report: {html_path}')


if __name__ == '__main__':
    main()
