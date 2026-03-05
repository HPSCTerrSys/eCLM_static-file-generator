#!/usr/bin/env python3
"""
Surface Data Comparison Script for CLM5 Surface Data Files
===========================================================
This script compares two CLM5 surface data NetCDF files and creates
visualizations highlighting the differences, saving them as PDFs and
generating an HTML report.

Author: Generated for TSMP-PDAF preprocessing
Usage: python compare_surfdata.py <file1.nc> <file2.nc> [-o output_name]
"""

import os
import sys
import argparse
import base64
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from netCDF4 import Dataset

# Import shared constants and utilities from visualize_surfdata
from visualize_surfdata import (
    NATPFT_NAMES, CFT_NAMES, URBAN_TYPES, MONTH_NAMES, SOIL_DEPTHS,
    get_scalar_value, get_1d_array, fig_to_base64,
    create_site_location_figure
)


def extract_differing_parts(name1, name2):
    """Extract the parts of two filenames that differ."""
    # Remove common prefix
    min_len = min(len(name1), len(name2))
    prefix_end = 0
    for i in range(min_len):
        if name1[i] != name2[i]:
            break
        prefix_end = i + 1

    # Remove common suffix
    suffix_start1 = len(name1)
    suffix_start2 = len(name2)
    for i in range(1, min_len - prefix_end + 1):
        if name1[-i] != name2[-i]:
            break
        suffix_start1 = len(name1) - i + 1
        suffix_start2 = len(name2) - i + 1

    diff1 = name1[prefix_end:suffix_start1].strip('_')
    diff2 = name2[prefix_end:suffix_start2].strip('_')

    if diff1 and diff2:
        return f"{diff1}_vs_{diff2}"
    else:
        # Fallback to timestamp
        return datetime.now().strftime('%Y%m%d_%H%M%S')


def compute_difference(val1, val2):
    """Compute difference and percent change between two values."""
    diff = val2 - val1
    if val1 != 0:
        pct_change = (diff / abs(val1)) * 100
    elif val2 != 0:
        pct_change = np.inf if diff > 0 else -np.inf
    else:
        pct_change = 0
    return diff, pct_change


def get_change_color(diff, threshold=0.01):
    """Get color based on difference: green=same, red=increased, blue=decreased."""
    if abs(diff) < threshold:
        return '#48bb78'  # Green - no change
    elif diff > 0:
        return '#e53e3e'  # Red - increased
    else:
        return '#3182ce'  # Blue - decreased


