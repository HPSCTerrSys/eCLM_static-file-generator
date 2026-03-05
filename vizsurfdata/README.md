# Python scripts for visualizing and comparing eCLM surface data files

## Scripts

### visualize_surfdata.py

Visualizes all variables in a CLM5 surface data NetCDF file, generating PDF figures and an HTML report.

```bash
python visualize_surfdata.py <surfdata.nc>
```

**Output:**
- `<filename>_figures/` - Directory containing PDF figures
- `<filename>.html` - Interactive HTML report with embedded figures

**Sections:** Site location map, basic parameters, land cover, natural PFTs, crop types, soil profiles, monthly LAI/SAI, urban parameters, emission factors, and summary.

### compare_surfdata.py

Compares two surface data files side-by-side, highlighting differences with color-coded visualizations.

```bash
python compare_surfdata.py <file1.nc> <file2.nc> <label1> <label2> [-o output_name]
```

**Arguments:**
- `file1.nc`, `file2.nc` - NetCDF files to compare
- `label1`, `label2` - Labels for legends and naming (e.g., "2005" "2006" or "control" "experiment")
- `-o output_name` - Optional custom output name (default: `comparison_<label1>_vs_<label2>`)

**Output:**
- `<output_name>_figures/` - Directory containing PDF figures
- `<output_name>.html` - Interactive HTML comparison report

**Color coding:** Green = no change, Red = increased, Blue = decreased

## Requirements

See [`../requirements.txt`](../requirements.txt). `cartopy` is optional — site location maps are skipped gracefully if it is not installed.
