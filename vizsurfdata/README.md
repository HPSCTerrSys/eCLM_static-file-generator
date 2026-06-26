# Python scripts for visualizing and comparing eCLM surface data files

Both scripts auto-detect whether the input file(s) are **single-site**
(`lsmlat = lsmlon = 1`) or a **regional grid** and activate the appropriate
visualisation mode automatically.

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

| # | Section                  | Single-site                                                   | Regional grid                                                                                                         |
|---|--------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| 1 | Domain / site overview   | Cartopy point map + scalar cards                              | Cartopy bounding-box map + spatial maps of AREA, FMAX, SOIL\_COLOR, zbedrock, SLOPE, STD\_ELEV, LAKEDEPTH, peatf, gdp |
| 2 | Land cover fractions     | Pie chart + bar chart                                         | Spatial maps of PCT\_NATVEG, PCT\_CROP, PCT\_URBAN (total), PCT\_LAKE, PCT\_WETLAND, PCT\_GLACIER                     |
| 3 | Natural PFTs             | Pie chart + horizontal bar chart                              | Spatial maps for each active PFT (max > 1 %) + domain-mean bar chart                                                  |
| 4 | Crop functional types    | Pie chart + bar chart + fertiliser bar                        | Spatial maps for active CFTs + domain-mean fertiliser bar                                                             |
| 5 | Soil properties          | Vertical profiles (sand, clay, organic) + stacked texture bar | Depth-mean spatial maps + domain-mean profiles with spatial std                                                       |
| 6 | Monthly vegetation       | LAI / SAI / height time series per PFT                        | Domain-mean LAI / SAI time series + annual-mean LAI spatial maps per PFT                                              |
| 7 | Urban parameters         | Bar charts per density class                                  | PCT\_URBAN spatial maps + domain-mean bar charts for building parameters                                              |
| 8 | Emission factors & other | Bar charts + glacier elevation chart + harvest bars           | Spatial maps of EF and harvest variables + domain-mean glacier chart                                                  |
| 9 | Summary                  | Pie charts + scalar table                                     | Grid of key spatial maps                                                                                              |

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
| Single-site | Scalar comparison tables, side-by-side bar charts, overlaid soil profiles, LAI time-series overlays |
| Regional grid | Difference maps (file 2 − file 1), domain-mean comparison bar charts, diverging-colourmap spatial plots |

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

- Both scripts write output next to the input NetCDF file.
- For regional grids with many active PFTs or CFTs the spatial-map figures can
  be large; PDF rendering may take a minute or two.
- Domain-mean values shown in regional mode are averaged over land cells only
  (determined from `LANDFRAC_PFT` or `PFTDATA_MASK`).
