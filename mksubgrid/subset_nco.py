#!/usr/bin/env python3
"""
Extract a geographic subgrid from eCLM domain and surface data files.

Both files share the same curvilinear grid (rotated-pole EUR-CORDEX), meaning
lat/lon values do not map linearly to array indices. This script reads the 2D
coordinate arrays from the domain file to locate the smallest rectangular i/j
index block that covers the requested bounding box, then delegates the actual
file extraction to NCO's ncks.

Dependencies
------------
  Python : numpy, xarray
  NCO    : ncks

Usage
-----
  python subset_nco.py \\
      --domain    domain.lnd.EUR-0275.nc \\
      --surfdata  surfdata_EUR-0275.nc \\
      --out-domain    domain.lnd.ALP-0275.nc \\
      --out-surfdata  surfdata_ALP-0275.nc \\
      --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48

Notes
-----
  - Longitudes must be given in degrees east in the same convention as the
    input files (0–360 if the files were post-processed with xc+360).
  - The output bounding box may be slightly larger than requested because the
    curvilinear grid is axis-aligned in rotated-pole space, not in geographic
    space. Cells outside the box retain their original mask/frac values.
"""

import argparse
import subprocess
import sys

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Index detection
# ---------------------------------------------------------------------------

def find_index_bounds(domain_file, lon_min, lon_max, lat_min, lat_max):
    """Return the enclosing rectangular (j_min, j_max, i_min, i_max) index
    block for the given geographic bounding box.

    Reads the 2D xc/yc coordinate arrays from the domain file and selects all
    cells whose centres fall inside the box, then returns the min/max indices
    along each axis.
    """
    ds = xr.open_dataset(domain_file)
    lon = ds["xc"].values  # shape (nj, ni)
    lat = ds["yc"].values  # shape (nj, ni)
    ds.close()

    inside = (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)

    if not inside.any():
        sys.exit(
            "Error: no grid cells found within "
            f"lon=[{lon_min},{lon_max}] lat=[{lat_min},{lat_max}]. "
            "Check the bounding box and the longitude convention of the input files."
        )

    j_idx, i_idx = np.where(inside)
    return int(j_idx.min()), int(j_idx.max()), int(i_idx.min()), int(i_idx.max())


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def ncks_subset(infile, outfile, j_min, j_max, i_min, i_max, j_dim, i_dim):
    """Extract a rectangular index block from a NetCDF file using ncks."""
    cmd = [
        "ncks", "-O",
        f"-d", f"{j_dim},{j_min},{j_max}",
        f"-d", f"{i_dim},{i_min},{i_max}",
        infile, outfile,
    ]
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--domain",       required=True, help="Input domain file (NetCDF)")
    parser.add_argument("--surfdata",     required=True, help="Input surface data file (NetCDF)")
    parser.add_argument("--out-domain",   required=True, help="Output domain file")
    parser.add_argument("--out-surfdata", required=True, help="Output surface data file")
    parser.add_argument("--lon-min", required=True, type=float, help="West bound (degrees east)")
    parser.add_argument("--lon-max", required=True, type=float, help="East bound (degrees east)")
    parser.add_argument("--lat-min", required=True, type=float, help="South bound (degrees north)")
    parser.add_argument("--lat-max", required=True, type=float, help="North bound (degrees north)")
    return parser.parse_args()


def main():
    args = parse_args()

    print(
        f"\nLocating grid cells within "
        f"lon=[{args.lon_min}, {args.lon_max}], lat=[{args.lat_min}, {args.lat_max}] ..."
    )
    j_min, j_max, i_min, i_max = find_index_bounds(
        args.domain, args.lon_min, args.lon_max, args.lat_min, args.lat_max
    )
    print(f"  j / lsmlat : {j_min} – {j_max}  ({j_max - j_min + 1} cells)")
    print(f"  i / lsmlon : {i_min} – {i_max}  ({i_max - i_min + 1} cells)")

    print("\nExtracting domain file ...")
    # Domain file uses dimension names nj (rows) and ni (columns)
    ncks_subset(
        args.domain, args.out_domain,
        j_min, j_max, i_min, i_max,
        j_dim="nj", i_dim="ni",
    )

    print("\nExtracting surface data file ...")
    # Surface data file uses lsmlat / lsmlon for the same spatial dimensions
    ncks_subset(
        args.surfdata, args.out_surfdata,
        j_min, j_max, i_min, i_max,
        j_dim="lsmlat", i_dim="lsmlon",
    )

    print(f"\nDone.")
    print(f"  Domain  : {args.out_domain}")
    print(f"  Surfdata: {args.out_surfdata}")


if __name__ == "__main__":
    main()
