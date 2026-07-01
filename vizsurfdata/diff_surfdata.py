#!/usr/bin/env python3
"""
Compare two eCLM netCDF surface data files (text output).

Output sections:
  1. Variables only in file A
  2. Variables only in file B
  3. Variables present in both but with differing values

For single-site files (lsmlat=1, lsmlon=1) differences are shown
element-by-element with dimension-aware labels (soil depth, month,
PFT name, urban class, …).

For regional files, per-slice statistics are printed by default:
  [slice label]  N/M cells  mean Δ=…  max|Δ|=…  RMSE=…
Use --verbose to force element-level output for regional files too.

Usage:
    diff_surfdata.py FILE_A.nc FILE_B.nc
    diff_surfdata.py FILE_A.nc FILE_B.nc --var PCT_SAND KSAT_adj
    diff_surfdata.py FILE_A.nc FILE_B.nc --tol 1e-6
    diff_surfdata.py FILE_A.nc FILE_B.nc --verbose
    diff_surfdata.py FILE_A.nc FILE_B.nc --summary
    diff_surfdata.py FILE_A.nc FILE_B.nc --max-rows 0
"""

import argparse
import numpy as np
import netCDF4 as nc

# ---------------------------------------------------------------------------
# Dimension-label constants
# ---------------------------------------------------------------------------

SOIL_DEPTHS = [0.01, 0.04, 0.09, 0.16, 0.26, 0.40, 0.59, 0.83, 1.14, 1.56]

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

URBAN_TYPES = ['TBD', 'HD', 'MD']   # Tall Building District, High Density, Medium Density

_NATPFT_NAMES = {
    0:  "Bare Ground",
    1:  "NE tree – temperate",    2:  "NE tree – boreal",
    3:  "ND tree – boreal",       4:  "BE tree – tropical",
    5:  "BE tree – temperate",    6:  "BD tree – tropical",
    7:  "BD tree – temperate",    8:  "BD tree – boreal",
    9:  "BE shrub – temperate",   10: "BD shrub – temperate",
    11: "BD shrub – boreal",      12: "C3 arctic grass",
    13: "C3 grass",               14: "C4 grass",
}

_CFT_NAMES = {
    15: "C3 unmanaged rainfed",    16: "C3 unmanaged irrigated",
    17: "Temp corn rainfed",       18: "Temp corn irrigated",
    19: "Spring wheat rainfed",    20: "Spring wheat irrigated",
    21: "Winter wheat rainfed",    22: "Winter wheat irrigated",
    23: "Temp soybean rainfed",    24: "Temp soybean irrigated",
    25: "Barley rainfed",          26: "Barley irrigated",
    27: "Winter barley rainfed",   28: "Winter barley irrigated",
    29: "Rye rainfed",             30: "Rye irrigated",
    31: "Winter rye rainfed",      32: "Winter rye irrigated",
    33: "Cassava rainfed",         34: "Cassava irrigated",
    35: "Citrus rainfed",          36: "Citrus irrigated",
    37: "Cocoa rainfed",           38: "Cocoa irrigated",
    39: "Coffee rainfed",          40: "Coffee irrigated",
    41: "Cotton rainfed",          42: "Cotton irrigated",
    43: "Datepalm rainfed",        44: "Datepalm irrigated",
    45: "Foddergrass rainfed",     46: "Foddergrass irrigated",
    47: "Grapes rainfed",          48: "Grapes irrigated",
    49: "Groundnuts rainfed",      50: "Groundnuts irrigated",
    51: "Millet rainfed",          52: "Millet irrigated",
    53: "Oilpalm rainfed",         54: "Oilpalm irrigated",
    55: "Potatoes rainfed",        56: "Potatoes irrigated",
    57: "Pulses rainfed",          58: "Pulses irrigated",
    59: "Rapeseed rainfed",        60: "Rapeseed irrigated",
    61: "Rice rainfed",            62: "Rice irrigated",
    63: "Sorghum rainfed",         64: "Sorghum irrigated",
    65: "Sugarbeet rainfed",       66: "Sugarbeet irrigated",
    67: "Sugarcane rainfed",       68: "Sugarcane irrigated",
    69: "Sunflower rainfed",       70: "Sunflower irrigated",
    71: "Miscanthus rainfed",      72: "Miscanthus irrigated",
    73: "Switchgrass rainfed",     74: "Switchgrass irrigated",
    75: "Tropical corn rainfed",   76: "Tropical corn irrigated",
    77: "Tropical soybean rainfed", 78: "Tropical soybean irrigated",
}