def plot_comparison_bars(ax, labels, values1, values2, title, units, label1, label2):
    """Create side-by-side bar chart comparing two datasets."""
    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, values1, width, label=label1, color='#4299e1', edgecolor='#2d3748', alpha=0.8)
    bars2 = ax.bar(x + width/2, values2, width, label=label2, color='#ed8936', edgecolor='#2d3748', alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel(f'[{units}]')
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

    return bars1, bars2


def plot_difference_profile(ax, depths, values1, values2, title, units, label1, label2):
    """Create a soil profile comparison with difference shading."""
    diff = values2 - values1

    # Plot both profiles
    ax.plot(values1, depths, 'o-', color='#4299e1', linewidth=2, markersize=8, label=label1)
    ax.plot(values2, depths, 's-', color='#ed8936', linewidth=2, markersize=8, label=label2)

    # Shade the difference
    ax.fill_betweenx(depths, values1, values2, alpha=0.3,
                     color='#48bb78' if np.mean(diff) >= 0 else '#e53e3e')

    ax.invert_yaxis()
    ax.set_xlabel(f'{title} [{units}]')
    ax.set_ylabel('Depth (m)')
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def plot_monthly_comparison(ax, data1, data2, pft_idx, title, units, label1, label2, pft_name):
    """Plot monthly time series comparison for a specific PFT."""
    months = range(12)

    vals1 = data1[:, pft_idx, 0, 0]
    vals2 = data2[:, pft_idx, 0, 0]

    ax.plot(months, vals1, 'o-', color='#4299e1', linewidth=2, markersize=6, label=label1)
    ax.plot(months, vals2, 's-', color='#ed8936', linewidth=2, markersize=6, label=label2)
    ax.fill_between(months, vals1, vals2, alpha=0.3, color='#a0aec0')

    ax.set_xticks(months)
    ax.set_xticklabels(MONTH_NAMES)
    ax.set_xlabel('Month')
    ax.set_ylabel(f'[{units}]')
    ax.set_title(f'{title} - {pft_name}', fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def create_comparison_table(ax, params, title, label1='File 1', label2='File 2'):
    """Create a comparison table with color-coded differences."""
    ax.axis('off')

    # Table data: [Parameter, Label1, Label2, Difference, Change%]
    col_labels = ['Parameter', label1, label2, 'Difference', 'Change %']

    table_data = []
    cell_colors = []

    for param in params:
        name, val1, val2, units = param
        diff, pct = compute_difference(val1, val2)

        # Format values
        if isinstance(val1, float):
            if abs(val1) < 0.01 and val1 != 0:
                val1_str = f'{val1:.2e}'
                val2_str = f'{val2:.2e}'
                diff_str = f'{diff:.2e}'
            else:
                val1_str = f'{val1:.4f}'
                val2_str = f'{val2:.4f}'
                diff_str = f'{diff:.4f}'
        else:
            val1_str = str(val1)
            val2_str = str(val2)
            diff_str = str(diff)

        if np.isinf(pct):
            pct_str = 'N/A'
        else:
            pct_str = f'{pct:+.1f}%'

        table_data.append([f'{name} [{units}]', val1_str, val2_str, diff_str, pct_str])

        # Color based on difference
        color = get_change_color(diff, threshold=0.001)
        cell_colors.append(['white', 'white', 'white', color, color])

    table = ax.table(cellText=table_data, colLabels=col_labels,
                     loc='center', cellLoc='center', colWidths=[0.35, 0.15, 0.15, 0.15, 0.12])

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)

    # Style header
    for j in range(len(col_labels)):
        table[(0, j)].set_facecolor('#667eea')
        table[(0, j)].set_text_props(color='white', fontweight='bold')

    # Apply cell colors
    for i, row_colors in enumerate(cell_colors):
        for j, color in enumerate(row_colors):
            if color != 'white':
                table[(i + 1, j)].set_facecolor(color)
                table[(i + 1, j)].set_text_props(color='white', fontweight='bold')

    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)


