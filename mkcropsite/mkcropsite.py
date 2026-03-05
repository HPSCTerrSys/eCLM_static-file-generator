#!/usr/bin/env python3
"""
mkcropsite.py – Convert a single-site CLM5 surface data file to a crop-site
configuration representing a uniform agricultural field.

Three modifications are applied:
  1. Land cover  – all major landunits set to Cropland (PCT_CROP = 100 %).
  2. Natural PFT – natural vegetation landunit set to 100 % C3 non-arctic grass
                   (natpft index 13).  This landunit carries zero weight after
                   step 1 but is kept consistent.
  3. Crop type   – a single user-specified Crop Functional Type (CFT) is set to
                   100 % of the crop landunit; all other CFTs are zeroed out.

Only single-site files (lsmlat = lsmlon = 1) are accepted.

Usage:
    python mkcropsite.py <surfdata.nc> --crop-type <CFT> [-o output.nc]
    python mkcropsite.py <surfdata.nc> --list-crops
"""

import os
import sys
import argparse
import shutil

import numpy as np
from netCDF4 import Dataset


# ---------------------------------------------------------------------------
# CLM5 PFT / CFT name tables (indices as used in the surface data file)
# ---------------------------------------------------------------------------

# natpft index for C3 non-arctic grass
C3GRASS_NATPFT = 13

NATPFT_NAMES = {
    0:  "Bare ground",
    1:  "Needleleaf evergreen tree – temperate",
    2:  "Needleleaf evergreen tree – boreal",
    3:  "Needleleaf deciduous tree – boreal",
    4:  "Broadleaf evergreen tree – tropical",
    5:  "Broadleaf evergreen tree – temperate",
    6:  "Broadleaf deciduous tree – tropical",
    7:  "Broadleaf deciduous tree – temperate",
    8:  "Broadleaf deciduous tree – boreal",
    9:  "Broadleaf evergreen shrub – temperate",
    10: "Broadleaf deciduous shrub – temperate",
    11: "Broadleaf deciduous shrub – boreal",
    12: "C3 arctic grass",
    13: "C3 grass (non-arctic)",
    14: "C4 grass",
}