_ALL_PFT_NAMES = {**_NATPFT_NAMES, **_CFT_NAMES}


# ---------------------------------------------------------------------------
# Index formatting
# ---------------------------------------------------------------------------

def _dim_label(dim_name, idx, ds, cft_coord=None):
    """Return a human-readable label for one (dimension, local-index) pair."""
    if dim_name == 'time':
        return f"t={MONTH_NAMES[idx % 12]}"
    if dim_name == 'nlevsoi':
        d = SOIL_DEPTHS[idx] if idx < len(SOIL_DEPTHS) else '?'
        return f"lev={idx}({d:.2f}m)" if isinstance(d, float) else f"lev={idx}"
    if dim_name == 'nlevgrnd':
        if idx < len(SOIL_DEPTHS):
            return f"lev={idx}({SOIL_DEPTHS[idx]:.2f}m)"
        return f"lev={idx}(bedrock-{idx - len(SOIL_DEPTHS)})"
    if dim_name == 'natpft':
        # natpft coordinate variable maps slot → global PFT index
        if 'natpft' in ds.variables:
            try:
                pft_idx = int(ds.variables['natpft'][idx])
            except Exception:
                pft_idx = idx
        else:
            pft_idx = idx
        name = _NATPFT_NAMES.get(pft_idx, f"PFT {pft_idx}")
        return f"natpft={pft_idx}({name})"
    if dim_name == 'cft':
        # cft coordinate variable maps slot → global CFT index
        if cft_coord is not None:
            try:
                cft_idx = int(cft_coord[idx])
            except Exception:
                cft_idx = idx + 15
        else:
            cft_idx = idx + 15
        name = _CFT_NAMES.get(cft_idx, f"CFT {cft_idx}")
        return f"cft={cft_idx}({name})"
    if dim_name == 'lsmpft':
        name = _ALL_PFT_NAMES.get(idx, f"PFT {idx}")
        return f"pft={idx}({name})"
    if dim_name == 'numurbl':
        name = URBAN_TYPES[idx] if idx < len(URBAN_TYPES) else str(idx)
        return f"urban={name}"
    if dim_name == 'numrad':
        return f"rad={'VIS' if idx == 0 else 'NIR'}"
    if dim_name == 'nlevurb':
        return f"urb_lev={idx}"
    if dim_name == 'nglcec':
        return f"glc_ec={idx}"
    if dim_name == 'nglcecp1':
        return f"glc_ecp1={idx}"
    if dim_name == 'lsmlat':
        return f"lat_idx={idx}"
    if dim_name == 'lsmlon':
        return f"lon_idx={idx}"
    return f"{dim_name}={idx}"


def format_index(dims, idx, ds, cft_coord=None):
    """Format a full index tuple into a readable label string."""
    return ", ".join(_dim_label(d, i, ds, cft_coord) for d, i in zip(dims, idx))


# ---------------------------------------------------------------------------
# Variable metadata
# ---------------------------------------------------------------------------

def var_label(ds, v):
    """Return 'VARNAME  long_name [units]  (dim×…)'."""
    var = ds.variables[v]
    long_name = getattr(var, 'long_name', '')
    units     = getattr(var, 'units', '')
    dims_str  = ' × '.join(
        f"{d}({ds.dimensions[d].size})" for d in var.dimensions
        if d in ds.dimensions
    )
    parts = []
    if long_name:
        parts.append(long_name)
    if units:
        parts.append(f"[{units}]")
    if dims_str:
        parts.append(f"({dims_str})")
    return f"{v}  " + "  ".join(parts) if parts else v


