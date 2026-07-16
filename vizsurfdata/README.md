# Python scripts for visualizing and comparing eCLM surface data files

`visualize_surfdata.py` and `compare_surfdata.py` auto-detect whether the
input file(s) are **single-site** (`lsmlat = lsmlon = 1`) or a **regional
grid** and activate the appropriate visualisation mode automatically.
`diff_surfdata.py` and `ensemble_surfdata.py` are text- and
ensemble-analysis tools respectively.

## Scripts

### visualize_surfdata.py

Visualizes all variables in a CLM5 surface data NetCDF file, generating PDF
figures and an HTML report.

```bash
python visualize_surfdata.py <surfdata.nc>
```

**Output:**
- `<filename>_figures/` – directory containing one PDF per section
- `<filename>.html` – self-contained HTML report with all figures embedded

**Sections and mode-specific behaviour:**

| # | Section                      | Single-site                                                   | Regional grid                                                                                                         |
|---|------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| 1 | Domain / site overview       | Cartopy point map + scalar cards                              | Cartopy bounding-box map + spatial maps of AREA, FMAX, SOIL\_COLOR, zbedrock, SLOPE, STD\_ELEV, LAKEDEPTH, peatf, gdp |
| 2 | Land cover fractions         | Pie chart + bar chart                                         | Spatial maps of PCT\_NATVEG, PCT\_CROP, PCT\_URBAN (total), PCT\_LAKE, PCT\_WETLAND, PCT\_GLACIER                     |
| 3 | Natural PFTs                 | Pie chart + horizontal bar chart                              | Spatial maps for each active PFT (max > 1 %) + domain-mean bar chart                                                  |
| 4 | Crop functional types        | Pie chart + bar chart + fertiliser bar                        | Spatial maps for active CFTs + domain-mean fertiliser bar                                                             |
| 5 | Soil properties              | Vertical profiles (sand, clay, organic) + stacked texture bar | Depth-mean spatial maps + domain-mean profiles with spatial std                                                       |
| 5b | Soil hydraulic parameters   | Vertical profiles per parameter (log scale for PSIS\_SAT, KSAT) | Domain-mean profiles + depth-averaged spatial maps (log colourbar for PSIS\_SAT, KSAT) |
| 6 | Monthly vegetation           | LAI / SAI / height time series per PFT                        | Domain-mean LAI / SAI time series + annual-mean LAI spatial maps per PFT                                              |
| 7 | Urban parameters             | Bar charts per density class                                  | PCT\_URBAN spatial maps + domain-mean bar charts for building parameters                                              |
| 8 | Emission factors & other     | Bar charts + glacier elevation chart + harvest bars           | Spatial maps of EF and harvest variables + domain-mean glacier chart                                                  |
| 9 | Summary                      | Pie charts + scalar table                                     | Grid of key spatial maps                                                                                              |

> **Note:** Section 5b is only produced when the file contains soil hydraulic
> parameters written by `soil_params_perturb.py`
> (`PSIS_SAT`, `THETAS`, `SHAPE_PARAM`, `KSAT` with `_adj` or plain suffix).

---

### compare_surfdata.py

Compares two CLM5 surface data files side-by-side, highlighting differences
with colour-coded visualisations.

```bash
python compare_surfdata.py <file1.nc> <file2.nc> <label1> <label2> [-o output_name]
```

**Arguments:**
- `file1.nc`, `file2.nc` – NetCDF files to compare (must be the same grid type)
- `label1`, `label2` – labels used in legends and output naming (e.g. `"2005" "2006"` or `"control" "experiment"`)
- `-o output_name` – optional custom output name (default: `comparison_<label1>_vs_<label2>`)

**Output:**
- `<output_name>_figures/` – directory containing one PDF per section
- `<output_name>.html` – self-contained HTML comparison report

**Colour coding:** Green = no change, Red = increased in file 2, Blue = decreased in file 2

**Mode-specific behaviour:**

| Mode | Comparison approach |
|------|---------------------|
| Single-site | Scalar comparison tables, side-by-side bar charts, overlaid soil profiles (with difference shading), LAI time-series overlays |
| Regional grid | Difference maps (file 2 − file 1), domain-mean comparison bar charts, diverging-colourmap spatial plots |