def create_html_report(figures_data, file1, file2, label1, label2, output_dir, output_name):
    """Generate an HTML comparison report with all figures embedded."""

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surface Data Comparison Report</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
        .file-info {{
            margin-top: 20px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .file-card {{
            padding: 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        .file1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .file2 {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }}
        .file-card strong {{
            display: block;
            margin-bottom: 5px;
            font-size: 1.1em;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
            display: flex;
            gap: 20px;
            justify-content: center;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        .color-same {{ background: #48bb78; }}
        .color-increased {{ background: #e53e3e; }}
        .color-decreased {{ background: #3182ce; }}
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
            background: #f5576c;
            color: white;
            text-decoration: none;
            border-radius: 20px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        .nav a:hover {{
            background: #e53e3e;
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
            border-bottom: 3px solid #f5576c;
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
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2d3748;
        }}
        .stat-label {{
            color: #718096;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        footer {{
            text-align: center;
            color: white;
            padding: 20px;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8em; }}
            .file-info {{ grid-template-columns: 1fr; }}
            .nav ul {{ flex-direction: column; }}
            .legend {{ flex-direction: column; align-items: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CLM5 Surface Data Comparison Report</h1>
            <p class="subtitle">Side-by-side comparison of land surface parameters</p>
            <div class="file-info">
                <div class="file-card file1">
                    <strong>{label1}</strong>
                    {file1}
                </div>
                <div class="file-card file2">
                    <strong>{label2}</strong>
                    {file2}
                </div>
            </div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color color-same"></div>
                    <span>No significant change</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color color-increased"></div>
                    <span>Increased in {label2}</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color color-decreased"></div>
                    <span>Decreased in {label2}</span>
                </div>
            </div>
            <div class="metadata" style="margin-top: 15px; color: #718096; font-size: 0.9em;">
                <strong>Generated:</strong> {timestamp}
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
            <p>Generated by CLM5 Surface Data Comparison Tool</p>
            <p>For discussion of model input parameter changes</p>
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
        file1=os.path.basename(file1),
        file2=os.path.basename(file2),
        label1=label1,
        label2=label2,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        nav_links=nav_links_html,
        sections=sections_html
    )

    output_file = os.path.join(output_dir, f'{output_name}.html')
    with open(output_file, 'w') as f:
        f.write(html_content)

    return output_file


def main():
    """Main function to create comparison visualizations."""

    parser = argparse.ArgumentParser(
        description='Compare two CLM5 surface data NetCDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compare_surfdata.py file1.nc file2.nc 2005 2006
  python compare_surfdata.py file1.nc file2.nc control experiment -o my_comparison
        """
    )
    parser.add_argument('file1', help='First (reference) NetCDF file')
    parser.add_argument('file2', help='Second (comparison) NetCDF file')
    parser.add_argument('label1', help='Label for the first file (used in legends and naming)')
    parser.add_argument('label2', help='Label for the second file (used in legends and naming)')
    parser.add_argument('-o', '--output', dest='output_name', default=None,
                        help='Output name for HTML and figures directory (default: comparison_<label1>_vs_<label2>)')

    args = parser.parse_args()

    # Validate input files
    if not os.path.exists(args.file1):
        print(f"Error: File not found: {args.file1}")
        sys.exit(1)
    if not os.path.exists(args.file2):
        print(f"Error: File not found: {args.file2}")
        sys.exit(1)

    # Use labels for legends
    label1 = args.label1
    label2 = args.label2

    # Determine output name
    if args.output_name:
        output_name = args.output_name
    else:
        # Use labels for default output name
        output_name = f'comparison_{label1}_vs_{label2}'

    # Create output directory
    output_dir = os.path.dirname(args.file1)
    if not output_dir:
        output_dir = '.'
    pdf_dir = os.path.join(output_dir, f'{output_name}_figures')
    os.makedirs(pdf_dir, exist_ok=True)

    print(f"Reading NetCDF files...")
    print(f"  {label1}: {args.file1}")
    print(f"  {label2}: {args.file2}")

    nc1 = Dataset(args.file1, 'r')
    nc2 = Dataset(args.file2, 'r')

    # Get coordinates for both sites
    lon1 = get_scalar_value(nc1.variables['LONGXY'])
    lat1 = get_scalar_value(nc1.variables['LATIXY'])
    lon2 = get_scalar_value(nc2.variables['LONGXY'])
    lat2 = get_scalar_value(nc2.variables['LATIXY'])

    figures_data = []

    # =========================================================================
    # SECTION 0: Site Locations Map
    # =========================================================================
    print("Creating Site Locations Map...")
    site_map_figures = []
    fig_map = create_site_location_figure(
        [lon1, lon2], [lat1, lat2], labels=[label1, label2])
    if fig_map is not None:
        pdf_path = os.path.join(pdf_dir, '00_site_locations.pdf')
        fig_map.savefig(pdf_path, bbox_inches='tight')
        site_map_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': (f'Political map showing the locations of both sites: '
                        f'{label1} ({lon1:.3f}°E, {lat1:.3f}°N) and '
                        f'{label2} ({lon2:.3f}°E, {lat2:.3f}°N).'),
            'base64': fig_to_base64(fig_map)
        })
        plt.close(fig_map)

    if site_map_figures:
        figures_data.append({
            'id': 'site-locations',
            'title': 'Site Locations',
            'description': 'Political map showing the geographic locations of both sites.',
            'figures': site_map_figures
        })

    # =========================================================================
    # SECTION 1: Scalar Parameters Comparison
    # =========================================================================
    print("Creating Section 1: Scalar Parameters Comparison...")
    section1_figures = []

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Location and basic parameters
    basic_params = [
        ('LONGXY', 'degrees E'),
        ('LATIXY', 'degrees N'),
        ('AREA', 'km^2'),
        ('FMAX', 'unitless'),
        ('zbedrock', 'm'),
        ('SLOPE', 'degrees'),
        ('STD_ELEV', 'm'),
        ('gdp', 'unitless'),
    ]

    basic_data = []
    for var_name, units in basic_params:
        val1 = get_scalar_value(nc1.variables[var_name])
        val2 = get_scalar_value(nc2.variables[var_name])
        basic_data.append((var_name, val1, val2, units))

    create_comparison_table(axes[0, 0], basic_data, 'Basic Site Parameters', label1, label2)

    # Land cover fractions
    land_params = [
        ('PCT_NATVEG', '%'),
        ('PCT_CROP', '%'),
        ('PCT_LAKE', '%'),
        ('PCT_WETLAND', '%'),
        ('PCT_GLACIER', '%'),
        ('peatf', 'fraction'),
        ('LANDFRAC_PFT', 'fraction'),
    ]

    land_data = []
    for var_name, units in land_params:
        val1 = get_scalar_value(nc1.variables[var_name])
        val2 = get_scalar_value(nc2.variables[var_name])
        land_data.append((var_name, val1, val2, units))

    # Add total urban
    urban1 = np.sum(get_1d_array(nc1.variables['PCT_URBAN']))
    urban2 = np.sum(get_1d_array(nc2.variables['PCT_URBAN']))
    land_data.append(('PCT_URBAN (total)', urban1, urban2, '%'))

    create_comparison_table(axes[0, 1], land_data, 'Land Cover Fractions', label1, label2)

    # Soil parameters
    soil_params = [
        ('SOIL_COLOR', 'index'),
        ('mxsoil_color', 'count'),
    ]

    soil_data = []
    for var_name, units in soil_params:
        val1 = get_scalar_value(nc1.variables[var_name])
        val2 = get_scalar_value(nc2.variables[var_name])
        soil_data.append((var_name, val1, val2, units))

    create_comparison_table(axes[1, 0], soil_data, 'Soil Parameters', label1, label2)

    # Emission factors
    ef_params = [
        ('EF1_BTR', 'unitless'),
        ('EF1_FET', 'unitless'),
        ('EF1_FDT', 'unitless'),
        ('EF1_SHR', 'unitless'),
        ('EF1_GRS', 'unitless'),
        ('EF1_CRP', 'unitless'),
    ]

    ef_data = []
    for var_name, units in ef_params:
        val1 = get_scalar_value(nc1.variables[var_name])
        val2 = get_scalar_value(nc2.variables[var_name])
        ef_data.append((var_name, val1, val2, units))

    create_comparison_table(axes[1, 1], ef_data, 'Emission Factors', label1, label2)

    fig.suptitle('Scalar Parameters Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '01_scalar_comparison.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section1_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Comparison of scalar parameters: basic site info, land cover fractions, soil parameters, and emission factors.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'scalar-comparison',
        'title': 'Scalar Parameters',
        'description': 'Comparison of single-value parameters. Green indicates no change, red indicates increase in File 2, blue indicates decrease.',
        'figures': section1_figures
    })

    # =========================================================================
    # SECTION 2: Land Cover Comparison
    # =========================================================================
    print("Creating Section 2: Land Cover Comparison...")
    section2_figures = []

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Major land cover comparison
    land_labels = ['Natural Veg', 'Cropland', 'Urban', 'Lake', 'Wetland', 'Glacier']
    land_vals1 = [
        get_scalar_value(nc1.variables['PCT_NATVEG']),
        get_scalar_value(nc1.variables['PCT_CROP']),
        np.sum(get_1d_array(nc1.variables['PCT_URBAN'])),
        get_scalar_value(nc1.variables['PCT_LAKE']),
        get_scalar_value(nc1.variables['PCT_WETLAND']),
        get_scalar_value(nc1.variables['PCT_GLACIER'])
    ]
    land_vals2 = [
        get_scalar_value(nc2.variables['PCT_NATVEG']),
        get_scalar_value(nc2.variables['PCT_CROP']),
        np.sum(get_1d_array(nc2.variables['PCT_URBAN'])),
        get_scalar_value(nc2.variables['PCT_LAKE']),
        get_scalar_value(nc2.variables['PCT_WETLAND']),
        get_scalar_value(nc2.variables['PCT_GLACIER'])
    ]

    plot_comparison_bars(axes[0], land_labels, land_vals1, land_vals2,
                        'Major Land Cover Types', '%', label1, label2)

    # Difference bar chart
    diffs = np.array(land_vals2) - np.array(land_vals1)
    colors = [get_change_color(d, 0.01) for d in diffs]
    axes[1].bar(land_labels, diffs, color=colors, edgecolor='#2d3748')
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1].set_ylabel('Difference (File2 - File1) [%]')
    axes[1].set_title('Land Cover Change', fontsize=11, fontweight='bold')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].grid(axis='y', alpha=0.3)

    for i, (d, label) in enumerate(zip(diffs, land_labels)):
        if abs(d) > 0.01:
            axes[1].text(i, d + 0.1 * np.sign(d), f'{d:+.2f}', ha='center', fontsize=9)

    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '02_land_cover_comparison.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section2_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Side-by-side comparison of major land cover types and their differences.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'land-cover-comparison',
        'title': 'Land Cover Comparison',
        'description': 'Comparison of major land cover type fractions between the two files.',
        'figures': section2_figures
    })

    # =========================================================================
    # SECTION 3: Natural PFT Comparison
    # =========================================================================
    print("Creating Section 3: Natural PFT Comparison...")
    section3_figures = []

    pct_nat_pft1 = get_1d_array(nc1.variables['PCT_NAT_PFT'])
    pct_nat_pft2 = get_1d_array(nc2.variables['PCT_NAT_PFT'])
    natpft_labels = [NATPFT_NAMES.get(i, f'PFT {i}')[:25] for i in range(15)]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Side-by-side comparison
    plot_comparison_bars(axes[0], natpft_labels, pct_nat_pft1, pct_nat_pft2,
                        'Natural PFT Distribution', '%', label1, label2)

    # Difference plot
    diffs = pct_nat_pft2 - pct_nat_pft1
    colors = [get_change_color(d, 0.1) for d in diffs]
    y_pos = range(15)
    axes[1].barh(y_pos, diffs, color=colors, edgecolor='#2d3748')
    axes[1].axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels(natpft_labels, fontsize=8)
    axes[1].set_xlabel('Difference (File2 - File1) [%]')
    axes[1].set_title('Natural PFT Change', fontsize=11, fontweight='bold')
    axes[1].grid(axis='x', alpha=0.3)

    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '03_natural_pft_comparison.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section3_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Comparison of natural Plant Functional Type distributions.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'natural-pft-comparison',
        'title': 'Natural PFT Comparison',
        'description': 'Comparison of natural Plant Functional Type (PFT) distributions within the natural vegetation landunit.',
        'figures': section3_figures
    })

    # =========================================================================
    # SECTION 4: Crop Functional Types Comparison
    # =========================================================================
    print("Creating Section 4: CFT Comparison...")
    section4_figures = []

    pct_cft1 = get_1d_array(nc1.variables['PCT_CFT'])
    pct_cft2 = get_1d_array(nc2.variables['PCT_CFT'])
    cft_indices = nc1.variables['cft'][:]

    # Find CFTs that are non-zero in either file
    nonzero_mask = (pct_cft1 > 0.1) | (pct_cft2 > 0.1)

    if np.any(nonzero_mask):
        nonzero_cft1 = pct_cft1[nonzero_mask]
        nonzero_cft2 = pct_cft2[nonzero_mask]
        nonzero_indices = cft_indices[nonzero_mask]
        nonzero_labels = [CFT_NAMES.get(int(i), f'CFT {i}')[:25] for i in nonzero_indices]

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))

        plot_comparison_bars(axes[0], nonzero_labels, nonzero_cft1, nonzero_cft2,
                            'Crop Type Distribution', '%', label1, label2)

        # Difference plot
        diffs = nonzero_cft2 - nonzero_cft1
        colors = [get_change_color(d, 0.1) for d in diffs]
        y_pos = range(len(nonzero_labels))
        axes[1].barh(y_pos, diffs, color=colors, edgecolor='#2d3748')
        axes[1].axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        axes[1].set_yticks(y_pos)
        axes[1].set_yticklabels(nonzero_labels, fontsize=8)
        axes[1].set_xlabel('Difference (File2 - File1) [%]')
        axes[1].set_title('Crop Type Change', fontsize=11, fontweight='bold')
        axes[1].grid(axis='x', alpha=0.3)

        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '04_cft_comparison.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section4_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Comparison of Crop Functional Type distributions (showing only non-zero CFTs).',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    figures_data.append({
        'id': 'cft-comparison',
        'title': 'Crop Functional Types Comparison',
        'description': 'Comparison of Crop Functional Type (CFT) distributions within the crop landunit.',
        'figures': section4_figures
    })

    # =========================================================================
    # SECTION 5: Soil Properties Comparison
    # =========================================================================
    print("Creating Section 5: Soil Properties Comparison...")
    section5_figures = []

    fig, axes = plt.subplots(1, 3, figsize=(15, 6))

    # Sand
    sand1 = get_1d_array(nc1.variables['PCT_SAND'])
    sand2 = get_1d_array(nc2.variables['PCT_SAND'])
    plot_difference_profile(axes[0], SOIL_DEPTHS, sand1, sand2, 'Sand Content', '%', label1, label2)

    # Clay
    clay1 = get_1d_array(nc1.variables['PCT_CLAY'])
    clay2 = get_1d_array(nc2.variables['PCT_CLAY'])
    plot_difference_profile(axes[1], SOIL_DEPTHS, clay1, clay2, 'Clay Content', '%', label1, label2)

    # Organic
    org1 = get_1d_array(nc1.variables['ORGANIC'])
    org2 = get_1d_array(nc2.variables['ORGANIC'])
    plot_difference_profile(axes[2], SOIL_DEPTHS, org1, org2, 'Organic Matter', 'kg/m3', label1, label2)

    fig.suptitle('Soil Properties Comparison by Depth', fontsize=14, fontweight='bold')
    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '05_soil_comparison.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section5_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Vertical profiles of soil properties with shaded areas showing differences between files.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    # Soil difference table
    fig, ax = plt.subplots(figsize=(14, 8))

    soil_layer_data = []
    for i, depth in enumerate(SOIL_DEPTHS):
        soil_layer_data.append((f'Sand @ {depth:.2f}m', sand1[i], sand2[i], '%'))
        soil_layer_data.append((f'Clay @ {depth:.2f}m', clay1[i], clay2[i], '%'))
        soil_layer_data.append((f'Organic @ {depth:.2f}m', org1[i], org2[i], 'kg/m3'))

    # Only show layers with differences
    diff_layers = [(n, v1, v2, u) for n, v1, v2, u in soil_layer_data if abs(v2 - v1) > 0.01]

    if diff_layers:
        create_comparison_table(ax, diff_layers[:15], 'Soil Properties with Differences', label1, label2)
    else:
        ax.text(0.5, 0.5, 'No significant differences in soil properties',
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.axis('off')

    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '05b_soil_diff_table.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section5_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Table of soil properties showing layers with significant differences.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'soil-comparison',
        'title': 'Soil Properties Comparison',
        'description': 'Comparison of soil texture (sand, clay) and organic matter content across depth layers.',
        'figures': section5_figures
    })

    # =========================================================================
    # SECTION 6: Monthly LAI Comparison
    # =========================================================================
    print("Creating Section 6: Monthly LAI Comparison...")
    section6_figures = []

    lai1 = nc1.variables['MONTHLY_LAI'][:]
    lai2 = nc2.variables['MONTHLY_LAI'][:]

    # Combine PFT names
    all_pft_names = {**NATPFT_NAMES, **CFT_NAMES}

    # Find PFTs with non-zero LAI in either file
    active_pfts = []
    for pft in range(79):
        if np.any(lai1[:, pft, 0, 0] > 0) or np.any(lai2[:, pft, 0, 0] > 0):
            active_pfts.append(pft)

    # Plot comparison for top active PFTs
    n_plots = min(6, len(active_pfts))
    if n_plots > 0:
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        for i, pft_idx in enumerate(active_pfts[:n_plots]):
            pft_name = all_pft_names.get(pft_idx, f'PFT {pft_idx}')[:30]
            plot_monthly_comparison(axes[i], lai1, lai2, pft_idx, 'LAI', 'm2/m2', label1, label2, pft_name)

        # Hide unused axes
        for i in range(n_plots, 6):
            axes[i].axis('off')

        fig.suptitle('Monthly LAI Comparison by PFT', fontsize=14, fontweight='bold')
        plt.tight_layout()
        pdf_path = os.path.join(pdf_dir, '06_lai_comparison.pdf')
        fig.savefig(pdf_path, bbox_inches='tight')
        section6_figures.append({
            'pdf_name': os.path.basename(pdf_path),
            'caption': 'Monthly Leaf Area Index (LAI) comparison for active PFTs. Shaded area shows the difference.',
            'base64': fig_to_base64(fig)
        })
        plt.close(fig)

    # LAI difference heatmap
    fig, ax = plt.subplots(figsize=(14, 8))

    if len(active_pfts) > 0:
        lai_diff_matrix = np.zeros((len(active_pfts[:15]), 12))
        for i, pft in enumerate(active_pfts[:15]):
            lai_diff_matrix[i, :] = lai2[:, pft, 0, 0] - lai1[:, pft, 0, 0]

        im = ax.imshow(lai_diff_matrix, cmap='RdBu_r', aspect='auto', vmin=-np.max(np.abs(lai_diff_matrix)), vmax=np.max(np.abs(lai_diff_matrix)))
        ax.set_xticks(range(12))
        ax.set_xticklabels(MONTH_NAMES)
        ax.set_yticks(range(len(active_pfts[:15])))
        ax.set_yticklabels([all_pft_names.get(p, f'PFT {p}')[:25] for p in active_pfts[:15]], fontsize=8)
        ax.set_title('LAI Difference (File2 - File1)', fontsize=12, fontweight='bold')
        plt.colorbar(im, ax=ax, label='LAI difference (m2/m2)')

    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '06b_lai_diff_heatmap.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section6_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Heatmap of LAI differences by PFT and month. Blue = decrease, Red = increase in File 2.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'lai-comparison',
        'title': 'Monthly LAI Comparison',
        'description': 'Comparison of monthly Leaf Area Index values for active Plant Functional Types.',
        'figures': section6_figures
    })

    # =========================================================================
    # SECTION 7: Urban Parameters Comparison
    # =========================================================================
    print("Creating Section 7: Urban Parameters Comparison...")
    section7_figures = []

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # Urban percent
    pct_urban1 = get_1d_array(nc1.variables['PCT_URBAN'])
    pct_urban2 = get_1d_array(nc2.variables['PCT_URBAN'])
    plot_comparison_bars(axes[0, 0], URBAN_TYPES, pct_urban1, pct_urban2,
                        'Urban Fraction', '%', label1, label2)

    # Canyon HWR
    hwr1 = get_1d_array(nc1.variables['CANYON_HWR'])
    hwr2 = get_1d_array(nc2.variables['CANYON_HWR'])
    plot_comparison_bars(axes[0, 1], URBAN_TYPES, hwr1, hwr2,
                        'Canyon H/W Ratio', 'ratio', label1, label2)

    # Roof height
    ht1 = get_1d_array(nc1.variables['HT_ROOF'])
    ht2 = get_1d_array(nc2.variables['HT_ROOF'])
    plot_comparison_bars(axes[0, 2], URBAN_TYPES, ht1, ht2,
                        'Roof Height', 'm', label1, label2)

    # Building temperature
    tb1 = get_1d_array(nc1.variables['T_BUILDING_MIN']) - 273.15
    tb2 = get_1d_array(nc2.variables['T_BUILDING_MIN']) - 273.15
    plot_comparison_bars(axes[1, 0], URBAN_TYPES, tb1, tb2,
                        'Min Building Temp', 'C', label1, label2)

    # Roof fraction
    rf1 = get_1d_array(nc1.variables['WTLUNIT_ROOF'])
    rf2 = get_1d_array(nc2.variables['WTLUNIT_ROOF'])
    plot_comparison_bars(axes[1, 1], URBAN_TYPES, rf1, rf2,
                        'Roof Fraction', 'fraction', label1, label2)

    # Pervious road fraction
    pr1 = get_1d_array(nc1.variables['WTROAD_PERV'])
    pr2 = get_1d_array(nc2.variables['WTROAD_PERV'])
    plot_comparison_bars(axes[1, 2], URBAN_TYPES, pr1, pr2,
                        'Pervious Road Fraction', 'fraction', label1, label2)

    fig.suptitle('Urban Parameters Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '07_urban_comparison.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section7_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Comparison of urban parameters across three density classes.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'urban-comparison',
        'title': 'Urban Parameters Comparison',
        'description': 'Comparison of urban canyon and building parameters for three density classes.',
        'figures': section7_figures
    })

    # =========================================================================
    # SECTION 8: Summary of All Differences
    # =========================================================================
    print("Creating Section 8: Summary of Differences...")
    section8_figures = []

    fig = plt.figure(figsize=(16, 12))

    # Count differences
    all_diffs = []

    # Scalar differences
    scalar_vars = ['LONGXY', 'LATIXY', 'AREA', 'FMAX', 'zbedrock', 'SLOPE', 'STD_ELEV',
                   'PCT_NATVEG', 'PCT_CROP', 'PCT_LAKE', 'PCT_WETLAND', 'PCT_GLACIER',
                   'SOIL_COLOR', 'peatf', 'gdp', 'LAKEDEPTH']

    for var in scalar_vars:
        try:
            v1 = get_scalar_value(nc1.variables[var])
            v2 = get_scalar_value(nc2.variables[var])
            diff = abs(v2 - v1)
            if diff > 0.001:
                all_diffs.append((var, v1, v2, diff))
        except:
            pass

    # Create summary visualization
    ax1 = fig.add_subplot(2, 2, 1)

    n_total = len(scalar_vars) + 15 + 64 + 30 + 20  # approximate total variables
    n_changed = len(all_diffs)
    n_same = n_total - n_changed

    ax1.pie([n_same, n_changed], labels=['Unchanged', 'Changed'],
            colors=['#48bb78', '#e53e3e'], autopct='%1.1f%%', startangle=90)
    ax1.set_title('Overall Parameter Changes', fontsize=12, fontweight='bold')

    # Top differences table
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.axis('off')

    if all_diffs:
        # Sort by absolute difference
        sorted_diffs = sorted(all_diffs, key=lambda x: x[3], reverse=True)[:10]
        top_diff_data = [(name, v1, v2, 'various') for name, v1, v2, _ in sorted_diffs]
        create_comparison_table(ax2, top_diff_data, 'Top 10 Scalar Differences', label1, label2)
    else:
        ax2.text(0.5, 0.5, 'No significant scalar differences found',
                ha='center', va='center', fontsize=14)

    # Land cover change summary
    ax3 = fig.add_subplot(2, 2, 3)
    land_changes = np.array(land_vals2) - np.array(land_vals1)
    colors = [get_change_color(d, 0.01) for d in land_changes]
    bars = ax3.barh(land_labels, land_changes, color=colors, edgecolor='#2d3748')
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_xlabel('Change in Coverage (%)')
    ax3.set_title('Land Cover Changes Summary', fontsize=12, fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)

    # PFT change summary
    ax4 = fig.add_subplot(2, 2, 4)
    pft_diffs = pct_nat_pft2 - pct_nat_pft1
    significant_pft_changes = [(NATPFT_NAMES.get(i, f'PFT {i}')[:20], pft_diffs[i])
                               for i in range(15) if abs(pft_diffs[i]) > 0.1]

    if significant_pft_changes:
        labels, values = zip(*significant_pft_changes)
        colors = [get_change_color(v, 0.1) for v in values]
        ax4.barh(range(len(labels)), values, color=colors, edgecolor='#2d3748')
        ax4.set_yticks(range(len(labels)))
        ax4.set_yticklabels(labels, fontsize=9)
        ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax4.set_xlabel('Change in PFT Coverage (%)')
        ax4.set_title('Significant PFT Changes', fontsize=12, fontweight='bold')
        ax4.grid(axis='x', alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'No significant PFT changes',
                ha='center', va='center', fontsize=14)
        ax4.axis('off')

    fig.suptitle('Summary of All Differences', fontsize=14, fontweight='bold')
    plt.tight_layout()
    pdf_path = os.path.join(pdf_dir, '08_summary.pdf')
    fig.savefig(pdf_path, bbox_inches='tight')
    section8_figures.append({
        'pdf_name': os.path.basename(pdf_path),
        'caption': 'Summary overview of all differences between the two surface data files.',
        'base64': fig_to_base64(fig)
    })
    plt.close(fig)

    figures_data.append({
        'id': 'summary',
        'title': 'Summary of Differences',
        'description': 'A comprehensive summary of all parameter differences for quick reference.',
        'figures': section8_figures
    })

    # Close NetCDF files
    nc1.close()
    nc2.close()

    # Generate HTML report
    print("Generating HTML report...")
    html_file = create_html_report(figures_data, args.file1, args.file2, label1, label2, output_dir, output_name)

    print(f"\nComparison complete!")
    print(f"PDF figures saved in: {pdf_dir}")
    print(f"HTML report saved as: {html_file}")

    return html_file


if __name__ == '__main__':
    main()