def _is_regional(ds):
    """True if the file has more than one lat or lon grid cell."""
    nlat = ds.dimensions.get('lsmlat')
    nlon = ds.dimensions.get('lsmlon')
    return (nlat is not None and nlat.size > 1) or \
           (nlon is not None and nlon.size > 1)


_SPATIAL_DIMS = {'lsmlat', 'lsmlon'}


def _non_spatial_axes(dims):
    """Return list of (axis_index, dim_name) for non-spatial dimensions."""
    return [(i, d) for i, d in enumerate(dims) if d not in _SPATIAL_DIMS]


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def _print_element_diffs(dims, fa, fb, ds, cft_coord, max_rows):
    """Print element-by-element differences. Returns number of differing elements."""
    both_nan = np.isnan(fa) & np.isnan(fb)
    mask = ~both_nan & ~np.isclose(fa, fb, equal_nan=True)
    indices = list(zip(*np.where(mask)))
    n_total = len(indices)
    limit = n_total if max_rows is None else max_rows
    for idx in indices[:limit]:
        label = format_index(dims, idx, ds, cft_coord)
        va, vb = fa[idx], fb[idx]
        print(f"    [{label}]  {va:.8g}  →  {vb:.8g}  (Δ={vb - va:+.4g})")
    if max_rows is not None and n_total > max_rows:
        print(f"    ... ({n_total - max_rows} more element(s) not shown; "
              f"use --verbose or --max-rows 0)")
    return n_total


def _print_regional_stats(dims, fa, fb, ds, cft_coord, verbose, max_rows):
    """Print per-non-spatial-slice statistics for regional arrays.
    With --verbose also emits element-level rows.
    Returns total number of differing elements."""
    non_sp = _non_spatial_axes(dims)
    non_sp_names  = [d for _, d in non_sp]
    non_sp_axes_i = [i for i, _ in non_sp]
    non_sp_shape  = tuple(ds.dimensions[d].size for d in non_sp_names)

    total_diffs = 0

    for ns_idx in (np.ndindex(*non_sp_shape) if non_sp_shape else [()]):
        # Build slicer that fixes non-spatial dims
        slices = [slice(None)] * len(dims)
        for pos, ax in enumerate(non_sp_axes_i):
            slices[ax] = ns_idx[pos]
        slices = tuple(slices)

        sa = fa[slices]
        sb = fb[slices]
        both_nan = np.isnan(sa) & np.isnan(sb)
        diff_mask = ~both_nan & ~np.isclose(sa, sb, equal_nan=True)
        n_diff = int(diff_mask.sum())
        if n_diff == 0:
            continue
        total_diffs += n_diff

        # Slice label from the non-spatial dimensions
        if non_sp_names:
            slice_label = ", ".join(
                _dim_label(non_sp_names[k], ns_idx[k], ds, cft_coord)
                for k in range(len(non_sp_names))
            )
        else:
            slice_label = "all cells"

        diff = sb - sa
        n_cells = sa.size
        print(f"    [{slice_label}]  {n_diff}/{n_cells} cells  "
              f"mean Δ={np.nanmean(diff):+.4g}  "
              f"max|Δ|={np.nanmax(np.abs(diff)):.4g}  "
              f"RMSE={np.sqrt(np.nanmean(diff ** 2)):.4g}")

        if verbose:
            # Element-level rows within this slice
            sp_dim_names = [d for d in dims if d in _SPATIAL_DIMS]
            sp_ax_in_slice = [i for i, d in enumerate(dims) if d in _SPATIAL_DIMS]
            printed = 0
            for cell_idx in zip(*np.where(diff_mask)):
                # Reconstruct full index tuple
                full = list(slices)
                for ci, sp_ax in enumerate(sp_ax_in_slice):
                    full[sp_ax] = cell_idx[ci]
                label = format_index(dims, tuple(full), ds, cft_coord)
                va = float(sa[cell_idx])
                vb = float(sb[cell_idx])
                print(f"      [{label}]  {va:.8g}  →  {vb:.8g}  "
                      f"(Δ={vb - va:+.4g})")
                printed += 1
                if max_rows is not None and printed >= max_rows:
                    remaining = n_diff - printed
                    if remaining > 0:
                        print(f"      ... ({remaining} more cell(s) in this slice "
                              f"not shown; use --max-rows 0)")
                    break

    return total_diffs