Soil hydraulic parameters (Section 5b) are compared when present in either
file: domain-mean profile overlays (log scale for PSIS\_SAT and KSAT) plus
depth-mean difference maps.

---

### diff_surfdata.py

Text-based diff tool for two CLM5 surface data NetCDF files.  Useful for
quick sanity checks and scripted pipelines where a graphical report is not
needed.

```bash
python diff_surfdata.py FILE_A.nc FILE_B.nc
python diff_surfdata.py FILE_A.nc FILE_B.nc --var PCT_SAND KSAT_adj
python diff_surfdata.py FILE_A.nc FILE_B.nc --tol 1e-6
python diff_surfdata.py FILE_A.nc FILE_B.nc --verbose
python diff_surfdata.py FILE_A.nc FILE_B.nc --summary
python diff_surfdata.py FILE_A.nc FILE_B.nc --max-rows 0
```

**Output sections (printed to stdout):**
1. Variables only in file A
2. Variables only in file B
3. Variables present in both but with differing values

For **single-site** files differences are shown element-by-element with
dimension-aware labels (soil depth, month, PFT name, urban class, …).

For **regional** files, per-slice statistics are printed by default
(`N/M cells`, `mean Δ`, `max|Δ|`, `RMSE`).  Use `--verbose` to force
element-level output.

**Options:**

| Flag | Description |
|------|-------------|
| `--var VAR [VAR …]` | Restrict comparison to listed variable names |
| `--tol FLOAT` | Absolute tolerance for considering values identical (default: 0) |
| `--verbose` | Force element-level output for regional files |
| `--summary` | Print only a one-line summary per differing variable |
| `--max-rows N` | Limit element-level rows per variable (0 = unlimited) |

---

### ensemble_surfdata.py

Produces per-layer distribution plots (box plots with individual member dots)
for an ensemble of single-site CLM5 surface data files.  Restricted to
**single-site** files and covers **soil properties** (Section 5) and
**soil hydraulic parameters** (Section 5b).

```bash
python ensemble_surfdata.py member_01.nc member_02.nc ... member_N.nc \
    --label ENSEMBLE_NAME [-o OUTPUT_DIR]

# Glob expansion
python ensemble_surfdata.py member_*.nc --label SaveCrops4EU
```

**Arguments:**
- Two or more single-site NetCDF files (positional)
- `--label NAME` – ensemble name used in titles and output filenames (default: `ensemble`)
- `-o OUTPUT_DIR` – output directory (default: `<label>_ensemble_figures/` next to the first input file)

**Output:**
- `<label>_ensemble_figures/` – one PDF per parameter
- `<label>_ensemble.html` – self-contained HTML report

**Figure design:** one horizontal box-and-whisker plot per parameter, with
one box per soil layer (depth increases downward).  Whiskers extend to
min/max across members; the IQR box and median line are shown; individual
member values are overlaid as dots with a small y-jitter.
PSIS\_SAT and KSAT use a logarithmic x-axis.

**Sections produced:**

| Section | Parameters |
|---------|------------|
| Soil Properties | PCT\_SAND, PCT\_CLAY, ORGANIC, silt (derived) |
| Soil Hydraulic Parameters | PSIS\_SAT, THETAS, SHAPE\_PARAM, KSAT (only when present) |

---

## Requirements

Install dependencies from the local `requirements.txt`:

```bash
pip install -r vizsurfdata/requirements.txt
```

| Package | Required | Purpose |
|---------|----------|---------|
| `numpy` | yes | array operations |
| `matplotlib` | yes | all plots |
| `netCDF4` | yes | reading `.nc` files |
| `cartopy` | optional | site / domain overview maps (skipped gracefully if absent) |

## Notes

- `visualize_surfdata.py` and `compare_surfdata.py` write output next to the
  input NetCDF file(s) by default.  `ensemble_surfdata.py` writes to
  `<label>_ensemble_figures/` next to the first input file unless `-o` is given.
- For regional grids with many active PFTs or CFTs the spatial-map figures can
  be large; PDF rendering may take a minute or two.
- Domain-mean values in regional mode are averaged over land cells only
  (determined from `LANDFRAC_PFT` or `PFTDATA_MASK`).
- `diff_surfdata.py` only requires `numpy` and `netCDF4` — no matplotlib needed.
