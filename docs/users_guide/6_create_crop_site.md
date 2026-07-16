# Creating a Crop-Site / Agricultural Field Surface File

For single-site simulations of an agricultural field or flux tower
located in cropland, the standard CLM surface data file often contains
a mix of natural vegetation, crops, urban land, and other cover types
as derived from the raw-data input datasets in `$CSMDATA` (see
[Creation of surface file](4_create_surface_file.md)).  To represent a
uniform agricultural field you need to override these defaults so that
the model sees 100 % cropland with a single, well-defined crop type.

The `mkcropsite/mkcropsite.py` script automates this workflow.


## What the script changes

| Variable                                 | Before                       | After                                           |
|------------------------------------------|------------------------------|-------------------------------------------------|
| `PCT_CROP`                               | derived from land-cover data | **100 %**                                       |
| `PCT_NATVEG`                             | derived                      | **0 %**                                         |
| `PCT_LAKE`, `PCT_WETLAND`, `PCT_GLACIER` | derived                      | **0 %**                                         |
| `PCT_URBAN` (all density classes)        | derived                      | **0 %**                                         |
| `PCT_NAT_PFT`                            | mixed PFT distribution       | **100 % C3 non-arctic grass** (natpft index 13) |
| `PCT_CFT`                                | mixed crop distribution      | **100 % of the user-specified CFT**             |

All other variables (soil texture, topography, emission factors,
monthly LAI, urban building parameters, …) are preserved unchanged
from the input file.  Adjust them separately with additional
post-processing if needed.


## Workflow

### 1. Create a standard single-site surface file

Follow the steps in the earlier chapters of this guide to generate a surface
file for your site location.  The script requires a **single-site** file
(`lsmlat = lsmlon = 1`); it will refuse regional (multi-cell) files.

### 2. Choose your crop type

CLM5 BGC mode supports 64 Crop Functional Types (CFTs) with global indices
15–78.  Common European crops:

| CFT index | Crop                   |
|-----------|------------------------|
| 19        | Spring wheat rainfed   |
| 20        | Spring wheat irrigated |
| 21        | Winter wheat rainfed   |
| 22        | Winter wheat irrigated |
| 25        | Barley rainfed         |
| 29        | Rye rainfed            |
| 55        | Potatoes rainfed       |
| 59        | Rapeseed rainfed       |
| 65        | Sugarbeet rainfed      |

To see all CFTs present in your specific file, run:

```bash
python mkcropsite/mkcropsite.py <surfdata.nc> --list-crops
```

### 3. Run the script

```bash
python mkcropsite/mkcropsite.py <surfdata.nc> --crop-type <CFT> [-o output.nc]
```

The `--crop-type` argument accepts either the integer CFT index or a
case-insensitive name substring:

```bash
# By index:
python mkcropsite/mkcropsite.py surfdata.nc --crop-type 21

# By name:
python mkcropsite/mkcropsite.py surfdata.nc --crop-type "winter wheat rainfed"

# Custom output name:
python mkcropsite/mkcropsite.py surfdata.nc --crop-type 21 -o surfdata_winterwheat.nc
```

The script prints a summary of the applied changes and writes a **new
output file** without modifying the original.

### 4. Verify the result

Use `vizsurfdata/visualize_surfdata.py` to generate a visual report of the
modified surface file and confirm that the land cover and PFT settings look
as expected.