def _print_values_only(ds, v, cft_coord, verbose):
    """Print values of a variable that exists only in one file (when --verbose)."""
    if not verbose:
        return
    var = ds.variables[v]
    raw = var[:]
    dims = var.dimensions
    if raw.dtype.kind in ('S', 'U') or raw.dtype == object:
        for idx in np.ndindex(raw.shape):
            s = bytes(raw[idx]).rstrip(b" \x00").decode("utf-8", errors="replace")
            label = format_index(dims, idx, ds, cft_coord)
            print(f"    [{label}]  '{s}'")
        return
    try:
        fa = np.ma.filled(raw.astype(float), np.nan)
    except Exception:
        return
    for idx in np.ndindex(fa.shape):
        label = format_index(dims, idx, ds, cft_coord)
        print(f"    [{label}]  {fa[idx]:.8g}")


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def compare(path_a, path_b, var_filter=None, tol=1e-8,
            verbose=False, summary=False, max_rows=50):
    ds_a = nc.Dataset(path_a)
    ds_b = nc.Dataset(path_b)

    regional_a = _is_regional(ds_a)
    regional_b = _is_regional(ds_b)
    is_regional = regional_a or regional_b

    # CFT coordinate arrays for labelling (may differ between files)
    cft_coord_a = (np.array(ds_a.variables['cft'][:])
                   if 'cft' in ds_a.variables else None)
    cft_coord_b = (np.array(ds_b.variables['cft'][:])
                   if 'cft' in ds_b.variables else None)

    # Header
    print(f"File A: {path_a}")
    print(f"File B: {path_b}")
    if is_regional:
        nlat = ds_a.dimensions['lsmlat'].size
        nlon = ds_a.dimensions['lsmlon'].size
        print(f"Grid:   regional ({nlat} × {nlon})")
        print(f"        (regional output: per-slice stats by default; "
              f"use --verbose for cell-level rows)")
    else:
        print(f"Grid:   single-site")
    print(f"Tol:    {tol:.2g}")

    vars_a = set(ds_a.variables)
    vars_b = set(ds_b.variables)
    if var_filter:
        vars_a = vars_a & set(var_filter)
        vars_b = vars_b & set(var_filter)

    # ------------------------------------------------------------------
    # 1. Variables only in one file
    # ------------------------------------------------------------------
    only_a = sorted(vars_a - set(ds_b.variables))
    only_b = sorted(vars_b - set(ds_a.variables))

    if only_a:
        print(f"\nOnly in A  ({len(only_a)}):")
        for v in only_a:
            print(f"  {var_label(ds_a, v)}")
            _print_values_only(ds_a, v, cft_coord_a, verbose)
    else:
        print("\nNo variables only in A")

    if only_b:
        print(f"\nOnly in B  ({len(only_b)}):")
        for v in only_b:
            print(f"  {var_label(ds_b, v)}")
            _print_values_only(ds_b, v, cft_coord_b, verbose)
    else:
        print("\nNo variables only in B")

    # ------------------------------------------------------------------
    # 2. Find differences in shared variables (fast pass)
    # ------------------------------------------------------------------
    shared = sorted(vars_a & vars_b & set(ds_a.variables) & set(ds_b.variables))
    print(f"\nChecking {len(shared)} shared variable(s)…")

    diffs = {}   # varname -> n_differing_elements (int)

    for v in shared:
        raw_a = ds_a.variables[v][:]
        raw_b = ds_b.variables[v][:]

        # char arrays
        if raw_a.dtype.kind in ('S', 'U') or raw_a.dtype == object:
            if np.any(raw_a != raw_b):
                diffs[v] = -1   # sentinel: char differences, count not meaningful
            continue

        # numeric
        try:
            fa = np.ma.filled(raw_a.astype(float), np.nan)
            fb = np.ma.filled(raw_b.astype(float), np.nan)
        except Exception:
            continue

        both_nan = np.isnan(fa) & np.isnan(fb)
        different = ~both_nan & ~np.isclose(fa, fb, rtol=0, atol=tol, equal_nan=True)
        n = int(different.sum())
        if n:
            diffs[v] = n

    # ------------------------------------------------------------------
    # 3. Report differences
    # ------------------------------------------------------------------
    if not diffs:
        print("\nAll shared variables are identical.")
    else:
        print(f"\nDifferences in shared variables  ({len(diffs)} variable(s)):")

        for v, n_diff in diffs.items():
            var_a = ds_a.variables[v]
            dims  = tuple(var_a.dimensions)
            cft_coord = cft_coord_a   # use file-A cft mapping for labels

            count_str = f"{n_diff} element(s)" if n_diff >= 0 else "string diffs"
            print(f"\n  {var_label(ds_a, v)}  [{count_str}]")

            if summary:
                continue

            raw_a = ds_a.variables[v][:]
            raw_b = ds_b.variables[v][:]

            # char arrays
            if raw_a.dtype.kind in ('S', 'U') or raw_a.dtype == object:
                for idx in np.ndindex(raw_a.shape):
                    sa = bytes(raw_a[idx]).rstrip(b" \x00").decode("utf-8", errors="replace")
                    sb = bytes(raw_b[idx]).rstrip(b" \x00").decode("utf-8", errors="replace")
                    if sa != sb:
                        label = format_index(dims, idx, ds_a, cft_coord)
                        print(f"    [{label}]  '{sa}'  →  '{sb}'")
                continue

            fa = np.ma.filled(raw_a.astype(float), np.nan)
            fb = np.ma.filled(raw_b.astype(float), np.nan)

            has_spatial = bool(_SPATIAL_DIMS & set(dims))
            if is_regional and has_spatial:
                _print_regional_stats(dims, fa, fb, ds_a,
                                      cft_coord, verbose, max_rows)
            else:
                _print_element_diffs(dims, fa, fb, ds_a, cft_coord, max_rows)

    # ------------------------------------------------------------------
    # Summary line
    # ------------------------------------------------------------------
    print(f"\nSummary: {len(only_a)} only-in-A  |  {len(only_b)} only-in-B"
          f"  |  {len(diffs)} variable(s) with value differences")

    ds_a.close()
    ds_b.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file_a", metavar="FILE_A.nc")
    parser.add_argument("file_b", metavar="FILE_B.nc")
    parser.add_argument(
        "--var", nargs="+", metavar="VAR",
        help="Only compare these variable(s) (e.g. --var PCT_SAND KSAT_adj)",
    )
    parser.add_argument(
        "--tol", type=float, default=1e-8, metavar="TOL",
        help="Absolute tolerance for numerical comparisons (default: 1e-8)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="For regional files: also print cell-level rows inside each slice. "
             "For variables only in one file: also print their values.",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print only variable headers and element counts; suppress per-element "
             "and per-slice output",
    )
    parser.add_argument(
        "--max-rows", type=int, default=50, metavar="N",
        help="Max element/cell rows to show per variable or per slice "
             "(default: 50; use 0 for unlimited)",
    )
    args = parser.parse_args()

    compare(
        args.file_a, args.file_b,
        var_filter=args.var,
        tol=args.tol,
        verbose=args.verbose,
        summary=args.summary,
        max_rows=None if args.max_rows == 0 else args.max_rows,
    )


if __name__ == "__main__":
    main()
