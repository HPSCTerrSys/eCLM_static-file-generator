# mksubgrid — Geographic subgrid extraction

Extract a rectangular geographic subgrid from eCLM domain and surface data
files. Two independent implementations are provided; they produce equivalent
results and can be used interchangeably.

Both files share the same curvilinear grid (rotated-pole EUR-CORDEX). Because
lat/lon values do not map linearly to array indices in such a grid, simply
slicing at fixed index offsets is not sufficient — the grid coordinates must be
consulted first to find the enclosing rectangular i/j index block.

---

## Scripts

### `subset_nco.py` — Python + NCO

Uses **xarray** to scan the 2D coordinate arrays of the domain file and locate
the index bounds, then delegates the actual file cutting to **NCO**'s `ncks`.

**Dependencies:** Python 3 (numpy, xarray), NCO

```bash
python subset_nco.py \
    --domain    domain.lnd.EUR-0275.nc \
    --surfdata  surfdata_EUR-0275.nc \
    --out-domain    domain.lnd.ALP-0275.nc \
    --out-surfdata  surfdata_ALP-0275.nc \
    --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48
```

---

### `subset_cdo.sh` — CDO

Uses **CDO**'s `sellonlatbox` operator to extract the domain file. CDO
recognises the CF-standard coordinate variables (`xc`, `yc`) in the domain
file directly and determines the index bounds internally.

**Dependencies:** CDO

```bash
./subset_cdo.sh \
    --domain    domain.lnd.EUR-0275.nc \
    --surfdata  surfdata_EUR-0275.nc \
    --out-domain    domain.lnd.ALP-0275.nc \
    --out-surfdata  surfdata_ALP-0275.nc \
    --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48
```

---

## Notes common to both scripts

- **Longitude convention** — values must be given in the same convention as
  the input files. If the files were post-processed with `xc + 360` (negative
  longitudes shifted to 0–360), use the shifted values here too.
- **Bounding box vs. index box** — the output domain may be slightly larger
  than requested. The curvilinear grid is axis-aligned in rotated-pole space,
  not in geographic space, so the enclosing rectangular index block will
  include a few cells outside the requested lat/lon box. These cells retain
  their original `mask`/`frac` values and are treated as inactive by eCLM.

---

## Pros and cons

|  | `subset_nco.py` | `subset_cdo.sh` |
|---|---|---|
| **Variables preserved** | All variables, all shapes | Drops variables with two non-spatial, non-time leading dimensions (see below) |
| **Output fidelity** | Minimal changes: only sliced dimensions differ from input (see below) | Restructures the file: reorders dimensions, variables, and attributes (see below) |
| **Coordinate handling** | Reads any coordinate name from the domain file explicitly | Requires CF-standard names (`xc`, `yc`) in the domain file |
| **Dependencies** | Python 3 + xarray/numpy, NCO | CDO only |
| **Ease of use** | Single command for both files | Single command for both files |

### CDO: dropped variables

CDO's internal data model supports variables of the form
`(time, level, lat, lon)`. Variables with **two non-spatial, non-time leading
dimensions** lie outside this model and are silently skipped with a
`cdfVerifyVars: Inconsistent number of dimensions` warning. In the EUR-0275
surface data file this affects 14 urban parameters:

| Variable | Shape |
|---|---|
| `ALB_IMPROAD_DIR/DIF` | `(numrad, numurbl, lsmlat, lsmlon)` |
| `ALB_PERROAD_DIR/DIF` | `(numrad, numurbl, lsmlat, lsmlon)` |
| `ALB_ROOF_DIR/DIF`    | `(numrad, numurbl, lsmlat, lsmlon)` |
| `ALB_WALL_DIR/DIF`    | `(numrad, numurbl, lsmlat, lsmlon)` |
| `TK_ROOF/WALL/IMPROAD`| `(nlevurb, numurbl, lsmlat, lsmlon)` |
| `CV_ROOF/WALL/IMPROAD`| `(nlevurb, numurbl, lsmlat, lsmlon)` |

These variables are required by eCLM's urban land unit. **Use `subset_nco.py`
if a complete surface data file is needed.**

### CDO: structural changes to the output file

Beyond dropped variables, CDO restructures the domain file in several ways
that differ from the input. The table below is based on a direct comparison of
`ncdump -h` output for the CDO and NCO domain subgrids.

| Aspect | NCO output | CDO output |
|---|---|---|
| **Dimension order** | `nj, ni, nv` (as in input) | `ni, nj, nv` (swapped) |
| **Variable order** | Preserved from input: `area`, `frac`, `mask`, `xc`, `xv`, `yc`, `yv` | Coordinate variables first: `xc`, `xc_bnds`, `yc`, `yc_bnds`, `mask`, `area`, `frac` |
| **Bounds variable names** | `xv`, `yv` (original names) | Renamed to `xc_bnds`, `yc_bnds`; `bounds` attributes updated accordingly |
| **Added variable attributes** | None | Adds `standard_name` and `_CoordinateAxisType` to `xc` and `yc` |
| **New global attributes** | None | Adds `CDI` and `CDO` version strings |
| **Global attribute order** | Preserved from input | Reordered |

These changes are cosmetic and do not affect the data values, but they may
matter if downstream tools or scripts depend on a specific variable order,
attribute names, or the `xv`/`yv` naming convention expected by eCLM.
