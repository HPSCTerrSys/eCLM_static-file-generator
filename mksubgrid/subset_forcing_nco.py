#!/usr/bin/env python3
"""
Extract a geographic subgrid from an eCLM atmospheric forcing file.

Forcing files share the same curvilinear rotated-pole grid as the domain and
surface data files (rlon=1592, rlat=1544 for EUR-0275). Geographic latitude
and longitude are stored as 2D arrays lon(rlat, rlon) and lat(rlat, rlon),
so the index bounds of the requested bounding box cannot be read from the
dimension axes directly.

This script reads the 2D coordinate arrays to locate the smallest rectangular
rlat/rlon index block covering the requested bounding box, then delegates the
actual file cutting to NCO's ncks. All time steps are preserved; only the
spatial dimensions are subsetted.

Dependencies
------------
  Python : numpy, xarray
  NCO    : ncks

Usage
-----
  python subset_forcing_nco.py \\
      --input  2022-01.nc \\
      --output 2022-01_ALP-0275.nc \\
      --lon-min 2 --lon-max 17 --lat-min 43 --lat-max 48

Notes
-----
  - Longitudes must be given in degrees east in the same convention as the
    input file.
  - The output bounding box may be slightly larger than requested because the
    curvilinear grid is axis-aligned in rotated-pole space, not in geographic
    space. Out-of-box cells retain their original fill values.
  - The 1D rotated-pole axes rlon(rlon) and rlat(rlat) and the rotated_pole
    scalar grid-mapping variable are preserved automatically by ncks.
"""

import argparse
import subprocess
import sys

import numpy as np
import xarray as xr


# ---------------------------------------------------------------------------
# Index detection
# ---------------------------------------------------------------------------

def find_index_bounds(input_file, lon_min, lon_max, lat_min, lat_max):
    """Return the enclosing rectangular (j_min, j_max, i_min, i_max) index
    block for the given geographic bounding box.

    Reads the 2D lon/lat coordinate arrays and selects all cells whose centres
    fall inside the box, then returns the min/max indices along each axis.
    """
    ds = xr.open_dataset(input_file)
    lon = ds["lon"].values  # shape (rlat, rlon)
    lat = ds["lat"].values  # shape (rlat, rlon)
    ds.close()

    inside = (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)

    if not inside.any():
        sys.exit(
            "Error: no grid cells found within "
            f"lon=[{lon_min},{lon_max}] lat=[{lat_min},{lat_max}]. "
            "Check the bounding box and the longitude convention of the input file."
        )

    j_idx, i_idx = np.where(inside)
    return int(j_idx.min()), int(j_idx.max()), int(i_idx.min()), int(i_idx.max())


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def ncks_subset(infile, outfile, j_min, j_max, i_min, i_max):
    """Extract a rectangular spatial block from a NetCDF file using ncks."""
    cmd = [
        "ncks", "-O",
        "-d", f"rlat,{j_min},{j_max}",
        "-d", f"rlon,{i_min},{i_max}",
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
    parser.add_argument("--input",   required=True, help="Input forcing file (NetCDF)")
    parser.add_argument("--output",  required=True, help="Output forcing file")
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
        args.input, args.lon_min, args.lon_max, args.lat_min, args.lat_max
    )
    print(f"  rlat : {j_min} – {j_max}  ({j_max - j_min + 1} cells)")
    print(f"  rlon : {i_min} – {i_max}  ({i_max - i_min + 1} cells)")

    print("\nExtracting forcing file ...")
    ncks_subset(args.input, args.output, j_min, j_max, i_min, i_max)

    print(f"\nDone.")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