# Global CLM5 CFT indices (15–78) and their names
CFT_NAMES = {
    15: "C3 unmanaged rainfed crop",    16: "C3 unmanaged irrigated crop",
    17: "Temperate corn rainfed",        18: "Temperate corn irrigated",
    19: "Spring wheat rainfed",          20: "Spring wheat irrigated",
    21: "Winter wheat rainfed",          22: "Winter wheat irrigated",
    23: "Temperate soybean rainfed",     24: "Temperate soybean irrigated",
    25: "Barley rainfed",                26: "Barley irrigated",
    27: "Winter barley rainfed",         28: "Winter barley irrigated",
    29: "Rye rainfed",                   30: "Rye irrigated",
    31: "Winter rye rainfed",            32: "Winter rye irrigated",
    33: "Cassava rainfed",               34: "Cassava irrigated",
    35: "Citrus rainfed",                36: "Citrus irrigated",
    37: "Cocoa rainfed",                 38: "Cocoa irrigated",
    39: "Coffee rainfed",                40: "Coffee irrigated",
    41: "Cotton rainfed",                42: "Cotton irrigated",
    43: "Datepalm rainfed",              44: "Datepalm irrigated",
    45: "Foddergrass rainfed",           46: "Foddergrass irrigated",
    47: "Grapes rainfed",                48: "Grapes irrigated",
    49: "Groundnuts rainfed",            50: "Groundnuts irrigated",
    51: "Millet rainfed",                52: "Millet irrigated",
    53: "Oilpalm rainfed",               54: "Oilpalm irrigated",
    55: "Potatoes rainfed",              56: "Potatoes irrigated",
    57: "Pulses rainfed",                58: "Pulses irrigated",
    59: "Rapeseed rainfed",              60: "Rapeseed irrigated",
    61: "Rice rainfed",                  62: "Rice irrigated",
    63: "Sorghum rainfed",               64: "Sorghum irrigated",
    65: "Sugarbeet rainfed",             66: "Sugarbeet irrigated",
    67: "Sugarcane rainfed",             68: "Sugarcane irrigated",
    69: "Sunflower rainfed",             70: "Sunflower irrigated",
    71: "Miscanthus rainfed",            72: "Miscanthus irrigated",
    73: "Switchgrass rainfed",           74: "Switchgrass irrigated",
    75: "Tropical corn rainfed",         76: "Tropical corn irrigated",
    77: "Tropical soybean rainfed",      78: "Tropical soybean irrigated",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_crops(cft_indices_in_file):
    """Print all CFT types available in the file and exit."""
    print("Available crop functional types (CFT) in this file:\n")
    print(f"  {'Index':>5}  Name")
    print(f"  {'-----':>5}  ----")
    for idx in sorted(cft_indices_in_file):
        name = CFT_NAMES.get(int(idx), f"Unknown CFT {idx}")
        print(f"  {int(idx):>5}  {name}")


def resolve_crop_type(crop_type_arg, cft_indices):
    """
    Resolve --crop-type argument to (global_cft_index, array_position).

    Accepts:
      - An integer string matching a global CFT index present in the file.
      - A case-insensitive substring of a CFT name.
    """
    cft_list = list(int(x) for x in cft_indices)

    # Try integer first
    try:
        requested = int(crop_type_arg)
        if requested not in cft_list:
            print(f"Error: CFT index {requested} is not present in this file.")
            print(f"  Valid indices: {cft_list[0]}–{cft_list[-1]}")
            print("  Run with --list-crops to see all available types.")
            sys.exit(1)
        pos = cft_list.index(requested)
        return requested, pos
    except ValueError:
        pass

    # Name substring match
    query = crop_type_arg.lower()
    matches = [(idx, name) for idx, name in CFT_NAMES.items()
               if query in name.lower() and idx in cft_list]

    if not matches:
        print(f"Error: No CFT name contains '{crop_type_arg}'.")
        print("  Run with --list-crops to see all available types.")
        sys.exit(1)

    if len(matches) > 1:
        print(f"Ambiguous crop type '{crop_type_arg}'. Matching types:")
        for idx, name in sorted(matches):
            print(f"  {idx:3d}: {name}")
        print("  Please be more specific or use the CFT index directly.")
        sys.exit(1)

    global_idx = matches[0][0]
    pos = cft_list.index(global_idx)
    return global_idx, pos


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert a single-site CLM5 surface data file to a crop-site "
            "configuration (uniform agricultural field)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set crop type by index (winter wheat rainfed = 21):
  python mkcropsite.py surfdata.nc --crop-type 21

  # Set crop type by name (case-insensitive substring):
  python mkcropsite.py surfdata.nc --crop-type "winter wheat rainfed"

  # Custom output file name:
  python mkcropsite.py surfdata.nc --crop-type 19 -o surfdata_soybean.nc

  # List all available crop types in a file:
  python mkcropsite.py surfdata.nc --list-crops
        """,
    )
    parser.add_argument("surfdata",
                        help="Input CLM5 single-site surface data NetCDF file")
    parser.add_argument("--crop-type", dest="crop_type", default=None,
                        help="Crop type as CFT global index (15–78) or "
                             "case-insensitive name substring (e.g. 'wheat')")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file path "
                             "(default: <input_stem>_cropsite.nc next to input)")
    parser.add_argument("--list-crops", action="store_true",
                        help="List all CFT types present in the file and exit")

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate input file
    # ------------------------------------------------------------------
    if not os.path.isfile(args.surfdata):
        print(f"Error: File not found: {args.surfdata}")
        sys.exit(1)

    with Dataset(args.surfdata, "r") as nc:
        nlat = nc.dimensions["lsmlat"].size
        nlon = nc.dimensions["lsmlon"].size

        # Sanity check: single-site only
        if nlat != 1 or nlon != 1:
            print("Error: This script only accepts single-site surface data files "
                  f"(lsmlat = lsmlon = 1).")
            print(f"  This file has lsmlat = {nlat}, lsmlon = {nlon}.")
            sys.exit(1)

        cft_indices = nc.variables["cft"][:]
        natpft_indices = nc.variables["natpft"][:]

        if args.list_crops:
            list_crops(cft_indices)
            sys.exit(0)

        if args.crop_type is None:
            parser.error("--crop-type is required (or use --list-crops).")

        # Resolve crop type
        cft_global, cft_pos = resolve_crop_type(args.crop_type, cft_indices)

        # Resolve natpft position for C3 non-arctic grass
        natpft_list = list(int(x) for x in natpft_indices)
        if C3GRASS_NATPFT not in natpft_list:
            print(f"Error: natpft index {C3GRASS_NATPFT} (C3 non-arctic grass) "
                  "not found in file.")
            sys.exit(1)
        c3grass_pos = natpft_list.index(C3GRASS_NATPFT)

    # ------------------------------------------------------------------
    # Determine output path and copy input
    # ------------------------------------------------------------------
    if args.output:
        out_path = args.output
    else:
        base, ext = os.path.splitext(args.surfdata)
        out_path = base + "_cropsite" + ext

    if os.path.abspath(out_path) == os.path.abspath(args.surfdata):
        print("Error: Output path is the same as the input. "
              "Use -o to specify a different output file.")
        sys.exit(1)

    shutil.copy2(args.surfdata, out_path)
    print(f"Copied {args.surfdata}")
    print(f"     → {out_path}")

    # ------------------------------------------------------------------
    # Apply modifications
    # ------------------------------------------------------------------
    with Dataset(out_path, "r+") as nc:

        # 1. Land cover: set all major landunits to zero, crop to 100 %
        nc.variables["PCT_CROP"][:]    = 100.0
        nc.variables["PCT_NATVEG"][:] = 0.0
        nc.variables["PCT_LAKE"][:]   = 0.0
        nc.variables["PCT_WETLAND"][:] = 0.0
        nc.variables["PCT_GLACIER"][:] = 0.0
        nc.variables["PCT_URBAN"][:]   = 0.0   # shape (numurbl, 1, 1)

        # 2. Natural PFT: C3 non-arctic grass at 100 % (within NatVeg landunit)
        pct_nat_pft = nc.variables["PCT_NAT_PFT"]
        pct_nat_pft[:] = 0.0
        pct_nat_pft[c3grass_pos, 0, 0] = 100.0

        # 3. Crop functional type: single CFT at 100 % (within crop landunit)
        pct_cft = nc.variables["PCT_CFT"]
        pct_cft[:] = 0.0
        pct_cft[cft_pos, 0, 0] = 100.0

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    cft_name = CFT_NAMES.get(cft_global, f"CFT {cft_global}")
    print()
    print("Modifications applied:")
    print("  [1] Land cover  : PCT_CROP = 100 %  "
          "(PCT_NATVEG, PCT_LAKE, PCT_WETLAND, PCT_GLACIER, PCT_URBAN = 0)")
    print(f"  [2] Natural PFT : 100 % C3 non-arctic grass "
          f"(natpft index {C3GRASS_NATPFT})")
    print(f"  [3] Crop type   : 100 % {cft_name} "
          f"(CFT global index {cft_global}, array position {cft_pos})")
    print()
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
